from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
import os
import json
import uuid
from dotenv import load_dotenv
from supabase import create_client, Client
from pinecone import Pinecone
import openai
from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import PdfFormatOption
import tempfile
from werkzeug.utils import secure_filename
from replit import db

load_dotenv()

app = Flask(__name__, static_folder="../frontend/build", static_url_path="/")
CORS(app)

# Initialize services
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

pinecone_api_key = os.getenv("PINECONE_API_KEY")
pinecone_client = Pinecone(api_key=pinecone_api_key) if pinecone_api_key else None
openai.api_key = os.getenv("OPENAI_API_KEY")

# Initialize Docling converter
converter = DocumentConverter()

# Persistent storage using Replit Key-Value Store
def get_reference_sets():
    """Get all reference sets from persistent storage"""
    try:
        return db.get("reference_sets", {})
    except:
        return {}

def save_reference_set(ref_set_id, reference_set):
    """Save reference set to persistent storage"""
    reference_sets = get_reference_sets()
    reference_sets[ref_set_id] = reference_set
    db["reference_sets"] = reference_sets

def get_inquiries():
    """Get all inquiries from persistent storage"""
    try:
        return db.get("inquiries", {})
    except:
        return {}

def save_inquiry(inquiry_id, inquiry):
    """Save inquiry to persistent storage"""
    inquiries = get_inquiries()
    inquiries[inquiry_id] = inquiry
    db["inquiries"] = inquiries

# Get or create Pinecone index
PINECONE_INDEX_NAME = "research-assistant"
if pinecone_client:
    try:
        # Try to get existing index
        index = pinecone_client.Index(PINECONE_INDEX_NAME)
    except:
        # Create index if it doesn't exist
        try:
            pinecone_client.create_index(
                name=PINECONE_INDEX_NAME,
                dimension=1536,  # OpenAI embedding dimension
                metric="cosine",
                spec={
                    "serverless": {
                        "cloud": "aws",
                        "region": "us-east-1"
                    }
                }
            )
            index = pinecone_client.Index(PINECONE_INDEX_NAME)
        except Exception as e:
            print(f"Error creating Pinecone index: {e}")
            index = None
else:
    index = None

@app.route("/api/hello")
def hello():
    return jsonify(message="Research Assistant API is running!")

@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json()
    try:
        response = supabase.auth.sign_in_with_password({
            "email": data["email"],
            "password": data["password"]
        })
        return jsonify({"success": True, "user": response.user.dict(), "session": response.session.dict()})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route("/api/auth/signup", methods=["POST"])
def signup():
    data = request.get_json()
    try:
        response = supabase.auth.sign_up({
            "email": data["email"],
            "password": data["password"]
        })
        return jsonify({"success": True, "user": response.user.dict()})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route("/api/reference-sets", methods=["GET"])
def api_get_reference_sets():
    # Return stored reference sets
    reference_sets_dict = get_reference_sets()
    # Convert ObservedDict objects to regular dicts for JSON serialization
    reference_sets_list = [dict(ref_set) for ref_set in reference_sets_dict.values()]
    return jsonify({"reference_sets": reference_sets_list})

@app.route("/api/reference-sets", methods=["POST"])
def create_reference_set():
    data = request.get_json()
    domain = data.get("domain", "").strip()  # Changed from 'name' to 'domain'
    description = data.get("description", "").strip()

    if not domain:
        return jsonify({"success": False, "error": "Domain is required"}), 400

    # Generate unique ID for the reference set
    ref_set_id = str(uuid.uuid4())

    # Store the reference set
    reference_set = {
        "id": ref_set_id,
        "domain": domain,
        "description": description,
        "file_count": 0
    }
    save_reference_set(ref_set_id, reference_set)

    print(f"Creating reference set with domain: {domain} - {description}")
    return jsonify({"success": True, "message": "Reference set created", "id": ref_set_id, "domain": domain})

@app.route("/api/inquiries", methods=["GET"])
def api_get_inquiries():
    # Return stored inquiries
    inquiries_dict = get_inquiries()
    # Convert ObservedDict objects to regular dicts for JSON serialization
    inquiries_list = [dict(inquiry) for inquiry in inquiries_dict.values()]
    return jsonify({"inquiries": inquiries_list})

@app.route("/api/inquiries", methods=["POST"])
def create_inquiry():
    data = request.get_json()
    title = data.get("title", "").strip()
    description = data.get("description", "").strip()
    reference_sets = data.get("reference_sets", [])

    if not title:
        return jsonify({"success": False, "error": "Title is required"}), 400

    if not reference_sets:
        return jsonify({"success": False, "error": "At least one reference set is required"}), 400

    # Generate unique ID for the inquiry
    inquiry_id = str(uuid.uuid4())

    # Store the inquiry
    inquiry = {
        "id": inquiry_id,
        "title": title,
        "description": description,
        "reference_sets": reference_sets,
        "messages": []
    }
    save_inquiry(inquiry_id, inquiry)

    print(f"Creating inquiry: {title} - {description} with reference sets: {reference_sets}")
    return jsonify({"success": True, "message": "Inquiry created", "inquiry_id": inquiry_id})

def get_embedding(text):
    """Get OpenAI embedding for text"""
    try:
        response = openai.embeddings.create(
            model="text-embedding-ada-002",
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"Error getting embedding: {e}")
        return None

def chunk_text(text, max_chunk_size=1000, overlap=100):
    """Split text into overlapping chunks"""
    chunks = []
    start = 0

    while start < len(text):
        end = start + max_chunk_size
        chunk = text[start:end]

        # Try to break at sentence boundary
        if end < len(text):
            last_period = chunk.rfind('.')
            last_newline = chunk.rfind('\n')
            break_point = max(last_period, last_newline)

            if break_point > start + max_chunk_size // 2:
                chunk = text[start:break_point + 1]
                end = break_point + 1

        chunks.append(chunk.strip())
        start = end - overlap

        if start >= len(text):
            break

    return chunks

@app.route("/api/reference-sets/<ref_set_id>/upload", methods=["POST"])
def upload_file_to_reference_set(ref_set_id):
    """Upload and process file for a specific reference set"""
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    # Get domain from form data
    domain = request.form.get('domain', 'Unknown Domain')

    try:
        # Save file temporarily
        filename = secure_filename(file.filename)
        temp_path = os.path.join(tempfile.gettempdir(), filename)
        file.save(temp_path)

        # Check file extension and process accordingly
        file_extension = filename.split('.')[-1].lower() if '.' in filename else ''

        print(f"Processing file: {filename}")

        if file_extension == 'jsonl':
            # Process JSONL file with structure preservation
            pages_info = process_jsonl_file(temp_path)
            if not pages_info:
                raise Exception("No valid JSON objects found in JSONL file")
        elif file_extension == 'json':
            # Process JSON file with structure preservation
            pages_info = process_json_file(temp_path)
            if not pages_info:
                raise Exception("No valid data found in JSON file")
        else:
            # Process with Docling for other formats
            result = converter.convert(temp_path)

            # Extract text and page information
            document_text = result.document.export_to_markdown()

            # Get page information if available
            pages_info = []
            if hasattr(result.document, 'pages') and result.document.pages:
                for i, page in enumerate(result.document.pages):
                    pages_info.append({
                        'page_num': i + 1,
                        'text': page.export_to_markdown() if hasattr(page, 'export_to_markdown') else str(page)
                    })
            else:
                # If no page info available, treat as single page
                pages_info = [{'page_num': 1, 'text': document_text}]

        # Process each page
        total_chunks = 0
        vectors_to_upsert = []
        
        print(f"Processing {len(pages_info)} pages/entries from {filename}...")

        for idx, page_info in enumerate(pages_info):
            if idx % 10 == 0:  # Log progress every 10 pages
                print(f"  Processing entry {idx + 1}/{len(pages_info)}...")
            page_text = page_info['text']
            page_num = page_info['page_num']
            metadata = page_info.get('metadata', {})
            raw_json = page_info.get('raw_json')

            # Split page into chunks
            chunks = chunk_text(page_text)

            for i, chunk in enumerate(chunks):
                if len(chunk.strip()) < 50:  # Skip very short chunks
                    continue

                # Get embedding
                embedding = get_embedding(chunk)
                if not embedding:
                    print(f"    Failed to get embedding for chunk {i} on page {page_num}")
                    continue

                # Create unique ID for this chunk
                chunk_id = f"{ref_set_id}_{filename}_{page_num}_{i}"

                # Prepare metadata
                chunk_metadata = {
                    'domain': domain,
                    'reference_set_id': ref_set_id,
                    'document_name': filename,
                    'page_number': page_num,
                    'chunk_index': i,
                    'text': chunk,
                    'file_type': filename.split('.')[-1].lower() if '.' in filename else 'unknown',
                }
                chunk_metadata.update(metadata)  # Add extracted metadata

                vectors_to_upsert.append({
                    'id': chunk_id,
                    'values': embedding,
                    'metadata': chunk_metadata
                })

                total_chunks += 1

        # Upsert to Pinecone in batches
        if index and vectors_to_upsert:
            print(f"Uploading {len(vectors_to_upsert)} chunks to vector database...")
            batch_size = 100
            for i in range(0, len(vectors_to_upsert), batch_size):
                batch = vectors_to_upsert[i:i + batch_size]
                try:
                    index.upsert(vectors=batch)
                    print(f"  Uploaded batch {i//batch_size + 1}/{(len(vectors_to_upsert) + batch_size - 1)//batch_size}")
                except Exception as e:
                    print(f"  Error uploading batch: {e}")
        elif not index:
            print("Warning: No Pinecone index available - content processed but not stored for search")
        elif not vectors_to_upsert:
            print("Warning: No valid chunks created - check OpenAI API connection")

        # Clean up temp file
        os.remove(temp_path)

        # Update file count for the reference set (fix: always increment, even if embeddings failed)
        reference_sets = get_reference_sets()
        if ref_set_id in reference_sets:
            reference_sets[ref_set_id]["file_count"] += 1
            save_reference_set(ref_set_id, reference_sets[ref_set_id])
            print(f"Updated file count for reference set {ref_set_id}: {reference_sets[ref_set_id]['file_count']} files")

        print(f"Successfully processed {filename}: {total_chunks} chunks across {len(pages_info)} pages")

        return jsonify({
            "success": True, 
            "message": f"File processed successfully",
            "stats": {
                "filename": filename,
                "pages": len(pages_info),
                "chunks": total_chunks,
                "domain": domain
            }
        })

    except Exception as e:
        # Clean up temp file if it exists
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.remove(temp_path)

        print(f"Error processing file: {e}")
        return jsonify({"error": f"Error processing file: {str(e)}"}), 500

def process_jsonl_file(file_path):
    """Process JSONL file and preserve structure with metadata"""
    pages_info = []

    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            line_num = 0

            for line in file:
                line = line.strip()
                if not line:
                    continue

                line_num += 1
                try:
                    json_obj = json.loads(line)

                    # Create structured content that preserves metadata
                    structured_content = {
                        'line_number': line_num,
                        'raw_data': json_obj,
                        'searchable_text': '',
                        'metadata': {}
                    }

                    # Extract searchable text while preserving structure
                    text_parts = []

                    # Handle different content structures
                    if 'verse' in json_obj:
                        # Quran/religious text structure
                        structured_content['metadata']['content_type'] = 'verse'
                        if 'chapter' in json_obj:
                            structured_content['metadata']['chapter'] = json_obj['chapter']
                        if 'verse_number' in json_obj:
                            structured_content['metadata']['verse_number'] = json_obj['verse_number']

                        # Add verse content
                        if isinstance(json_obj['verse'], str):
                            text_parts.append(f"Verse: {json_obj['verse']}")
                        elif isinstance(json_obj['verse'], dict):
                            for lang, text in json_obj['verse'].items():
                                text_parts.append(f"{lang}: {text}")
                                structured_content['metadata'][f'verse_{lang}'] = text

                    # Handle Quran verse structure with ayah, arabic, and English translation
                    if 'ayah' in json_obj:
                        structured_content['metadata']['content_type'] = 'verse'
                        structured_content['metadata']['verse_number'] = json_obj['ayah']
                        
                        # Store Arabic text
                        if 'arabic' in json_obj:
                            structured_content['metadata']['arabic'] = json_obj['arabic']
                            text_parts.append(f"Arabic: {json_obj['arabic']}")
                        
                        # Store English translation from "Clear Quran English"
                        if 'Clear Quran English' in json_obj:
                            structured_content['metadata']['english'] = json_obj['Clear Quran English']
                            text_parts.append(f"English: {json_obj['Clear Quran English']}")

                    # Handle translations
                    for lang_field in ['arabic', 'english', 'translation']:
                        if lang_field in json_obj:
                            if isinstance(json_obj[lang_field], str):
                                text_parts.append(f"{lang_field}: {json_obj[lang_field]}")
                                structured_content['metadata'][lang_field] = json_obj[lang_field]

                    # Handle general text fields
                    for field in ['text', 'content', 'title', 'description', 'passage']:
                        if field in json_obj and isinstance(json_obj[field], str):
                            text_parts.append(f"{field}: {json_obj[field]}")
                            structured_content['metadata'][field] = json_obj[field]

                    # Preserve all other metadata
                    for key, value in json_obj.items():
                        if key not in ['verse', 'arabic', 'english', 'translation', 'text', 'content', 'title', 'description', 'passage']:
                            if isinstance(value, (str, int, float, bool)):
                                structured_content['metadata'][key] = value

                    # Combine all text for searching
                    structured_content['searchable_text'] = ' | '.join(text_parts)

                    # Create a "page" for each JSON object to maintain granularity
                    if structured_content['searchable_text'].strip():
                        pages_info.append({
                            'page_num': line_num,
                            'text': structured_content['searchable_text'],
                            'metadata': structured_content['metadata'],
                            'raw_json': json_obj
                        })

                except json.JSONDecodeError as e:
                    print(f"Invalid JSON on line {line_num}: {e}")
                    continue

        return pages_info

    except Exception as e:
        print(f"Error processing JSONL file: {e}")
        return []

def process_json_file(file_path):
    """Process JSON file and preserve structure with metadata"""
    pages_info = []

    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            json_data = json.load(file)

            # Handle different JSON structures
            if isinstance(json_data, list):
                # Array of objects
                for i, obj in enumerate(json_data):
                    if isinstance(obj, dict):
                        # Process similar to JSONL
                        structured_content = {
                            'index': i,
                            'raw_data': obj,
                            'searchable_text': '',
                            'metadata': {}
                        }

                        # Extract searchable text
                        text_parts = []
                        for key, value in obj.items():
                            if isinstance(value, str) and len(value) > 5:
                                text_parts.append(f"{key}: {value}")
                                structured_content['metadata'][key] = value
                            elif isinstance(value, (int, float, bool)):
                                structured_content['metadata'][key] = value

                        structured_content['searchable_text'] = ' | '.join(text_parts)

                        if structured_content['searchable_text'].strip():
                            pages_info.append({
                                'page_num': i + 1,
                                'text': structured_content['searchable_text'],
                                'metadata': structured_content['metadata'],
                                'raw_json': obj
                            })

            elif isinstance(json_data, dict):
                # Single object or nested structure
                def extract_from_dict(data, prefix="", page_num=1):
                    text_parts = []
                    metadata = {}

                    for key, value in data.items():
                        full_key = f"{prefix}.{key}" if prefix else key

                        if isinstance(value, str) and len(value) > 5:
                            text_parts.append(f"{full_key}: {value}")
                            metadata[full_key] = value
                        elif isinstance(value, (int, float, bool)):
                            metadata[full_key] = value
                        elif isinstance(value, dict):
                            # Recursively handle nested objects
                            nested_text, nested_meta = extract_from_dict(value, full_key, page_num)
                            text_parts.extend(nested_text)
                            metadata.update(nested_meta)

                    return text_parts, metadata

                text_parts, metadata = extract_from_dict(json_data)

                if text_parts:
                    pages_info.append({
                        'page_num': 1,
                        'text': ' | '.join(text_parts),
                        'metadata': metadata,
                        'raw_json': json_data
                    })

        return pages_info

    except Exception as e:
        print(f"Error processing JSON file: {e}")
        return []

@app.route("/api/test-search", methods=["POST"])
def test_search():
    """Test search functionality without affecting anything"""
    data = request.get_json()
    query = data.get("query", "")
    ref_set_id = data.get("ref_set_id", "")

    if not query:
        return jsonify({"error": "Query is required"}), 400

    try:
        # Get embedding for the query
        query_embedding = get_embedding(query)
        if not query_embedding:
            return jsonify({"error": "Failed to generate query embedding"}), 500

        # Search Pinecone for relevant chunks
        relevant_results = []

        if index and query_embedding:
            # Query Pinecone
            search_results = index.query(
                vector=query_embedding,
                top_k=3,  # Just get top 3 for testing
                include_metadata=True,
                filter={
                    "reference_set_id": ref_set_id
                } if ref_set_id else None
            )

            # Extract relevant chunks with all metadata
            for i, match in enumerate(search_results.matches):
                metadata = match.metadata
                
                # Extract Quran-specific information
                arabic_text = metadata.get('arabic', '')
                english_text = metadata.get('english', '')
                chapter = metadata.get('chapter', '')
                verse_number = metadata.get('verse_number', '')
                
                # Format display text for Quran verses
                formatted_text = ""
                if arabic_text and english_text:
                    formatted_text = f"Arabic: {arabic_text}\n\nEnglish: {english_text}"
                elif arabic_text:
                    formatted_text = f"Arabic: {arabic_text}"
                elif english_text:
                    formatted_text = f"English: {english_text}"
                else:
                    # Fallback to original text
                    formatted_text = metadata.get('text', '')
                
                # Format verse reference
                verse_reference = ""
                if chapter and verse_number:
                    # Try to get surah name if available
                    surah_name = metadata.get('surah_name', f"Surah {chapter}")
                    verse_reference = f"{surah_name} {chapter}:{verse_number}"
                elif chapter:
                    verse_reference = f"Chapter {chapter}"
                
                relevant_results.append({
                    "rank": i + 1,
                    "score": float(match.score),
                    "text_preview": formatted_text[:400] + "..." if len(formatted_text) > 400 else formatted_text,
                    "full_text": formatted_text,
                    "arabic": arabic_text,
                    "english": english_text,
                    "verse_reference": verse_reference,
                    "chapter": chapter,
                    "verse_number": verse_number,
                    "document": metadata.get('document_name', 'Unknown'),
                    "domain": metadata.get('domain', 'Unknown'),
                    "page_number": metadata.get('page_number', 'N/A'),
                    "chunk_index": metadata.get('chunk_index', 'N/A'),
                    "metadata_keys": list(metadata.keys())
                })

        return jsonify({
            "query": query,
            "results_found": len(relevant_results),
            "results": relevant_results,
            "ref_set_filter": ref_set_id if ref_set_id else "No filter (all reference sets)"
        })

    except Exception as e:
        print(f"Test search error: {e}")
        return jsonify({"error": f"Search test failed: {str(e)}"}), 500

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json()
    query = data.get("query", "")
    reference_sets = data.get("reference_sets", [])
    inquiry_id = data.get("inquiry_id", "")

    if not query:
        return jsonify({"error": "Query is required"}), 400

    try:
        # Get embedding for the query
        query_embedding = get_embedding(query)
        if not query_embedding:
            return jsonify({"error": "Failed to generate query embedding"}), 500

        # Search Pinecone for relevant chunks
        relevant_chunks = []
        citations = []

        if index and query_embedding:
            # Query Pinecone
            search_results = index.query(
                vector=query_embedding,
                top_k=5,
                include_metadata=True,
                filter={
                    "reference_set_id": {"$in": reference_sets}
                } if reference_sets else None
            )

            # Extract relevant chunks and build citations
            for match in search_results.matches:
                metadata = match.metadata
                relevant_chunks.append(metadata.get('text', ''))

                citation = f"{metadata.get('document_name', 'Unknown')} (Domain: {metadata.get('domain', 'Unknown')}, Page: {metadata.get('page_number', 'N/A')})"
                if citation not in citations:
                    citations.append(citation)

        # Build context from relevant chunks
        context = "\n\n".join(relevant_chunks[:3])  # Use top 3 chunks

        if not context:
            response = f"I couldn't find relevant information in the selected reference sets for your query: '{query}'. You may need to upload more documents to these domains or try a different query."
        else:
            # Generate response using OpenAI with context
            try:
                chat_response = openai.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {
                            "role": "system",
                            "content": """You are a research assistant helping analyze documents. Use the provided context to answer questions accurately. Always cite your sources and indicate when information is not available in the context."""
                        },
                        {
                            "role": "user",
                            "content": f"""Context from research documents:
{context}

Question: {query}

Please provide a detailed answer based on the context above. If the context doesn't contain enough information to fully answer the question, please indicate that."""
                        }
                    ],
                    max_tokens=500,
                    temperature=0.7
                )

                response = chat_response.choices[0].message.content

            except Exception as e:
                print(f"OpenAI API error: {e}")
                response = f"I found relevant information but encountered an error generating the response. Here's what I found in the documents: {context[:500]}..."

        return jsonify({
            "response": response,
            "citations": citations,
            "sources": reference_sets,
            "chunks_found": len(relevant_chunks)
        })

    except Exception as e:
        print(f"Chat error: {e}")
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_react_app(path):
    # Handle API routes separately
    if path.startswith("api/"):
        return "API endpoint not found", 404

    # Serve static files
    if path and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)

    # For all other routes, serve React app
    return send_from_directory(app.static_folder, "index.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
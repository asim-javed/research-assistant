
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
def get_reference_sets():
    # For now, return mock data - in a real app you'd get from Supabase based on user ID
    mock_data = [
        {"id": "1", "domain": "Machine Learning", "description": "Papers and documents about ML algorithms", "file_count": 0},
        {"id": "2", "domain": "Medical Research", "description": "Clinical studies and medical literature", "file_count": 0}
    ]
    return jsonify({"reference_sets": mock_data})

@app.route("/api/reference-sets", methods=["POST"])
def create_reference_set():
    data = request.get_json()
    domain = data.get("domain", "").strip()  # Changed from 'name' to 'domain'
    description = data.get("description", "").strip()
    
    if not domain:
        return jsonify({"success": False, "error": "Domain is required"}), 400
    
    # Generate unique ID for the reference set
    ref_set_id = str(uuid.uuid4())
    
    # In a real app, you'd save to Supabase here
    # For now, just return success
    print(f"Creating reference set with domain: {domain} - {description}")
    return jsonify({"success": True, "message": "Reference set created", "id": ref_set_id, "domain": domain})

@app.route("/api/inquiries", methods=["GET"])
def get_inquiries():
    # For now, return mock data - in a real app you'd get from Supabase based on user ID
    mock_data = [
        {"id": "1", "title": "Sample Inquiry", "description": "A sample inquiry for testing"}
    ]
    return jsonify({"inquiries": mock_data})

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
    
    # In a real app, you'd save to Supabase here
    # For now, just return success
    print(f"Creating inquiry: {title} - {description} with reference sets: {reference_sets}")
    return jsonify({"success": True, "message": "Inquiry created", "inquiry_id": f"inquiry_{len(title)}_id"})

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
        
        # Process with Docling
        print(f"Processing file: {filename}")
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
        
        for page_info in pages_info:
            page_text = page_info['text']
            page_num = page_info['page_num']
            
            # Split page into chunks
            chunks = chunk_text(page_text)
            
            for i, chunk in enumerate(chunks):
                if len(chunk.strip()) < 50:  # Skip very short chunks
                    continue
                
                # Get embedding
                embedding = get_embedding(chunk)
                if not embedding:
                    continue
                
                # Create unique ID for this chunk
                chunk_id = f"{ref_set_id}_{filename}_{page_num}_{i}"
                
                # Prepare metadata
                metadata = {
                    'domain': domain,
                    'reference_set_id': ref_set_id,
                    'document_name': filename,
                    'page_number': page_num,
                    'chunk_index': i,
                    'text': chunk,
                    'file_type': filename.split('.')[-1].lower() if '.' in filename else 'unknown'
                }
                
                vectors_to_upsert.append({
                    'id': chunk_id,
                    'values': embedding,
                    'metadata': metadata
                })
                
                total_chunks += 1
        
        # Upsert to Pinecone in batches
        if index and vectors_to_upsert:
            batch_size = 100
            for i in range(0, len(vectors_to_upsert), batch_size):
                batch = vectors_to_upsert[i:i + batch_size]
                index.upsert(vectors=batch)
        
        # Clean up temp file
        os.remove(temp_path)
        
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

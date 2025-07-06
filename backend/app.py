
from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
import os
from dotenv import load_dotenv
from supabase import create_client, Client
from pinecone import Pinecone
import openai

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
    # Get user's reference sets
    # This will be implemented once you have auth working
    return jsonify({"reference_sets": []})

@app.route("/api/reference-sets", methods=["POST"])
def create_reference_set():
    data = request.get_json()
    # Create new reference set
    # This will store in Supabase
    return jsonify({"success": True, "message": "Reference set created"})

@app.route("/api/inquiries", methods=["GET"])
def get_inquiries():
    # Get user's lines of inquiry
    return jsonify({"inquiries": []})

@app.route("/api/inquiries", methods=["POST"])
def create_inquiry():
    data = request.get_json()
    # Start new line of inquiry
    return jsonify({"success": True, "inquiry_id": "temp_id"})

@app.route("/api/upload", methods=["POST"])
def upload_file():
    # Handle file upload and processing with Docling
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    
    # TODO: Process with Docling, chunk, embed, store in Pinecone
    return jsonify({"success": True, "message": "File uploaded and processed"})

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json()
    query = data.get("query", "")
    reference_sets = data.get("reference_sets", [])
    
    # TODO: Query Pinecone, get relevant chunks, generate response with OpenAI
    response = "This is a placeholder response for: " + query
    
    return jsonify({
        "response": response,
        "citations": [],
        "sources": []
    })

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_react_app(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, "index.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)

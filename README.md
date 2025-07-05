
# Research Assistant MVP

A full-stack research assistant designed for academic inquiry. Features include:
- Reference Set (domain-based) document organization
- Persistent, citation-based chat sessions (Lines of Inquiry)
- Multidisciplinary querying across reference sets
- User authentication via Supabase
- File storage and vector search with Pinecone
- Chunking and embedding via Docling

## Tech Stack
- Flask (backend)
- React (frontend)
- Supabase (auth + metadata)
- Pinecone (vector DB)
- Docling (embedding pipeline)

## How to Use on Replit
1. Import this repo into Replit.
2. Set your environment variables in a `.env` file:
   - `SUPABASE_URL`
   - `SUPABASE_KEY`
   - `PINECONE_API_KEY`
   - `OPENAI_API_KEY`
3. Click Run.

## File Structure
- `backend/`: Flask API
- `frontend/`: React UI
- `supabase_schema.sql`: DB schema
- `.env`: Place your API keys here

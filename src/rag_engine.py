# Chunking, ChromaDB vector store, retrieval logic

import os
import io
import streamlit as st 
import chromadb
from sentence_transformers import SentenceTransformer
from pypdf import PdfReader

@st.cache_resource
def load_embedder():
    return SentenceTransformer('all-MiniLM-L6-v2')

embedder = load_embedder() 
chroma_client = chromadb.PersistentClient(path="./data/chroma_db")
collection = chroma_client.get_or_create_collection(name="tax_knowledge")

def clear_vector_db():
    """Reset the database (useful for testing)."""
    global collection
    chroma_client.delete_collection("tax_knowledge")
    collection = chroma_client.get_or_create_collection(name="tax_knowledge")

def ingest_pdf(file_bytes: bytes, filename: str):
    """Extract text from a PDF, chunk it, and store in ChromaDB."""
    reader = PdfReader(io.BytesIO(file_bytes))
    
    full_text = ""
    for page in reader.pages:
        text = page.extract_text()
        if text:
            full_text += text + "\n"
    
    chunks = full_text.split("\n\n")
    chunks = [chunk.strip() for chunk in chunks if len(chunk.strip()) > 100]
    
    if not chunks:
        chunks = [full_text[i:i+1000] for i in range(0, len(full_text), 1000)]
    
    for i, chunk in enumerate(chunks):
        embedding = embedder.encode(chunk).tolist()
        collection.add(
            documents=[chunk],
            embeddings=[embedding],
            ids=[f"{filename}_{i}"]
        )
    
    return len(chunks)

def retrieve_context(query: str, top_k: int = 3) -> str:
    """Search for the most relevant tax rules based on the user's query."""
    if collection.count() == 0:
        return ""
    
    query_embedding = embedder.encode(query).tolist()
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k
    )
    
    if results and results['documents']:
        docs = results['documents'][0]
        return "\n---\n".join(docs)
    return ""

def get_knowledge_count() -> int:
    """Return the number of chunks stored."""
    return collection.count()
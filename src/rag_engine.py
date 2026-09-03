# Chunking, ChromaDB vector store, retrieval logic

import hashlib
import io
import os

import chromadb
import streamlit as st
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer


@st.cache_resource
def load_embedder():
    return SentenceTransformer("all-MiniLM-L6-v2")


embedder = load_embedder()


CHROMA_PATH = os.path.join("data", "chroma_db")

os.makedirs(CHROMA_PATH, exist_ok=True)

chroma_client = chromadb.PersistentClient(
    path=CHROMA_PATH
)

collection = chroma_client.get_or_create_collection(
    name="tax_knowledge"
)


def clear_vector_db():
    global collection

    try:
        chroma_client.delete_collection("tax_knowledge")
    except Exception:
        pass

    collection = chroma_client.get_or_create_collection(
        name="tax_knowledge"
    )


def create_chunk_id(filename: str, chunk_index: int, chunk: str):
    content = f"{filename}_{chunk_index}_{chunk}"

    return hashlib.md5(
        content.encode("utf-8")
    ).hexdigest()


def ingest_pdf(file_bytes: bytes, filename: str):
    reader = PdfReader(io.BytesIO(file_bytes))

    full_text = ""

    for page in reader.pages:
        text = page.extract_text()

        if text:
            full_text += text + "\n"

    full_text = full_text.strip()

    if not full_text:
        return 0

    chunks = full_text.split("\n\n")

    chunks = [
        chunk.strip()
        for chunk in chunks
        if len(chunk.strip()) > 100
    ]

    if not chunks:
        chunks = [
            full_text[i:i + 1000]
            for i in range(0, len(full_text), 1000)
        ]

    documents = []
    embeddings = []
    ids = []
    metadatas = []

    for i, chunk in enumerate(chunks):
        chunk_id = create_chunk_id(
            filename,
            i,
            chunk
        )

        embedding = embedder.encode(
            chunk
        ).tolist()

        documents.append(chunk)
        embeddings.append(embedding)
        ids.append(chunk_id)

        metadatas.append({
            "filename": filename,
            "chunk_index": i
        })

    collection.upsert(
        documents=documents,
        embeddings=embeddings,
        ids=ids,
        metadatas=metadatas
    )

    return len(chunks)


def retrieve_context(
    query: str,
    top_k: int = 3
) -> str:

    if collection.count() == 0:
        return ""

    query_embedding = embedder.encode(
        query
    ).tolist()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(
            top_k,
            collection.count()
        )
    )

    if not results:
        return ""

    documents = results.get("documents")

    if not documents:
        return ""

    if not documents[0]:
        return ""

    return "\n---\n".join(
        documents[0]
    )


def get_knowledge_count():
    return collection.count()
import os
import uuid
import hashlib
import fitz  # pymupdf
import pandas as pd
from typing import List, Dict, Tuple
from langchain.text_splitter import RecursiveCharacterTextSplitter
import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
from fastembed import TextEmbedding

CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_db")
MAX_CHUNK_SIZE = int(os.getenv("MAX_CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))

_embed_model = None
_chroma_client = None
_collection = None


def get_embed_model():
    global _embed_model
    if _embed_model is None:
        _embed_model = TextEmbedding("sentence-transformers/all-MiniLM-L6-v2")
    return _embed_model


def get_collection():
    global _chroma_client, _collection
    if _collection is None:
        _chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
        _collection = _chroma_client.get_or_create_collection(
            name="smartrag_docs",
            metadata={"hnsw:space": "cosine"}
        )
    return _collection


def embed_texts(texts: List[str]) -> List[List[float]]:
    model = get_embed_model()
    embeddings = list(model.embed(texts))
    return [e.tolist() for e in embeddings]


def extract_text_from_pdf(file_path: str) -> Tuple[str, int]:
    doc = fitz.open(file_path)
    text = ""
    for page in doc:
        text += page.get_text()
    page_count = len(doc)
    doc.close()
    return text, page_count


def extract_text_from_csv(file_path: str) -> Tuple[str, int]:
    df = pd.read_csv(file_path)
    text = f"CSV Document with {len(df)} rows and {len(df.columns)} columns.\n"
    text += f"Columns: {', '.join(df.columns.tolist())}\n\n"
    # Convert each row to readable text
    for idx, row in df.iterrows():
        row_text = " | ".join([f"{col}: {val}" for col, val in row.items()])
        text += f"Row {idx+1}: {row_text}\n"
    return text, 1


def extract_text_from_txt(file_path: str) -> Tuple[str, int]:
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()
    return text, 1


def chunk_text(text: str, doc_name: str, doc_id: str, page_count: int) -> List[Dict]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=MAX_CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    chunks = splitter.split_text(text)
    result = []
    for i, chunk in enumerate(chunks):
        result.append({
            "id": f"{doc_id}_chunk_{i}",
            "text": chunk,
            "metadata": {
                "doc_id": doc_id,
                "doc_name": doc_name,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "page_count": page_count,
            }
        })
    return result


def ingest_file(file_path: str, original_name: str, source: str = "user") -> Dict:
    ext = os.path.splitext(original_name)[1].lower()
    doc_id = hashlib.md5(original_name.encode()).hexdigest()[:12]

    # Extract text
    if ext == ".pdf":
        text, page_count = extract_text_from_pdf(file_path)
        doc_type = "pdf"
    elif ext == ".csv":
        text, page_count = extract_text_from_csv(file_path)
        doc_type = "csv"
    else:
        text, page_count = extract_text_from_txt(file_path)
        doc_type = "txt"

    if not text.strip():
        raise ValueError(f"No text extracted from {original_name}")

    # Chunk
    chunks = chunk_text(text, original_name, doc_id, page_count)

    # Embed & store in ChromaDB
    collection = get_collection()
    batch_size = 50
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i+batch_size]
        texts = [c["text"] for c in batch]
        ids = [c["id"] for c in batch]
        metadatas = [c["metadata"] for c in batch]
        embeddings = embed_texts(texts)
        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas
        )

    size_kb = os.path.getsize(file_path) / 1024

    return {
        "doc_id": doc_id,
        "name": original_name,
        "type": doc_type,
        "size_kb": round(size_kb, 2),
        "chunk_count": len(chunks),
        "page_count": page_count,
        "source": source
    }


def get_all_chunks_for_doc(doc_id: str) -> List[Dict]:
    collection = get_collection()
    results = collection.get(
        where={"doc_id": doc_id},
        include=["documents", "metadatas"]
    )
    chunks = []
    for i, doc in enumerate(results["documents"]):
        chunks.append({
            "text": doc,
            "metadata": results["metadatas"][i]
        })
    return chunks


def delete_doc_from_chroma(doc_id: str):
    collection = get_collection()
    results = collection.get(where={"doc_id": doc_id}, include=[])
    if results["ids"]:
        collection.delete(ids=results["ids"])

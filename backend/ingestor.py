import os
import fitz
import pandas as pd
import hashlib
from pathlib import Path
from typing import List, Dict
import chromadb
from langchain.text_splitter import RecursiveCharacterTextSplitter

CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_db")
MAX_CHUNK_SIZE = int(os.getenv("MAX_CHUNK_SIZE", 1000))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 200))

_client = None
_collection = None

def get_collection():
    global _client, _collection
    if _collection is None:
        _client = chromadb.PersistentClient(path=CHROMA_PATH)
        _collection = _client.get_or_create_collection(
            name="smartrag",
            metadata={"hnsw:space": "cosine"}
        )
    return _collection

def make_doc_id(filename: str) -> str:
    return hashlib.md5(filename.encode()).hexdigest()[:12]

def extract_pdf(path: str):
    doc = fitz.open(path)
    pages = []
    for i, page in enumerate(doc):
        text = page.get_text("text").strip()
        if text:
            pages.append({"text": text, "page": i+1})
    doc.close()
    return pages, len(doc)

def extract_csv(path: str):
    df = pd.read_csv(path)
    rows = []
    for idx, row in df.iterrows():
        text = " | ".join([f"{col}: {val}" for col, val in row.items() if pd.notna(val)])
        if text.strip():
            rows.append({"text": text, "page": idx+1})
    rows.insert(0, {"text": f"Columns: {', '.join(df.columns)}. Rows: {len(df)}", "page": 0})
    return rows, len(df)

def ingest_file(file_path: str, filename: str, source: str = "upload") -> Dict:
    ext = Path(filename).suffix.lower()
    file_size = os.path.getsize(file_path) / 1024

    if ext == ".pdf":
        pages, page_count = extract_pdf(file_path)
        file_type = "pdf"
    elif ext == ".csv":
        pages, page_count = extract_csv(file_path)
        file_type = "csv"
    else:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        pages = [{"text": content, "page": 1}]
        page_count = 1
        file_type = "txt"

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=MAX_CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""]
    )

    collection = get_collection()
    doc_id = make_doc_id(filename)
    chunk_count = 0

    for page_data in pages:
        sub_chunks = splitter.split_text(page_data["text"])
        for i, chunk_text in enumerate(sub_chunks):
            if len(chunk_text.strip()) < 20:
                continue
            chunk_id = f"{doc_id}_p{page_data['page']}_c{i}"
            try:
                collection.add(
                    documents=[chunk_text],
                    metadatas=[{
                        "doc_id": doc_id,
                        "doc_name": filename,
                        "page": page_data["page"],
                        "chunk_index": i,
                        "file_type": file_type,
                        "source": source
                    }],
                    ids=[chunk_id]
                )
                chunk_count += 1
            except Exception:
                pass

    return {
        "doc_id": doc_id,
        "name": filename,
        "type": file_type,
        "size_kb": file_size,
        "chunk_count": chunk_count,
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
    for text, meta in zip(results.get("documents", []), results.get("metadatas", [])):
        chunks.append({"text": text, "metadata": meta})
    return chunks

def delete_doc_from_chroma(doc_id: str) -> int:
    collection = get_collection()
    results = collection.get(where={"doc_id": doc_id}, include=["metadatas"])
    ids = results.get("ids", [])
    if ids:
        collection.delete(ids=ids)
    return len(ids)

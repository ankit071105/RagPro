import os
import csv
import io
import tempfile
import logging
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from database import init_db, add_document, get_all_documents, delete_document, add_query, get_query_history, get_dashboard_stats
from ingestor import ingest_file, get_collection, delete_doc_from_chroma, get_all_chunks_for_doc
from retriever import hybrid_search, format_sources
from generator import classify_intent, generate_answer, generate_comparison
from evaluator import evaluate_response
from features.auto_questions import generate_questions
from features.followup_suggester import suggest_followups
from features.insight_extractor import extract_insights
from kaggle_loader import load_kaggle_dataset

app = FastAPI(title="SmartRAG Pro API", version="1.0.0")

app.add_middleware(CORSMiddleware, allow_origins=["https://rag-pro-three.vercel.app", "http://localhost:3000", "http://localhost:8000", "*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
async def startup():
    init_db()
    logger.info("DB initialized")
    try:
        load_kaggle_dataset()
    except Exception as e:
        logger.warning(f"Kaggle load skipped: {e}")

@app.get("/health")
def health():
    col = get_collection()
    return {"status": "ok", "total_chunks": col.count(), "model": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")}

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    ext = Path(file.filename).suffix.lower()
    if ext not in [".pdf", ".csv", ".txt", ".md"]:
        raise HTTPException(400, f"Unsupported file type: {ext}")
    content = await file.read()
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(400, "File too large. Max 50MB.")
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    try:
        result = ingest_file(tmp_path, file.filename, source="upload")
        add_document(result["doc_id"], result["name"], result["type"], result["size_kb"], result["chunk_count"], result["page_count"], result["source"])
        return {"filename": result["name"], "file_type": result["type"], "chunk_count": result["chunk_count"], "page_count": result["page_count"], "status": "success"}
    finally:
        os.unlink(tmp_path)

@app.get("/documents")
def list_documents():
    docs = get_all_documents()
    return [{"id": d["id"], "filename": d["name"], "file_type": d["type"], "chunk_count": d["chunk_count"], "page_count": d["page_count"], "source": d["source"], "uploaded_at": d["upload_time"]} for d in docs]

@app.delete("/documents/{doc_id}")
def remove_document(doc_id: str):
    docs = get_all_documents()
    doc = next((d for d in docs if d["id"] == doc_id), None)
    if not doc:
        raise HTTPException(404, "Document not found")
    delete_doc_from_chroma(doc_id)
    delete_document(doc_id)
    return {"status": "deleted", "filename": doc["name"]}

class QueryRequest(BaseModel):
    query: str
    filter_doc: Optional[str] = None
    history: Optional[List[dict]] = []

@app.post("/query")
async def query_documents(req: QueryRequest):
    if not req.query.strip():
        raise HTTPException(400, "Query cannot be empty")
    col = get_collection()
    if col.count() == 0:
        raise HTTPException(400, "No documents indexed yet. Please upload documents first.")
    intent = classify_intent(req.query)
    chunks = hybrid_search(req.query, filter_doc=req.filter_doc)
    if not chunks:
        return {"answer": "I couldn't find relevant information in the uploaded documents.", "intent": intent, "sources": [], "scores": {"faithfulness": 0, "relevance": 0, "context_precision": 0, "overall": 0}, "follow_ups": []}
    answer = generate_answer(req.query, chunks, intent, req.history)
    scores = evaluate_response(req.query, answer, chunks)
    sources = format_sources(chunks)
    follow_ups = suggest_followups(req.query, answer)
    add_query(req.query, answer, intent, [], sources, scores, 0)
    return {"answer": answer, "intent": intent, "sources": sources, "scores": scores, "follow_ups": follow_ups}

class CompareRequest(BaseModel):
    query: str
    doc_a: str
    doc_b: str

@app.post("/compare")
async def compare_documents(req: CompareRequest):
    chunks_a = hybrid_search(req.query, filter_doc=req.doc_a, top_k=4)
    chunks_b = hybrid_search(req.query, filter_doc=req.doc_b, top_k=4)
    if not chunks_a and not chunks_b:
        raise HTTPException(400, "No content found in selected documents")
    result = generate_comparison(req.query, chunks_a, chunks_b, req.doc_a, req.doc_b)
    scores = evaluate_response(req.query, result, chunks_a + chunks_b)
    return {"comparison": result, "doc_a": req.doc_a, "doc_b": req.doc_b, "scores": scores}

@app.get("/documents/{doc_id}/questions")
async def get_doc_questions(doc_id: str):
    chunks_data = get_all_chunks_for_doc(doc_id)
    if not chunks_data:
        raise HTTPException(404, "Document not found")
    texts = [c["text"] for c in chunks_data]
    doc_name = chunks_data[0]["metadata"].get("doc_name", doc_id)
    return {"filename": doc_name, "questions": generate_questions(texts, doc_name)}

@app.get("/documents/{doc_id}/insights")
async def get_doc_insights(doc_id: str):
    chunks_data = get_all_chunks_for_doc(doc_id)
    if not chunks_data:
        raise HTTPException(404, "Document not found")
    doc_name = chunks_data[0]["metadata"].get("doc_name", doc_id)
    insights = extract_insights(chunks_data, doc_name)
    return {"filename": doc_name, "insights": insights}

class SearchRequest(BaseModel):
    query: str
    top_k: Optional[int] = 8

@app.post("/search")
async def semantic_search(req: SearchRequest):
    chunks = hybrid_search(req.query, top_k=req.top_k)
    return {"query": req.query, "results": [{"text": c["text"], "filename": c["metadata"].get("doc_name", ""), "page": c["metadata"].get("chunk_index", 0), "score": round(c.get("rrf_score", 0), 4)} for c in chunks]}

@app.get("/history")
def query_history(limit: int = 50):
    rows = get_query_history(limit)
    return [{"id": r["id"], "query": r["query"], "answer": r["answer"], "intent": r.get("intent") or "factoid", "faithfulness": r["faithfulness"], "relevance": r["relevance"], "context_precision": r["context_precision"], "overall_score": r["overall_score"], "sources": r.get("sources", []), "created_at": r["timestamp"]} for r in rows]

@app.get("/history/export")
def export_history():
    history = get_query_history(limit=1000)
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["id","query","intent","faithfulness","relevance","context_precision","overall_score","timestamp"])
    writer.writeheader()
    for r in history:
        writer.writerow({k: r.get(k,"") for k in ["id","query","intent","faithfulness","relevance","context_precision","overall_score","timestamp"]})
    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=query_history.csv"})

@app.get("/dashboard")
def dashboard():
    s = get_dashboard_stats()
    return {"total_docs": s["total_docs"], "total_queries": s["total_queries"], "avg_faithfulness": s["avg_faithfulness"], "avg_relevance": s["avg_relevance"], "avg_score": s["avg_overall"], "intent_distribution": {r["intent"]: r["cnt"] for r in s.get("intent_distribution", []) if r.get("intent")}, "recent_queries": [{"faithfulness": r["faithfulness"], "relevance": r["relevance"], "overall_score": r["overall_score"], "created_at": r["timestamp"]} for r in s.get("recent_scores", [])]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

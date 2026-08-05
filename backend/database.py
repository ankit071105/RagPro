import sqlite3
import os
import json
from datetime import datetime
from typing import List, Dict, Optional

DB_PATH = os.getenv("SQLITE_PATH", "./smart_rag.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            size_kb REAL,
            chunk_count INTEGER DEFAULT 0,
            page_count INTEGER DEFAULT 0,
            upload_time TEXT NOT NULL,
            source TEXT DEFAULT 'user'
        );
        CREATE TABLE IF NOT EXISTS query_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT NOT NULL,
            answer TEXT NOT NULL,
            intent TEXT,
            doc_ids TEXT,
            sources TEXT,
            faithfulness REAL DEFAULT 0,
            relevance REAL DEFAULT 0,
            context_precision REAL DEFAULT 0,
            overall_score REAL DEFAULT 0,
            response_time_ms INTEGER DEFAULT 0,
            timestamp TEXT NOT NULL
        );
    """)
    conn.commit()
    conn.close()


def add_document(doc_id, name, doc_type, size_kb, chunk_count, page_count, source="user"):
    conn = get_conn()
    conn.execute("""
        INSERT OR REPLACE INTO documents
        (id, name, type, size_kb, chunk_count, page_count, upload_time, source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (doc_id, name, doc_type, size_kb, chunk_count, page_count,
          datetime.utcnow().isoformat(), source))
    conn.commit()
    conn.close()


def get_all_documents():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM documents ORDER BY upload_time DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_document(doc_id):
    conn = get_conn()
    conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
    conn.commit()
    conn.close()


def add_query(query, answer, intent, doc_ids, sources, scores, response_time_ms):
    conn = get_conn()
    conn.execute("""
        INSERT INTO query_history
        (query, answer, intent, doc_ids, sources, faithfulness, relevance,
         context_precision, overall_score, response_time_ms, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        query, answer, intent,
        json.dumps(doc_ids),
        json.dumps(sources),
        scores.get("faithfulness", 0),
        scores.get("relevance", 0),
        scores.get("context_precision", 0),
        scores.get("overall", 0),
        response_time_ms,
        datetime.utcnow().isoformat()
    ))
    conn.commit()
    conn.close()


def get_query_history(limit=50):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM query_history ORDER BY timestamp DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["doc_ids"] = json.loads(d.get("doc_ids") or "[]")
        d["sources"] = json.loads(d.get("sources") or "[]")
        result.append(d)
    return result


def get_dashboard_stats():
    conn = get_conn()
    total_docs = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    total_queries = conn.execute("SELECT COUNT(*) FROM query_history").fetchone()[0]
    score_row = conn.execute("""
        SELECT AVG(faithfulness), AVG(relevance), AVG(context_precision), AVG(overall_score)
        FROM query_history
    """).fetchone()
    intent_rows = conn.execute("""
        SELECT intent, COUNT(*) as cnt FROM query_history GROUP BY intent
    """).fetchall()
    recent_scores = conn.execute("""
        SELECT faithfulness, relevance, context_precision, overall_score, timestamp
        FROM query_history ORDER BY timestamp DESC LIMIT 20
    """).fetchall()
    conn.close()
    return {
        "total_docs": total_docs,
        "total_queries": total_queries,
        "avg_faithfulness": round(score_row[0] or 0, 3),
        "avg_relevance": round(score_row[1] or 0, 3),
        "avg_context_precision": round(score_row[2] or 0, 3),
        "avg_overall": round(score_row[3] or 0, 3),
        "intent_distribution": [dict(r) for r in intent_rows],
        "recent_scores": [dict(r) for r in recent_scores],
    }


def doc_exists(doc_id):
    conn = get_conn()
    row = conn.execute("SELECT id FROM documents WHERE id = ?", (doc_id,)).fetchone()
    conn.close()
    return row is not None

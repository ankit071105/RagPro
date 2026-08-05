import os
from typing import List, Dict, Optional
from rank_bm25 import BM25Okapi
from ingestor import get_collection, embed_texts

TOP_K = int(os.getenv("TOP_K_RESULTS", "5"))


def dense_search(query: str, doc_ids: Optional[List[str]] = None, top_k: int = 10) -> List[Dict]:
    collection = get_collection()
    query_embedding = embed_texts([query])[0]

    where_filter = None
    if doc_ids and len(doc_ids) > 0:
        if len(doc_ids) == 1:
            where_filter = {"doc_id": doc_ids[0]}
        else:
            where_filter = {"doc_id": {"$in": doc_ids}}

    kwargs = {
        "query_embeddings": [query_embedding],
        "n_results": min(top_k, max(1, collection.count())),
        "include": ["documents", "metadatas", "distances"]
    }
    if where_filter:
        kwargs["where"] = where_filter

    results = collection.query(**kwargs)

    hits = []
    for i, doc in enumerate(results["documents"][0]):
        distance = results["distances"][0][i]
        score = max(0, 1 - distance)
        hits.append({
            "text": doc,
            "metadata": results["metadatas"][0][i],
            "dense_score": score,
            "rank": i + 1
        })
    return hits


def bm25_search(query: str, doc_ids: Optional[List[str]] = None, top_k: int = 10) -> List[Dict]:
    collection = get_collection()

    where_filter = None
    if doc_ids and len(doc_ids) > 0:
        if len(doc_ids) == 1:
            where_filter = {"doc_id": doc_ids[0]}
        else:
            where_filter = {"doc_id": {"$in": doc_ids}}

    kwargs = {"include": ["documents", "metadatas"]}
    if where_filter:
        kwargs["where"] = where_filter

    all_results = collection.get(**kwargs)

    if not all_results["documents"]:
        return []

    docs = all_results["documents"]
    metadatas = all_results["metadatas"]

    tokenized_corpus = [doc.lower().split() for doc in docs]
    bm25 = BM25Okapi(tokenized_corpus)
    query_tokens = query.lower().split()
    scores = bm25.get_scores(query_tokens)

    ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)[:top_k]

    hits = []
    for rank, (idx, score) in enumerate(ranked):
        if score > 0:
            hits.append({
                "text": docs[idx],
                "metadata": metadatas[idx],
                "bm25_score": score,
                "rank": rank + 1
            })
    return hits


def reciprocal_rank_fusion(dense_hits: List[Dict], bm25_hits: List[Dict], k: int = 60) -> List[Dict]:
    scores = {}
    chunk_map = {}

    for hit in dense_hits:
        chunk_id = hit["metadata"].get("doc_id", "") + str(hit["metadata"].get("chunk_index", 0))
        scores[chunk_id] = scores.get(chunk_id, 0) + 1 / (k + hit["rank"])
        chunk_map[chunk_id] = hit

    for hit in bm25_hits:
        chunk_id = hit["metadata"].get("doc_id", "") + str(hit["metadata"].get("chunk_index", 0))
        scores[chunk_id] = scores.get(chunk_id, 0) + 1 / (k + hit["rank"])
        if chunk_id not in chunk_map:
            chunk_map[chunk_id] = hit

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    results = []
    for chunk_id, rrf_score in ranked:
        hit = chunk_map[chunk_id].copy()
        hit["rrf_score"] = round(rrf_score, 4)
        results.append(hit)
    return results


def hybrid_retrieve(query: str, doc_ids: Optional[List[str]] = None, top_k: int = None) -> List[Dict]:
    if top_k is None:
        top_k = TOP_K

    dense_hits = dense_search(query, doc_ids, top_k=top_k * 2)
    bm25_hits = bm25_search(query, doc_ids, top_k=top_k * 2)
    fused = reciprocal_rank_fusion(dense_hits, bm25_hits)
    return fused[:top_k]


def hybrid_search(query: str, filter_doc: Optional[str] = None, top_k: int = None) -> List[Dict]:
    """Wrapper matching main.py interface — converts filter_doc name to doc_id list"""
    if filter_doc:
        import hashlib
        doc_id = hashlib.md5(filter_doc.encode()).hexdigest()[:12]
        doc_ids = [doc_id]
    else:
        doc_ids = None
    return hybrid_retrieve(query, doc_ids=doc_ids, top_k=top_k)


def format_sources(chunks: List[Dict]) -> List[Dict]:
    seen = set()
    sources = []
    for c in chunks:
        meta = c.get("metadata", {})
        key = meta.get("doc_id", "") + str(meta.get("chunk_index", 0))
        if key not in seen:
            seen.add(key)
            sources.append({
                "filename": meta.get("doc_name", "Unknown"),
                "page": meta.get("chunk_index", 0),
                "file_type": "pdf",
                "preview": c["text"][:200] + "..." if len(c["text"]) > 200 else c["text"],
                "score": round(c.get("rrf_score", 0), 4)
            })
    return sources

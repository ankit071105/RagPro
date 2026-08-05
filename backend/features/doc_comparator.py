import os
from typing import List, Dict
from langchain_groq import ChatGroq
from langchain.schema import HumanMessage
from retriever import hybrid_retrieve

GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

def compare_documents(query: str, doc_id_a: str, doc_id_b: str,
                       doc_name_a: str, doc_name_b: str) -> Dict:
    llm = ChatGroq(model=GROQ_MODEL, temperature=0.2, max_tokens=1500)

    chunks_a = hybrid_retrieve(query, doc_ids=[doc_id_a], top_k=4)
    chunks_b = hybrid_retrieve(query, doc_ids=[doc_id_b], top_k=4)

    context_a = "\n".join([c["text"] for c in chunks_a])[:2000]
    context_b = "\n".join([c["text"] for c in chunks_b])[:2000]

    prompt = f"""Compare these two documents on the topic: "{query}"

Document A - {doc_name_a}:
{context_a}

Document B - {doc_name_b}:
{context_b}

Provide a structured comparison with:
1. Key similarities
2. Key differences
3. Which document covers the topic better and why
4. A brief conclusion

Be specific and cite document names."""
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        return {
            "comparison": response.content.strip(),
            "doc_a": {"name": doc_name_a, "chunks_used": len(chunks_a)},
            "doc_b": {"name": doc_name_b, "chunks_used": len(chunks_b)},
        }
    except Exception as e:
        return {"comparison": f"Comparison failed: {str(e)}", "doc_a": {}, "doc_b": {}}

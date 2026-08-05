import os
from typing import List, Dict, Optional
from langchain_groq import ChatGroq
from langchain.schema import HumanMessage, SystemMessage

GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
_llm = None

def get_llm():
    global _llm
    if _llm is None:
        _llm = ChatGroq(model=GROQ_MODEL, temperature=0.2, max_tokens=1024)
    return _llm

def classify_intent(query: str) -> str:
    llm = get_llm()
    prompt = ('Classify this query into exactly one of: factoid, summary, comparison, conversational\n\nQuery: "' 
              + query + '"\n\nRespond with ONLY one word.')
    response = llm.invoke([HumanMessage(content=prompt)])
    intent = response.content.strip().lower()
    return intent if intent in ["factoid", "summary", "comparison", "conversational"] else "factoid"

def generate_answer(query: str, context_chunks: List[Dict], intent: str,
                    chat_history: Optional[List[Dict]] = None) -> str:
    llm = get_llm()
    parts = []
    for i, chunk in enumerate(context_chunks):
        name = chunk["metadata"].get("doc_name", "Unknown")
        parts.append("[Source " + str(i+1) + " - " + name + "]\n" + chunk["text"])
    context_text = "\n\n".join(parts)
    task_map = {
        "summary": "Provide a comprehensive structured summary with bullet points.",
        "comparison": "Compare with clear similarities and differences.",
        "conversational": "Respond naturally based on context.",
        "factoid": "Provide a precise factual answer from the context."
    }
    system_prompt = ("You are SmartRAG Pro. Answer ONLY from the provided context.\n"
                     "Cite document names. Task: " + task_map.get(intent, task_map["factoid"]))
    user_prompt = "Context:\n" + context_text + "\n\nQuestion: " + query + "\n\nAnswer:"
    response = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)])
    return response.content.strip()

def generate_comparison(query: str, chunks_a: List[Dict], chunks_b: List[Dict],
                        doc_a: str, doc_b: str) -> str:
    llm = get_llm()
    text_a = "\n".join([c["text"] for c in chunks_a[:3]])
    text_b = "\n".join([c["text"] for c in chunks_b[:3]])
    prompt = ("Compare on: " + query + "\n\nDoc A (" + doc_a + "):\n" + text_a +
              "\n\nDoc B (" + doc_b + "):\n" + text_b +
              "\n\nProvide ## Similarities ## Key Differences ## Summary")
    response = llm.invoke([HumanMessage(content=prompt)])
    return response.content.strip()

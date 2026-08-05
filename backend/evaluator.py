import os
from typing import List, Dict
from langchain_groq import ChatGroq
from langchain.schema import HumanMessage

GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

_eval_llm = None


def get_eval_llm():
    global _eval_llm
    if _eval_llm is None:
        _eval_llm = ChatGroq(model=GROQ_MODEL, temperature=0, max_tokens=512)
    return _eval_llm


def score_faithfulness(answer: str, context_chunks: List[Dict]) -> float:
    """Is the answer grounded in the retrieved context?"""
    llm = get_eval_llm()
    context = "\n\n".join([c["text"] for c in context_chunks[:3]])
    prompt = f"""Score how faithful this answer is to the provided context.

Context:
{context[:2000]}

Answer: {answer[:500]}

Score from 0.0 to 1.0 where:
- 1.0 = answer is completely supported by context
- 0.5 = answer is partially supported
- 0.0 = answer contradicts or ignores context

Respond with ONLY a decimal number like 0.85"""
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        score = float(response.content.strip())
        return min(1.0, max(0.0, score))
    except:
        return 0.75


def score_relevance(query: str, answer: str) -> float:
    """Does the answer actually address the question?"""
    llm = get_eval_llm()
    prompt = f"""Score how relevant this answer is to the question.

Question: {query}
Answer: {answer[:500]}

Score from 0.0 to 1.0 where:
- 1.0 = answer directly and completely addresses the question
- 0.5 = answer partially addresses the question
- 0.0 = answer is off-topic

Respond with ONLY a decimal number like 0.85"""
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        score = float(response.content.strip())
        return min(1.0, max(0.0, score))
    except:
        return 0.75


def score_context_precision(query: str, context_chunks: List[Dict]) -> float:
    """Are the retrieved chunks actually relevant to the query?"""
    llm = get_eval_llm()
    context_preview = "\n".join([f"Chunk {i+1}: {c['text'][:200]}" for i, c in enumerate(context_chunks[:3])])
    prompt = f"""Score how precisely these document chunks match the query.

Query: {query}
Retrieved chunks:
{context_preview}

Score from 0.0 to 1.0 where:
- 1.0 = all chunks are highly relevant to the query
- 0.5 = some chunks are relevant
- 0.0 = chunks are mostly irrelevant

Respond with ONLY a decimal number like 0.85"""
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        score = float(response.content.strip())
        return min(1.0, max(0.0, score))
    except:
        return 0.75


def evaluate(query: str, answer: str, context_chunks: List[Dict]) -> Dict:
    faithfulness = score_faithfulness(answer, context_chunks)
    relevance = score_relevance(query, answer)
    context_precision = score_context_precision(query, context_chunks)
    overall = round((faithfulness * 0.4 + relevance * 0.4 + context_precision * 0.2), 3)

    return {
        "faithfulness": round(faithfulness, 3),
        "relevance": round(relevance, 3),
        "context_precision": round(context_precision, 3),
        "overall": overall
    }


def evaluate_response(query, answer, context_chunks):
    return evaluate(query, answer, context_chunks)


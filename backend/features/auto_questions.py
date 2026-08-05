import os
from typing import List, Dict
from langchain_groq import ChatGroq
from langchain.schema import HumanMessage

GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

def generate_auto_questions(chunks: List[Dict], doc_name: str) -> List[str]:
    llm = ChatGroq(model=GROQ_MODEL, temperature=0.5, max_tokens=512)
    sample_text = "\n\n".join([c["text"] for c in chunks[:5]])[:3000]
    prompt = f"""You are analyzing a document called "{doc_name}".

Document excerpt:
{sample_text}

Generate exactly 5 insightful questions that someone reading this document would want to ask.
Make questions specific, not generic. Cover different aspects.

Return ONLY 5 questions, one per line, no numbering, no extra text."""
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        questions = [q.strip() for q in response.content.strip().split("\n") if q.strip()]
        return questions[:5]
    except:
        return [
            f"What are the main topics covered in {doc_name}?",
            f"What are the key findings in {doc_name}?",
            f"What recommendations are made in {doc_name}?",
            f"What methodology is used in {doc_name}?",
            f"What conclusions are drawn in {doc_name}?"
        ]


def generate_questions(chunks, filename, num_questions=5):
    if chunks and isinstance(chunks[0], str):
        chunks = [{"text": c} for c in chunks]
    return generate_auto_questions(chunks, filename)

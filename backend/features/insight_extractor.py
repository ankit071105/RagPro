import os
from typing import List, Dict
from langchain_groq import ChatGroq
from langchain.schema import HumanMessage
import json

GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

def extract_insights(chunks: List[Dict], doc_name: str) -> Dict:
    llm = ChatGroq(model=GROQ_MODEL, temperature=0.2, max_tokens=1024)
    sample_text = "\n\n".join([c["text"] for c in chunks[:8]])[:4000]
    prompt = f"""Analyze this document excerpt from "{doc_name}" and extract structured insights.

Document:
{sample_text}

Return a JSON object with exactly these fields:
{{
  "summary": "3-sentence executive summary",
  "key_topics": ["topic1", "topic2", "topic3", "topic4", "topic5"],
  "key_entities": ["entity1", "entity2", "entity3"],
  "critical_points": ["point1", "point2", "point3"],
  "doc_type": "research_paper|policy|technical_doc|report|other"
}}

Return ONLY valid JSON, no markdown, no extra text."""
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        text = response.content.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text)
    except Exception as e:
        return {
            "summary": f"Document '{doc_name}' contains {len(chunks)} sections of content.",
            "key_topics": ["Content Analysis", "Document Review"],
            "key_entities": [],
            "critical_points": ["Please review the document for specific details"],
            "doc_type": "other"
        }

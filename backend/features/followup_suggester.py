import os
from typing import List
from langchain_groq import ChatGroq
from langchain.schema import HumanMessage

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

def suggest_followups(query: str, answer: str, num: int = 3) -> List[str]:
    llm = ChatGroq(api_key=GROQ_API_KEY, model_name=GROQ_MODEL, temperature=0.6, max_tokens=300)
    
    prompt = f"""Given this Q&A, suggest {num} natural follow-up questions the user might want to ask next.
Make them concise, specific, and directly related to the answer.

Question: {query}
Answer: {answer[:500]}

Return ONLY the follow-up questions, one per line. No numbering, no explanations."""
    
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        lines = [l.strip() for l in response.content.strip().split("\n") if l.strip()]
        return [l for l in lines if len(l) > 10][:num]
    except:
        return []

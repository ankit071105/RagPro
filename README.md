# SmartRAG Pro 
**Document Intelligence Platform — RAG-Based AI Assistant**

Built for Celebal Technologies Internship (CEI 2026)


**Live:** https://rag-pro-three.vercel.app/

**Backend:** https://ragpro-54ww.onrender.com

**PPT LINK** :- [SmartRAG_Pro.pdf](https://github.com/user-attachments/files/30853862/SmartRAG_Pro.pdf)



## Demonstration Video


https://github.com/user-attachments/assets/19e8a323-fa78-409d-8b83-bd734e6f7efd






---

## Features

- **6 Interaction Modes** — Chat, Search, Compare, Explore, Dashboard, History
- **Hybrid Retrieval** — ChromaDB dense + BM25 sparse + Reciprocal Rank Fusion (RRF)
- **Intent Classification** — factoid / summary / comparison / conversational
- **RAGAs Evaluation** — Faithfulness, Relevance, Context Precision per query
- **Auto Question Generator** — 5 smart questions generated per document
- **Insight Extractor** — Summary, key topics, entities, sentiment per document
- **Doc Comparator** — Side-by-side structured comparison of any two documents
- **Follow-up Suggestions** — 3 contextual follow-up questions after every answer
- **Analytics Dashboard** — Chart.js visualizations of RAGAs metrics over time
- **Query History** — Full log with intent filter + CSV export
- **Kaggle Dataset Pre-loading** — Auto-indexes on first startup
- **Dark / Light Theme** — Fully responsive single-file HTML frontend
- **Supports** — PDF, CSV, TXT (batch chunked, 1000 chars / 200 overlap)

---

## Setup

### 1. Prerequisites
- Python 3.11 (required — 3.13/3.14 breaks pydantic)
- Free Groq API key: https://console.groq.com

### 2. Clone & Install
```bash
git clone https://github.com/ankit071105/RagPro.git
cd RagPro/backend

# Create venv with Python 3.11 specifically
/opt/homebrew/bin/python3.11 -m venv venv
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Environment Variables
```bash
cp .env.example .env
# Add your GROQ_API_KEY inside .env
```

### 4. Add Kaggle Dataset (Optional)
```bash
# Place PDF/CSV/TXT files in data/kaggle/
# They auto-index on first startup
```

### 5. Run Backend
```bash
cd backend
./venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 6. Run Frontend
```bash
# In a separate terminal, from project root
python3 -m http.server 3000
# Open: http://localhost:3000
```

---

##  Project Structure
```
SmartRAG-Pro/
├── index.html              ← Complete frontend (1 file)
├── backend/
│   ├── main.py             ← FastAPI routes
│   ├── ingestor.py         ← LangChain doc processing
│   ├── retriever.py        ← Hybrid BM25 + ChromaDB + RRF
│   ├── generator.py        ← Groq LLM + intent classification
│   ├── evaluator.py        ← RAGAs scoring engine
│   ├── kaggle_loader.py    ← Dataset pre-loader
│   ├── database.py         ← SQLite history & metadata
│   ├── features/
│   │   ├── auto_questions.py    ← 5 smart questions per doc
│   │   ├── insight_extractor.py ← Summary + topics + entities
│   │   └── doc_comparator.py    ← Side-by-side comparison
│   └── requirements.txt
├── data/kaggle/            ← Place Kaggle dataset files here
├── .env.example
├── render.yaml
└── README.md
```

---

##  Tech Stack
| Layer | Tool |
|---|---|
| Frontend | HTML + Tailwind CDN + Chart.js + Vanilla JS |
| Backend | FastAPI + Uvicorn |
| Orchestration | LangChain |
| LLM | Groq (llama-3.3-70b-versatile) |
| Embeddings | FastEmbed all-MiniLM-L6-v2 |
| Vector DB | ChromaDB persistent |
| Sparse Search | rank-bm25 |
| Evaluation | RAGAs-style scoring |
| Metadata | SQLite |
| Deployment | Render free tier |

---

## How It Works

```
Upload Document
↓
PyMuPDF / pandas parse → LangChain chunk (1000 chars, 200 overlap)
↓
ChromaDB stores chunks + embeddings + metadata
↓
User asks question
↓
Intent Classifier → factoid / summary / comparison / conversational
↓
Hybrid Retrieval:
ChromaDB dense search (top 10) + BM25 sparse search (top 10)
→ RRF Fusion → top 5 chunks
↓
Groq LLaMA 3.3 70B generates answer (intent-specific prompt)
↓
RAGAs Evaluator scores: Faithfulness + Relevance + Context Precision
↓
Response: answer + sources + scores + follow-up suggestions
```

## Common Issues

```
| Issue | Fix |
|---|---|
| `pydantic` crash on startup   | Use Python 3.11 — not 3.13 or 3.14                    |
| `uvicorn` using wrong Python  | Use `./venv/bin/uvicorn` not system `uvicorn`         |
| Memory limit on Render        | Do not use sentence-transformers — causes OOM         |
| CORS error on frontend        | Add Vercel URL to CORS origins in main.py             |
| Frontend shows Offline        | Open in incognito — ad blocker may block onrender.com |
| Render uses Python 3.14       | Set `PYTHON_VERSION=3.11.9` in Render env vars        |
```
---


Made with ❤️ by Ankit Kumar

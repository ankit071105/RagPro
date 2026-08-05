# SmartRAG Pro 🧠
**Document Intelligence Platform — RAG-Based AI Assistant**

Built for Celebal Technologies Internship (CEI 2026)

---

## 🚀 Features
- **Hybrid Retrieval**: ChromaDB dense + BM25 sparse + Reciprocal Rank Fusion
- **Intent Classification**: factoid / summarization / comparison / conversational
- **RAGAs Evaluation**: Faithfulness, Relevance, Context Precision per query
- **4 Unique Features**: Auto Question Generator, Insight Extractor, Doc Comparator, Follow-up Suggestions
- **Analytics Dashboard**: Chart.js visualizations of all RAGAs metrics
- **Query History**: Full log with CSV export
- **Kaggle Dataset Pre-loading**: Auto-indexes on startup
- **Dark/Light Theme**: Fully responsive single-file HTML frontend
- **Supports**: PDF, TXT, CSV (any size — batch chunked)

---

## ⚙️ Setup

### 1. Clone & Install
```bash
cd backend
pip install -r requirements.txt
```

### 2. Environment Variables
```bash
cp .env.example .env
# Edit .env and add your GROQ_API_KEY
```
Get your free Groq API key at: https://console.groq.com

### 3. Add Kaggle Dataset (Optional)
Place PDF/TXT/CSV files in `data/kaggle/` — they auto-index on startup.

### 4. Run
```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
Open: http://localhost:8000/static/index.html

---

## 🌐 Deploy on Render
1. Push to GitHub
2. Create new Web Service on Render
3. Set environment variables (GROQ_API_KEY)
4. Build command: `pip install -r backend/requirements.txt`
5. Start command: `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT`

---

## 📁 Project Structure
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

## 🛠 Tech Stack
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

Made with ❤️ by Ankit Kumar

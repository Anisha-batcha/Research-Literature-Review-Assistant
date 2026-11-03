# Research Literature Review Assistant

Search arXiv for a research topic, review the resulting papers, generate a
citation-supported literature review, and ask questions grounded in the paper
abstracts. The app combines a React/Vite frontend with a FastAPI backend,
Sentence Transformers, FAISS, and the Groq API.

## Features

- Search arXiv and filter by year range and category; sort by relevance or newest.
- Select which papers to include in a generated review.
- Click review citations to open their arXiv records.
- Export the review and linked bibliography as Markdown.
- Ask questions and see the retrieved source papers.

The app uses arXiv metadata and abstracts, not full-text paper contents.
Generated reviews and answers require a Groq API key.

## Requirements

- Python 3.10+
- Node.js 20.19+ or 22.12+
- A Groq API key for review and Q&A generation

## Local setup

From the project root, create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Set `GROQ_API_KEY` in `.env`. Then install and start the frontend:

```powershell
cd frontend
npm ci
npm run dev
```

In a second terminal at the project root, start the API:

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

Open the frontend URL printed by Vite (normally http://127.0.0.1:5173).
The Vite development server proxies `/api` requests to the backend.

To serve the production frontend from FastAPI:

```powershell
cd frontend
npm ci
npm run build
cd ..
python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

Then open http://127.0.0.1:8000.

## Tests and production build

Run backend tests from the project root:

```powershell
python -m unittest discover -s tests
```

Build the frontend:

```powershell
cd frontend
npm run build
```

## Configuration and deployment

Never commit `.env` or a real API key. Configure `GROQ_API_KEY` in the
deployment platform's secret settings. The backend keeps paper search sessions
in process memory, so use a single backend worker unless session storage is
moved to a shared store.

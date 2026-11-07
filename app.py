import logging
import os
import time
import uuid
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.fetch_arxiv import search_arxiv
from src.generate import generate_literature_review, generate_qa_answer
from src.vectorstore import build_index, search_index


ROOT = Path(__file__).parent
load_dotenv(dotenv_path=ROOT / ".env")

logger = logging.getLogger(__name__)
app = FastAPI(title="Research Literature Review Assistant")


@app.get("/api/status")
def get_status():
    return {"groq_configured": bool(os.getenv("GROQ_API_KEY"))}


@dataclass
class PaperSession:
    topic: str
    papers: list[dict]
    index: object
    last_accessed: float


paper_sessions: dict[str, PaperSession] = {}
SESSION_TTL_SECONDS = 60 * 60


class SearchRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=500)
    max_results: int = Field(default=15, ge=5, le=30)
    year_from: int | None = Field(default=None, ge=1900, le=2100)
    year_to: int | None = Field(default=None, ge=1900, le=2100)
    category: str | None = Field(default=None, pattern=r"^[a-z-]+\.[A-Za-z-]+$")
    sort_by: str = Field(default="relevance", pattern=r"^(relevance|submittedDate)$")


class SessionRequest(BaseModel):
    session_id: uuid.UUID


class ReviewRequest(SessionRequest):
    paper_indices: list[int] = Field(min_length=1, max_length=30)


class QuestionRequest(SessionRequest):
    question: str = Field(min_length=1, max_length=2000)


def get_paper_session(session_id: uuid.UUID) -> PaperSession:
    session = paper_sessions.get(str(session_id))
    if session is None:
        raise HTTPException(
            status_code=404,
            detail="Your paper search has expired. Search the topic again.",
        )
    session.last_accessed = time.monotonic()
    return session


@app.post("/api/search")
def search_papers(request: SearchRequest):
    topic = request.topic.strip()
    if not topic:
        raise HTTPException(status_code=422, detail="Please enter a research topic.")

    try:
        if request.year_from and request.year_to and request.year_from > request.year_to:
            raise HTTPException(
                status_code=422,
                detail="The starting year must not be later than the ending year.",
            )

        papers = search_arxiv(
            topic,
            max_results=request.max_results,
            year_from=request.year_from,
            year_to=request.year_to,
            category=request.category,
            sort_by=request.sort_by,
        )
        if not papers:
            return {"session_id": None, "papers": [], "year_counts": {}}

        index = build_index(
            [f"{paper['title']}. {paper['summary']}" for paper in papers]
        )

        now = time.monotonic()
        expired_sessions = [
            session_id
            for session_id, session in paper_sessions.items()
            if now - session.last_accessed > SESSION_TTL_SECONDS
        ]
        for session_id in expired_sessions:
            del paper_sessions[session_id]

        session_id = str(uuid.uuid4())
        paper_sessions[session_id] = PaperSession(
            topic=topic,
            papers=papers,
            index=index,
            last_accessed=now,
        )
        return {
            "session_id": session_id,
            "papers": papers,
            "year_counts": dict(Counter(paper["year"] for paper in papers)),
        }
    except HTTPException:
        raise
    except Exception as error:
        logger.exception("Paper search failed")
        raise HTTPException(
            status_code=502,
            detail=f"Something went wrong fetching papers: {error}",
        ) from error


@app.post("/api/review")
def write_review(request: ReviewRequest):
    session = get_paper_session(request.session_id)
    if (
        len(set(request.paper_indices)) != len(request.paper_indices)
        or any(index < 0 or index >= len(session.papers) for index in request.paper_indices)
    ):
        raise HTTPException(status_code=422, detail="The selected paper list is invalid.")

    selected_papers = [session.papers[index] for index in request.paper_indices]
    try:
        review = generate_literature_review(session.topic, selected_papers)
        citations = {
            str(citation_number): {
                "index": request.paper_indices[citation_number - 1],
                "title": paper["title"],
                "url": paper["url"],
            }
            for citation_number, paper in enumerate(selected_papers, start=1)
        }
        return {"review": review, "citations": citations}
    except HTTPException:
        raise
    except Exception as error:
        logger.exception("Literature review generation failed")
        raise HTTPException(
            status_code=502,
            detail=f"Something went wrong generating the literature review: {error}",
        ) from error


@app.post("/api/question")
def ask_question(request: QuestionRequest):
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=422, detail="Please type a question first.")

    session = get_paper_session(request.session_id)
    try:
        top_indices, _ = search_index(
            session.index, question, k=min(5, len(session.papers))
        )
        relevant_papers = [session.papers[index] for index in top_indices]
        answer = generate_qa_answer(question, relevant_papers)
        return {
            "answer": answer,
            "sources": [
                {
                    "index": int(index),
                    "title": session.papers[index]["title"],
                    "url": session.papers[index]["url"],
                }
                for index in top_indices
            ],
        }
    except HTTPException:
        raise
    except Exception as error:
        logger.exception("Question answering failed")
        raise HTTPException(
            status_code=502,
            detail=f"Something went wrong answering the question: {error}",
        ) from error


frontend_dist = ROOT / "frontend" / "dist"
if frontend_dist.is_dir():
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")

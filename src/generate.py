"""
LLM Generation Module
------------------------
Two modes, both using Groq's free API (currently GPT-OSS / Qwen models -
model availability changes over time; verify with GET
https://api.groq.com/openai/v1/models if this ever needs updating):

1. generate_literature_review() - synthesizes a structured lit review
   across ALL fetched papers at once (their abstracts are short enough
   to fit directly in the prompt, so no retrieval needed here).

2. generate_qa_answer() - classic RAG: answers a specific question
   using only the top-k papers retrieved from the FAISS index.

Requires a free Groq API key:
1. Go to https://console.groq.com/keys
2. Sign in (no card required) and create an API key
3. Put it in a .env file in the project root as:
   GROQ_API_KEY=your_key_here
"""

import os
import time
import requests

MODEL_CANDIDATES = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "qwen/qwen3.8-27b",
]

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


def _try_model(model, api_key, prompt, retries_per_model=2, max_tokens=1500):
    """
    Try one model, with a couple of quick retries for transient errors.
    Returns (answer_text, None) on success, or (None, reason_string) if
    this model should be given up on (so the caller can try the next one
    and report a useful reason if everything fails).
    """
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": max_tokens,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    last_reason = "unknown error"

    for attempt in range(retries_per_model):
        try:
            response = requests.post(GROQ_URL, headers=headers, json=payload, timeout=60)

            if response.status_code in (429, 503):
                last_reason = f"{model}: HTTP {response.status_code} - {response.text[:200]}"
                if attempt < retries_per_model - 1:
                    time.sleep(2 * (attempt + 1))
                    continue
                return None, last_reason

            if response.status_code == 404:
                return None, f"{model}: HTTP 404 - model not found for this API key/version"

            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip(), None

        except requests.exceptions.HTTPError as e:
            last_reason = f"{model}: {e} - {getattr(e.response, 'text', '')[:200]}"
            if attempt < retries_per_model - 1:
                time.sleep(2 * (attempt + 1))
                continue
            return None, last_reason
        except Exception as e:
            return None, f"{model}: {type(e).__name__}: {e}"

    return None, last_reason


def _call_groq(prompt, max_tokens=1500):
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not configured. Add it to the project .env file."
        )

    reasons = []
    for model in MODEL_CANDIDATES:
        result, reason = _try_model(model, api_key, prompt, max_tokens=max_tokens)
        if result is not None:
            return result
        reasons.append(reason)

    reasons_text = " | ".join(reasons)
    raise RuntimeError(
        "Groq could not generate a response using the available models. "
        f"Details: {reasons_text}"
    )


def generate_literature_review(topic, papers):
    """
    Synthesize a structured literature review across all fetched papers.
    `papers` is a list of dicts with title, authors, year, summary, url.
    """
    papers_block = "\n\n".join(
        f"[{i + 1}] {p['title']} ({', '.join(p['authors']) if p['authors'] else 'Unknown'}, {p['year']})\n"
        f"Abstract: {p['summary']}"
        for i, p in enumerate(papers)
    )

    prompt = f"""You are helping write a literature review on the topic: "{topic}".

Below are {len(papers)} papers (numbered) with their abstracts.

{papers_block}

Write a structured literature review with these sections:
1. **Overview** - 2-3 sentences on the overall theme across these papers.
2. **Key Themes** - group the papers into 2-4 thematic clusters, describing
   what each cluster focuses on. Cite papers using their bracket number, e.g. [1], [3].
3. **Trends Over Time** - briefly note any shift in focus or methods across years,
   based on the publication years given.
4. **Gaps / Future Directions** - 2-3 sentences on what seems under-explored.

Use ONLY the information in the abstracts above. Cite every claim with the
bracket number(s) of the paper(s) it comes from. Do not invent papers or facts
not present above."""

    return _call_groq(prompt, max_tokens=2000)


def generate_qa_answer(question, relevant_papers):
    """
    Answer a specific question using only the retrieved papers (RAG-style).
    `relevant_papers` is a list of paper dicts (title, authors, year, summary).
    """
    context = "\n\n---\n\n".join(
        f"Title: {p['title']} ({p['year']})\nAuthors: {', '.join(p['authors']) if p['authors'] else 'Unknown'}\n"
        f"Abstract: {p['summary']}"
        for p in relevant_papers
    )

    prompt = f"""Answer the question using ONLY the paper abstracts below.
If the answer isn't contained in them, say
"I don't have enough information in the retrieved papers to answer that."
Cite the paper title(s) you used in your answer.

Papers:
{context}

Question: {question}

Answer:"""

    return _call_groq(prompt, max_tokens=800)
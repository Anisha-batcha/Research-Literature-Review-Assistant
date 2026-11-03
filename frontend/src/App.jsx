import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";

const initialPaperCount = 15;

function linkifyCitations(text, citations) {
  return text.replace(/\[(\d+)\]/g, (match, number) => {
    const citation = citations[number];
    return citation?.url ? `[${number}](<${citation.url}>)` : match;
  });
}

function downloadReview(topic, review, citations) {
  const bibliography = Object.entries(citations)
    .map(
      ([number, paper]) =>
        `[${number}] ${paper.title}${paper.url ? ` — ${paper.url}` : ""}`,
    )
    .join("\n");
  const contents = `${linkifyCitations(review, citations)}\n\n## References\n\n${bibliography}\n`;
  const blobUrl = URL.createObjectURL(
    new Blob([contents], { type: "text/markdown;charset=utf-8" }),
  );
  const link = document.createElement("a");
  const filename = topic
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
  link.href = blobUrl;
  link.download = `${filename || "literature-review"}.md`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(blobUrl), 0);
}

async function postJson(path, payload) {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || `Request failed (${response.status}).`);
  }
  return data;
}

function SectionHeading({ step, icon, children }) {
  return (
    <div className="section-heading">
      <span className="step-badge" aria-hidden="true">
        <span>{icon}</span>
      </span>
      <span className="section-title">
        <span className="step-number">{step}</span>
        {children}
      </span>
    </div>
  );
}

function PublicationChart({ yearCounts }) {
  const entries = Object.entries(yearCounts).sort(([a], [b]) =>
    a.localeCompare(b),
  );
  const maximum = Math.max(...entries.map(([, count]) => count), 1);

  return (
    <div
      className="chart"
      role="img"
      aria-label={`Papers by publication year: ${entries
        .map(([year, count]) => `${year}: ${count}`)
        .join(", ")}`}
    >
      {entries.map(([year, count]) => (
        <div className="chart-column" key={year}>
          <span className="chart-count">{count}</span>
          <div className="chart-bar-track">
            <div
              className="chart-bar"
              style={{ height: `${Math.max((count / maximum) * 100, 4)}%` }}
            />
          </div>
          <span className="chart-year">{year}</span>
        </div>
      ))}
    </div>
  );
}

function PaperList({ papers, selectedIndices, onSelectionChange }) {
  return (
    <details className="paper-list">
      <summary>View all {papers.length} papers</summary>
      <div className="paper-list-content">
        {papers.map((paper, index) => (
          <article className="paper-card" key={`${paper.url}-${index}`}>
            <label className="paper-selection">
              <input
                type="checkbox"
                checked={selectedIndices.includes(index)}
                onChange={(event) => onSelectionChange(index, event.target.checked)}
              />
              Include in review
            </label>
            <div className="paper-title">
              [{index + 1}] {paper.title}
            </div>
            <div className="paper-meta">
              {paper.authors?.length
                ? paper.authors.join(", ")
                : "Unknown authors"}{" "}
              · {paper.year} ·{" "}
              {paper.url ? (
                <a href={paper.url} target="_blank" rel="noreferrer">
                  arXiv link
                </a>
              ) : (
                "arXiv link unavailable"
              )}
            </div>
            <p className="paper-abstract">{paper.summary}</p>
          </article>
        ))}
      </div>
    </details>
  );
}

export default function App() {
  const [topic, setTopic] = useState("");
  const [paperCount, setPaperCount] = useState(initialPaperCount);
  const [yearFrom, setYearFrom] = useState("");
  const [yearTo, setYearTo] = useState("");
  const [category, setCategory] = useState("");
  const [sortBy, setSortBy] = useState("relevance");
  const [sessionId, setSessionId] = useState(null);
  const [papers, setPapers] = useState([]);
  const [selectedIndices, setSelectedIndices] = useState([]);
  const [yearCounts, setYearCounts] = useState({});
  const [searching, setSearching] = useState(false);
  const [reviewing, setReviewing] = useState(false);
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState("");
  const [review, setReview] = useState("");
  const [citations, setCitations] = useState({});
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState([]);
  const [groqConfigured, setGroqConfigured] = useState(true);

  useEffect(() => {
    fetch("/api/status")
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`Request failed (${response.status}).`);
        }
        return response.json();
      })
      .then((status) => setGroqConfigured(status.groq_configured))
      .catch((requestError) => setError(requestError.message));
  }, []);

  async function handleSearch(event) {
    event.preventDefault();
    if (!topic.trim()) {
      setError("Please enter a topic first.");
      return;
    }

    setSearching(true);
    setError("");
    try {
      const result = await postJson("/api/search", {
        topic: topic.trim(),
        max_results: paperCount,
        year_from: yearFrom ? Number(yearFrom) : null,
        year_to: yearTo ? Number(yearTo) : null,
        category: category || null,
        sort_by: sortBy,
      });
      if (!result.papers.length) {
        setPapers([]);
        setSelectedIndices([]);
        setSessionId(null);
        setYearCounts({});
        setReview("");
        setCitations({});
        setAnswer("");
        setSources([]);
        setError(
          "No papers found for this topic. Try broader or different keywords.",
        );
        return;
      }

      setPapers(result.papers);
      setSelectedIndices(result.papers.map((_, index) => index));
      setYearCounts(result.year_counts);
      setSessionId(result.session_id);
      setReview("");
      setCitations({});
      setAnswer("");
      setSources([]);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSearching(false);
    }
  }

  async function handleReview() {
    setReviewing(true);
    setError("");
    try {
      const result = await postJson("/api/review", {
        session_id: sessionId,
        paper_indices: selectedIndices,
      });
      setReview(result.review);
      setCitations(result.citations);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setReviewing(false);
    }
  }

  async function handleQuestion(event) {
    event.preventDefault();
    if (!question.trim()) {
      setError("Please type a question first.");
      return;
    }

    setAsking(true);
    setError("");
    try {
      const result = await postJson("/api/question", {
        session_id: sessionId,
        question: question.trim(),
      });
      setAnswer(result.answer);
      setSources(result.sources);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setAsking(false);
    }
  }

  function handlePaperSelection(index, included) {
    setSelectedIndices((current) =>
      included
        ? [...current, index].sort((a, b) => a - b)
        : current.filter((selectedIndex) => selectedIndex !== index),
    );
    setReview("");
    setCitations({});
  }

  return (
    <main className="page-shell">
      <header className="main-header">
        <div className="header-icon" aria-hidden="true">
          ◫
        </div>
        <h1>Research Literature Review Assistant</h1>
        <p>
          Give it a topic. It searches arXiv, reviews the papers, and drafts a
          structured summary.
        </p>
      </header>

      {!groqConfigured && (
        <aside className="notice" role="status">
          Check that <code>GROQ_API_KEY</code> is set in the project{" "}
          <code>.env</code> file to generate literature reviews and answers.
        </aside>
      )}

      <section className="panel search-panel">
        <SectionHeading step="1" icon="⌕">
          Search a Topic
        </SectionHeading>
        <form onSubmit={handleSearch}>
          <div className="search-controls">
            <label className="sr-only" htmlFor="topic">
              Research topic
            </label>
            <input
              id="topic"
              className="topic-input"
              value={topic}
              onChange={(event) => setTopic(event.target.value)}
              placeholder="e.g. root-knot nematode detection deep learning"
            />
            <label className="paper-slider" htmlFor="paper-count">
              <span>{paperCount}</span>
              <input
                id="paper-count"
                type="range"
                min="5"
                max="30"
                value={paperCount}
                onChange={(event) => setPaperCount(Number(event.target.value))}
              />
              <span className="range-labels">
                <span>5</span>
                <span>30</span>
              </span>
            </label>
          </div>
          <div className="search-filters">
            <label>
              From year
              <input
                type="number"
                min="1900"
                max="2100"
                value={yearFrom}
                onChange={(event) => setYearFrom(event.target.value)}
                placeholder="Any"
              />
            </label>
            <label>
              To year
              <input
                type="number"
                min="1900"
                max="2100"
                value={yearTo}
                onChange={(event) => setYearTo(event.target.value)}
                placeholder="Any"
              />
            </label>
            <label>
              arXiv category
              <select value={category} onChange={(event) => setCategory(event.target.value)}>
                <option value="">All categories</option>
                <option value="cs.AI">Artificial Intelligence (cs.AI)</option>
                <option value="cs.CL">Computation and Language (cs.CL)</option>
                <option value="cs.CV">Computer Vision (cs.CV)</option>
                <option value="cs.LG">Machine Learning (cs.LG)</option>
                <option value="stat.ML">Statistics - Machine Learning (stat.ML)</option>
                <option value="q-bio.NC">Neurons and Cognition (q-bio.NC)</option>
                <option value="physics.comp-ph">Computational Physics</option>
              </select>
            </label>
            <label>
              Sort by
              <select value={sortBy} onChange={(event) => setSortBy(event.target.value)}>
                <option value="relevance">Relevance</option>
                <option value="submittedDate">Newest first</option>
              </select>
            </label>
          </div>
          <button className="primary-button" type="submit" disabled={searching}>
            {searching ? (
              <>
                <span className="spinner" aria-hidden="true" />
                Searching arXiv and indexing papers…
              </>
            ) : (
              <>
                <span aria-hidden="true">⌕</span>
                Search &amp; Analyze
              </>
            )}
          </button>
        </form>
      </section>

      {error && (
        <div className="error-message" role="alert">
          {error}
        </div>
      )}

      {papers.length > 0 && (
        <>
          <section className="panel">
            <SectionHeading step="2" icon="▥">
              Papers Found &amp; Publication Trend
            </SectionHeading>
            <PublicationChart yearCounts={yearCounts} />
            <PaperList
              papers={papers}
              selectedIndices={selectedIndices}
              onSelectionChange={handlePaperSelection}
            />
          </section>

          <section className="panel">
            <SectionHeading step="3" icon="▤">
              Generate Literature Review
            </SectionHeading>
            <button
              className="primary-button"
              type="button"
              onClick={handleReview}
              disabled={reviewing || selectedIndices.length === 0}
            >
              {reviewing ? (
                <>
                  <span className="spinner" aria-hidden="true" />
                  Synthesizing across all papers…
                </>
              ) : (
                `Write Literature Review (${selectedIndices.length} selected)`
              )}
            </button>
            {review && (
              <>
                <div className="review-actions">
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={() => downloadReview(topic, review, citations)}
                  >
                    Download review and bibliography (.md)
                  </button>
                </div>
                <div className="answer-box markdown-content">
                  <ReactMarkdown>{linkifyCitations(review, citations)}</ReactMarkdown>
                </div>
              </>
            )}
          </section>

          <section className="panel">
            <SectionHeading step="4" icon="?">
              Ask a Specific Question
            </SectionHeading>
            <form onSubmit={handleQuestion}>
              <label className="sr-only" htmlFor="question">
                Question
              </label>
              <input
                id="question"
                className="question-input"
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                placeholder="e.g. What datasets were used across these papers?"
              />
              <button
                className="primary-button"
                type="submit"
                disabled={asking}
              >
                {asking ? (
                  <>
                    <span className="spinner" aria-hidden="true" />
                    Retrieving papers and generating answer…
                  </>
                ) : (
                  "Ask"
                )}
              </button>
            </form>
            {answer && (
              <>
                <div className="answer-box markdown-content">
                  <ReactMarkdown>{answer}</ReactMarkdown>
                </div>
                <div className="source-list" aria-label="Retrieved paper sources">
                  {sources.map((source) => (
                    <a
                      className="source-chip"
                      href={source.url}
                      key={source.index}
                      target="_blank"
                      rel="noreferrer"
                    >
                      [{source.index + 1}] {source.title}
                    </a>
                  ))}
                </div>
              </>
            )}
          </section>
        </>
      )}

      <footer className="footer-note">
        Built with React · arXiv API · Sentence-Transformers · FAISS · Groq
      </footer>
    </main>
  );
}

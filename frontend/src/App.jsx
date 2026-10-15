import { useState } from "react";
import "./App.css";

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"
).replace(/\/+$/, "");

const EXAMPLE_QUESTIONS = [
  "What is the penalty for selling adulterated goods?",
  "How long do I have to file a consumer complaint?",
  "ভেজাল পণ্য বিক্রি করলে কী শাস্তি হতে পারে?",
];

function renderAnswer(text, sources) {
  const parts = text.split(/(\[S\d+\]|\*\*[^*]+\*\*)/g);

  return parts.map((part, index) => {
    const citation = part.match(/^\[(S\d+)\]$/);

    if (citation) {
      const source = sources.find(
        (item) => item.source_id === citation[1],
      );

      return source ? (
        <a
          className="citation"
          href={`#source-${source.source_id}`}
          key={index}
          title={`View Section ${source.section_number}`}
        >
          {part}
        </a>
      ) : (
        <span key={index}>{part}</span>
      );
    }

    const bold = part.match(/^\*\*([^*]+)\*\*$/);

    if (bold) {
      return <strong key={index}>{bold[1]}</strong>;
    }

    return <span key={index}>{part}</span>;
  });
}

function App() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function askQuestion(value = question) {
    const cleanQuestion = value.trim();

    if (cleanQuestion.length < 3 || loading) return;

    setQuestion(cleanQuestion);
    setLoading(true);
    setError("");
    setAnswer(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/ask`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ question: cleanQuestion }),
      });

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(
          data.detail || `Request failed (${response.status})`,
        );
      }

      const data = await response.json();
      setAnswer(data);
    } catch (err) {
      setError(
        err instanceof TypeError
          ? "Could not connect to BanglaLawAI. Make sure the backend is running and its URL is correct."
          : err.message || "Something went wrong. Please try again.",
      );
    } finally {
      setLoading(false);
    }
  }

  function handleSubmit(event) {
    event.preventDefault();
    askQuestion();
  }

  function startNewQuestion() {
    setQuestion("");
    setAnswer(null);
    setError("");
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <a
          className="brand"
          href="#top"
          onClick={startNewQuestion}
          aria-label="BanglaLawAI home"
        >
          <span className="brand-mark" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none">
              <path
                d="M12 3 4.5 6v5.5c0 4.5 3.2 7.7 7.5 9.5 4.3-1.8 7.5-5 7.5-9.5V6L12 3Z"
                stroke="currentColor"
                strokeWidth="1.7"
                strokeLinejoin="round"
              />
              <path
                d="m8.5 12 2.2 2.2 4.8-5"
                stroke="currentColor"
                strokeWidth="1.7"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </span>
          <span className="brand-name">
            BanglaLaw<span>AI</span>
          </span>
        </a>

        <div className="topbar-note">
          <span className="status-dot" />
          Bangladesh consumer rights law
        </div>
      </header>

      <main className="main-content" id="top">
        <section className="hero">
          <div className="eyebrow">
            <span className="eyebrow-line" />
            LEGAL INFORMATION, MADE CLEAR
          </div>

          <h1>
            Understand your rights.
            <br />
            <span>Ask in your language.</span>
          </h1>

          <p className="hero-description">
            Ask questions about Bangladesh’s Consumer Rights Protection Act,
            2009. Get concise answers grounded in the law, with sources you
            can check.
          </p>

          <div className="scope-note">
            <span aria-hidden="true">⚖</span>
            <span>
              Focused on the Consumer Rights Protection Act, 2009
            </span>
          </div>
        </section>

        <section className="workspace" aria-label="Legal question assistant">
          <form className="question-form" onSubmit={handleSubmit}>
            <label className="input-label" htmlFor="question">
              YOUR QUESTION
              <span>English or বাংলা</span>
            </label>

            <textarea
              id="question"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Ask about consumer rights, complaints, penalties..."
              rows={3}
              maxLength={1000}
              disabled={loading}
            />

            <div className="form-footer">
              <span className="character-count">
                {question.length}/1000
              </span>

              <button
                className="ask-button"
                type="submit"
                disabled={loading || question.trim().length < 3}
              >
                {loading ? (
                  <>
                    <span className="spinner" />
                    Searching the law...
                  </>
                ) : (
                  <>
                    Ask BanglaLawAI
                    <span aria-hidden="true">↗</span>
                  </>
                )}
              </button>
            </div>
          </form>

          {!answer && !loading && !error && (
            <div className="examples">
              <p className="section-kicker">TRY ASKING</p>
              {EXAMPLE_QUESTIONS.map((example) => (
                <button
                  className="example-question"
                  key={example}
                  type="button"
                  onClick={() => askQuestion(example)}
                >
                  <span>{example}</span>
                  <span className="example-arrow" aria-hidden="true">
                    ↗
                  </span>
                </button>
              ))}
            </div>
          )}

          {loading && (
            <div className="loading-panel" role="status" aria-live="polite">
              <span className="loading-orb">
                <span />
              </span>
              <div>
                <strong>Looking up the relevant law</strong>
                <p>Retrieving legal passages and preparing your answer.</p>
              </div>
            </div>
          )}

          {error && (
            <div className="error-panel" role="alert">
              <strong>We couldn’t answer that yet.</strong>
              <p>{error}</p>
              <button
                type="button"
                className="text-button"
                onClick={() => askQuestion(question)}
              >
                Try again →
              </button>
            </div>
          )}

          {answer && (
            <section className="answer-panel" aria-live="polite">
              <div className="answer-heading">
                <div>
                  <p className="section-kicker">YOUR ANSWER</p>
                  <h2>What the law says</h2>
                </div>
                <span className="grounded-label">
                  <span className="status-dot" />
                  Sources retrieved
                </span>
              </div>

              <div className="answer-body">
                {renderAnswer(answer.answer, answer.sources || [])}
              </div>

              <div className="answer-disclaimer">
                This tool provides legal information, not personalized legal
                advice. Check the cited law for the full legal wording.
              </div>

              <div className="sources-heading">
                <div>
                  <p className="section-kicker">VERIFY THE ANSWER</p>
                  <h3>Legal sources</h3>
                </div>
                <span className="source-count">
                  {(answer.sources || []).length} cited
                </span>
              </div>

              {(answer.sources || []).length === 0 ? (
                <p className="no-sources">
                  No sources were cited for this answer. Verify the information
                  independently before relying on it.
                </p>
              ) : (
                <div className="source-list">
                  {answer.sources.map((source) => (
                    <details
                      className="source-item"
                      id={`source-${source.source_id}`}
                      key={source.source_id}
                    >
                      <summary>
                        <span className="source-tag">
                          {source.source_id}
                        </span>
                        <span className="source-title">
                          <strong>
                            Section {source.section_number}
                          </strong>
                          <span>{source.title}</span>
                        </span>
                        <span className="source-chevron" aria-hidden="true">
                          +
                        </span>
                      </summary>

                      <div className="source-details">
                        <p>
                          <strong>Act:</strong> Consumer Rights Protection
                          Act, 2009
                        </p>
                        {source.url && (
                          <a
                            href={source.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="source-link"
                          >
                            Read the official legal source ↗
                          </a>
                        )}
                      </div>
                    </details>
                  ))}
                </div>
              )}

              <button
                className="new-question-button"
                type="button"
                onClick={startNewQuestion}
              >
                + Ask another question
              </button>
            </section>
          )}
        </section>

        <footer className="page-footer">
          <span>BanglaLawAI</span>
          <span>Built for clearer access to consumer rights law in Bangladesh.</span>
        </footer>
      </main>
    </div>
  );
}

export default App;
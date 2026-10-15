# BanglaLawAI

**A bilingual Bangla–English AI legal assistant for Bangladesh's Consumers' Right Protection Act, 2009.**

BanglaLawAI is a Retrieval-Augmented Generation (RAG) application that helps users find relevant provisions of Bangladesh's consumer protection law and receive answers grounded in retrieved legal text.

The project combines semantic search, vector databases, and large language models to generate answers with section citations.

> **Disclaimer:** BanglaLawAI is an educational and informational project, not a substitute for professional legal advice. Verify relevant provisions against authoritative legal sources before making legal decisions.

## Features

- Ask questions in Bangla or English.
- Retrieve relevant legal sections using vector similarity search.
- Generate answers grounded in retrieved legal evidence.
- Include section citations in generated answers.
- Provide a REST API using FastAPI.
- Offer a web interface built with React and Vite.
- Evaluate retrieval quality and answer correctness using automated tests.

## Tech Stack

| Component | Technology |
|---|---|
| Backend API | Python, FastAPI, Uvicorn |
| Frontend | React, Vite |
| LLM inference | Groq API — `openai/gpt-oss-20b` |
| Embeddings | Google Gemini — `gemini-embedding-001` |
| Embedding dimensions | 3072 |
| Vector database | PostgreSQL, pgvector |
| Testing | pytest |

## Architecture

```text
User
  |
  v
React + Vite Frontend
  |
  | POST /api/v1/ask
  v
FastAPI Backend
  |
  v
Retriever
  |
  v
PostgreSQL + pgvector
  |
  v
Relevant Legal Sections
  |
  v
Groq LLM
  |
  v
Answer with Section Citations
```

## Project Structure

```text
BanglaLaw-AI/
├── frontend/                 # React + Vite frontend
├── tests/                    # Automated tests
├── data/
│   ├── cleaned/              # Cleaned legal corpus
│   ├── evaluation/           # Evaluation datasets
│   ├── processed/            # Processed retrieval chunks
│   └── metadata.jsonl        # Source metadata
├── main.py                   # FastAPI application
├── answer_service.py         # Answer generation and citation handling
├── retriever.py              # Vector retrieval
├── scraper.py                # Legal source collection
├── clean_corpus.py           # Corpus cleaning
├── chunk_sections.py         # Document chunking
├── build_vectorstore.py      # Vector-store construction
├── evaluate_retrieval.py     # Retrieval evaluation
├── evaluate_answers.py       # Answer evaluation
├── evaluate_live_answers.py  # Live answer evaluation
├── collect_actual_answers.py # Evaluation helper
├── requirements.txt          # Python dependencies
└── README.md
```

## Prerequisites

- Python 3.14 or a compatible Python version
- Node.js and npm
- PostgreSQL with the `pgvector` extension
- Groq API key
- Google AI API key with access to the configured embedding model

## Installation

### 1. Clone the repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd BanglaLaw-AI
```

Replace the placeholder with your actual GitHub repository URL.

### 2. Create a Python virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configure environment variables

Create a `.env` file in the project root:

```dotenv
GROQ_API_KEY=your_groq_api_key
GOOGLE_API_KEY=your_google_api_key
POSTGRES_PASSWORD=your_postgres_password
```

Check `retriever.py` and `build_vectorstore.py` for any additional required PostgreSQL settings, such as the database name, username, host, port, or connection URL.

**Never commit `.env` or expose API keys in frontend code.**

### 4. Configure PostgreSQL

Ensure PostgreSQL is running and the configured database exists.

Enable pgvector in the target database:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

Inspect `build_vectorstore.py` and follow the project's ingestion workflow to populate the vector database before starting the API.

### 5. Start the backend

From the project root:

```bash
uvicorn main:app --reload
```

The API should be available at:

- API: `http://127.0.0.1:8000`
- Interactive documentation: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/health`

### 6. Start the frontend

Open a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the local URL printed by Vite, usually:

`http://localhost:5173`

If necessary, configure the API URL in `frontend/.env.local`:

```dotenv
VITE_API_BASE_URL=http://localhost:8000
```

Restart the frontend development server after changing environment variables.

## API Usage

### Health check

```http
GET /health
```

### Ask a legal question

```http
POST /api/v1/ask
Content-Type: application/json
```

Example request:

```json
{
  "question": "What is the penalty for selling adulterated goods?"
}
```

Example using `curl`:

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/ask" \
  -H "Content-Type: application/json" \
  -d '{"question":"What is the penalty for selling adulterated goods?"}'
```

The response includes the answer and source information defined by the API response schema. Visit `/docs` to inspect the exact response format.

## Testing

Run the automated test suite:

```bash
pytest -q
```

Additional scripts are available for retrieval and answer evaluation:

```bash
python evaluate_retrieval.py
python evaluate_answers.py
python evaluate_live_answers.py
```

Inspect each script before running it. Live evaluations may consume external API quota or incur costs.

## Deployment

The intended deployment architecture separates the frontend, backend, and database.

1. Host PostgreSQL with pgvector.
2. Deploy FastAPI to a Python-compatible hosting provider.
3. Configure Groq, Google AI, and database credentials as backend environment variables.
4. Configure CORS to allow the deployed frontend origin.
5. Deploy the React frontend to a static hosting provider.
6. Set `VITE_API_BASE_URL` to the public backend URL.
7. Test health checks, retrieval, citations, and error handling in production.

A typical production backend command is:

```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

Adapt the command and environment settings to your hosting provider.

## Legal Data and Limitations

BanglaLawAI focuses on Bangladesh's Consumers' Right Protection Act, 2009. Its responses depend on the quality and completeness of the collected legal text, retrieval results, and language-model generation.

The system may retrieve incomplete evidence or generate an incorrect answer. Always verify important legal information against authoritative sources, including applicable amendments.

## License

No license has been specified yet. Add a license file before granting others explicit permission to reuse, modify, or distribute this project.

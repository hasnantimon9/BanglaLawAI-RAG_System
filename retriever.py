import os
import sys
from pathlib import Path
from urllib.parse import quote_plus

import psycopg
from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings


# --------------------------------------------------
# Configuration
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    sys.exit("ERROR: GOOGLE_API_KEY is missing from the environment.")

if not DATABASE_URL:
    if not POSTGRES_PASSWORD:
        sys.exit(
            "ERROR: Set DATABASE_URL or POSTGRES_PASSWORD."
        )

    # Backward-compatible local PostgreSQL configuration.
    DATABASE_URL = (
        "postgresql://banglalawai:"
        f"{quote_plus(POSTGRES_PASSWORD)}"
        "@127.0.0.1:5432/banglalawai"
    )

# psycopg.connect() expects a standard PostgreSQL URL.
if DATABASE_URL.startswith("postgresql+psycopg://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgresql+psycopg://",
        "postgresql://",
        1,
    )
elif DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = "postgresql://" + DATABASE_URL[len("postgres://"):]


# --------------------------------------------------
# Vector-store configuration
# --------------------------------------------------

COLLECTION = "banglalawai_consumer_rights_2009"

query_embeddings = GoogleGenerativeAIEmbeddings(
    model="gemini-embedding-001",
    task_type="RETRIEVAL_QUERY",
    output_dimensionality=3072,
)


# --------------------------------------------------
# Retrieval
# --------------------------------------------------

def retrieve(question: str, k: int = 5) -> list[dict]:
    """Return the k most relevant legal chunks."""

    if not question.strip():
        raise ValueError("Question cannot be empty.")

    if not 1 <= k <= 20:
        raise ValueError("k must be between 1 and 20.")

    query_vector = query_embeddings.embed_query(question)

    with psycopg.connect(
        DATABASE_URL,
        connect_timeout=10,
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    e.id,
                    e.document,
                    e.cmetadata,
                    1 - (e.embedding <=> %s::vector) AS similarity
                FROM langchain_pg_embedding AS e
                JOIN langchain_pg_collection AS c
                    ON e.collection_id = c.uuid
                WHERE c.name = %s
                ORDER BY e.embedding <=> %s::vector
                LIMIT %s
                """,
                (
                    str(query_vector),
                    COLLECTION,
                    str(query_vector),
                    k,
                ),
            )

            rows = cur.fetchall()

    return [
        {
            "chunk_id": row[0],
            "text": row[1],
            "metadata": row[2],
            "similarity": float(row[3]),
        }
        for row in rows
    ]

import os
import sys
from pathlib import Path
from urllib.parse import quote_plus

import psycopg
from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not POSTGRES_PASSWORD or not GOOGLE_API_KEY:
    sys.exit("ERROR: Check GOOGLE_API_KEY and POSTGRES_PASSWORD in .env")

COLLECTION = "banglalawai_consumer_rights_2009"

connection_string = (
    "postgresql+psycopg://banglalawai:"
    f"{quote_plus(POSTGRES_PASSWORD)}"
    "@127.0.0.1:5432/banglalawai"
)

# Query embeddings must use the retrieval-query task type.
query_embeddings = GoogleGenerativeAIEmbeddings(
    model="gemini-embedding-001",
    task_type="RETRIEVAL_QUERY",
    output_dimensionality=3072,
)


def retrieve(question: str, k: int = 5) -> list[dict]:
    """Return the k most relevant legal chunks for a question."""
    if not question.strip():
        raise ValueError("Question cannot be empty.")

    if not 1 <= k <= 20:
        raise ValueError("k must be between 1 and 20.")

    query_vector = query_embeddings.embed_query(question)

    with psycopg.connect(
        host="127.0.0.1",
        port=5432,
        dbname="banglalawai",
        user="banglalawai",
        password=POSTGRES_PASSWORD,
        connect_timeout=5,
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT e.id, e.document, e.cmetadata,
                       1 - (e.embedding <=> %s::vector) AS similarity
                FROM langchain_pg_embedding AS e
                JOIN langchain_pg_collection AS c
                    ON e.collection_id = c.uuid
                WHERE c.name = %s
                ORDER BY e.embedding <=> %s::vector
                LIMIT %s
                """,
                (str(query_vector), COLLECTION, str(query_vector), k),
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


if __name__ == "__main__":
    question = input("Ask a question about the Consumer Rights Protection Act, 2009: ")

    try:
        results = retrieve(question, k=5)
    except Exception as exc:
        sys.exit(f"Retrieval failed: {type(exc).__name__}: {exc}")

    if not results:
        print("No matching passages found.")
        sys.exit(0)

    for i, result in enumerate(results, start=1):
        metadata = result["metadata"]

        print(f"\n{'=' * 70}")
        print(f"Result {i} | Similarity: {result['similarity']:.4f}")
        print(f"Chunk ID: {result['chunk_id']}")
        print(f"Section: {metadata.get('section_number')}")
        print(f"Title: {metadata.get('title')}")
        print(f"Source: {metadata.get('source_url')}")
        print(f"\n{result['text']}")

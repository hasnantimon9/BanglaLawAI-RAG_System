import json
import os
import sys
from pathlib import Path
from urllib.parse import quote_plus, urlsplit, urlunsplit

from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_postgres import PGVector
from sqlalchemy import create_engine, text

# --------------------------------------------------
# Configuration
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

CHUNKS_PATH = BASE_DIR / "data" / "processed" / "chunks.jsonl"
ENV_PATH = BASE_DIR / ".env"

load_dotenv(dotenv_path=ENV_PATH)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DATABASE_URL = os.getenv("DATABASE_URL")

COLLECTION_NAME = "banglalawai_consumer_rights_2009"
EMBEDDING_DIMENSION = 3072
BATCH_SIZE = 16


# --------------------------------------------------
# Validate configuration
# --------------------------------------------------

if not GOOGLE_API_KEY:
    sys.exit("ERROR: GOOGLE_API_KEY is missing from the environment.")

if not CHUNKS_PATH.is_file():
    sys.exit(f"ERROR: Chunk file not found: {CHUNKS_PATH}")

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


# --------------------------------------------------
# Normalize PostgreSQL URL for SQLAlchemy / PGVector
# --------------------------------------------------

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = "postgresql://" + DATABASE_URL[len("postgres://"):]

if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgresql://",
        "postgresql+psycopg://",
        1,
    )


# --------------------------------------------------
# Load and validate chunks
# --------------------------------------------------

chunks = []

try:
    with CHUNKS_PATH.open(encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue

            try:
                chunk = json.loads(line)
            except json.JSONDecodeError as exc:
                sys.exit(
                    f"ERROR: Invalid JSON on line {line_number}: {exc}"
                )

            if not isinstance(chunk, dict):
                sys.exit(
                    f"ERROR: Expected a JSON object on line {line_number}"
                )

            required_fields = {
                "chunk_id",
                "embedding_text",
                "text",
                "metadata",
            }

            missing = required_fields - chunk.keys()

            if missing:
                sys.exit(
                    f"ERROR: Line {line_number} is missing fields: "
                    f"{sorted(missing)}"
                )

            if (
                not isinstance(chunk["chunk_id"], str)
                or not chunk["chunk_id"].strip()
            ):
                sys.exit(
                    f"ERROR: Invalid chunk_id on line {line_number}"
                )

            if (
                not isinstance(chunk["embedding_text"], str)
                or not chunk["embedding_text"].strip()
            ):
                sys.exit(
                    f"ERROR: Invalid embedding_text on line {line_number}"
                )

            if (
                not isinstance(chunk["text"], str)
                or not chunk["text"].strip()
            ):
                sys.exit(
                    f"ERROR: Invalid text on line {line_number}"
                )

            if not isinstance(chunk["metadata"], dict):
                sys.exit(
                    f"ERROR: Invalid metadata on line {line_number}"
                )

            chunks.append(chunk)

except OSError as exc:
    sys.exit(f"ERROR: Could not read chunk file: {exc}")


if not chunks:
    sys.exit("ERROR: No chunks found.")

chunk_ids = [chunk["chunk_id"] for chunk in chunks]

if len(set(chunk_ids)) != len(chunk_ids):
    sys.exit("ERROR: Duplicate chunk IDs found.")

print(f"Loaded and validated {len(chunks)} chunks.")


# --------------------------------------------------
# Initialize Gemini embeddings
# --------------------------------------------------

embeddings = GoogleGenerativeAIEmbeddings(
    model="gemini-embedding-001",
    task_type="RETRIEVAL_DOCUMENT",
    output_dimensionality=EMBEDDING_DIMENSION,
)


# --------------------------------------------------
# Initialize PostgreSQL vector store
# --------------------------------------------------

vector_store = PGVector(
    embeddings=embeddings,
    connection=DATABASE_URL,
    collection_name=COLLECTION_NAME,
    embedding_length=EMBEDDING_DIMENSION,
    distance_strategy="cosine",
    use_jsonb=True,
    create_extension=False,
)

# --------------------------------------------------
# Resume indexing: skip chunks already stored in Neon
# --------------------------------------------------

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

try:
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                    SELECT e.id
                    FROM langchain_pg_embedding AS e
                    JOIN langchain_pg_collection AS c
                        ON e.collection_id = c.uuid
                    WHERE c.name = :collection_name
            """),
            {"collection_name": COLLECTION_NAME},
        )
        existing_ids = set(result.scalars().all())
finally:
    engine.dispose()

chunks = [
    chunk for chunk in chunks
    if chunk["chunk_id"] not in existing_ids
]

print(f"Already indexed: {len(existing_ids)}")
print(f"Chunks remaining: {len(chunks)}")

if not chunks:
    print("All chunks are already indexed.")
    sys.exit(0)
# --------------------------------------------------
# Embed and index in batches
# --------------------------------------------------

for start in range(0, len(chunks), BATCH_SIZE):
    batch = chunks[start : start + BATCH_SIZE]

    # Embed enriched text to improve legal retrieval.
    embedding_texts = [
        chunk["embedding_text"]
        for chunk in batch
    ]

    vectors = embeddings.embed_documents(embedding_texts)

    # Verify embedding count and dimensions before insertion.
    if len(vectors) != len(batch):
        sys.exit(
            "ERROR: Embedding count does not match batch size."
        )

    if any(
        len(vector) != EMBEDDING_DIMENSION
        for vector in vectors
    ):
        sys.exit("ERROR: Unexpected embedding dimension.")

    # Store original legal passages, not enriched embedding text.
    vector_store.add_embeddings(
        texts=[chunk["text"] for chunk in batch],
        embeddings=vectors,
        metadatas=[chunk["metadata"] for chunk in batch],
        ids=[chunk["chunk_id"] for chunk in batch],
    )

    completed = min(start + len(batch), len(chunks))
    print(f"Indexed {completed}/{len(chunks)} chunks")


# --------------------------------------------------
# Completion summary
# --------------------------------------------------

print("\nIngestion completed successfully.")
print(f"Collection: {COLLECTION_NAME}")
print(f"Chunks indexed: {len(chunks)}")
print(f"Embedding dimensions: {EMBEDDING_DIMENSION}")

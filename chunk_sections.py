
import json
import re
from pathlib import Path

INPUT_PATH = Path("data/cleaned/sections.jsonl")
OUTPUT_PATH = Path("data/processed/chunks.jsonl")

DEFINITION_PATTERN = re.compile(
    r"(?m)^\((\d{1,2})\)[ \t]*$"
)


def build_embedding_text(
    record: dict,
    text: str,
    definition_number: int | None = None,
) -> str:
    parts = [
        f"Law: {record['law_title']}",
    ]

    if record.get("section_number") is not None:
        parts.append(f"Section: {record['section_number']}")

    if record.get("title"):
        parts.append(f"Section title: {record['title']}")

    if record.get("chapter"):
        parts.append(f"Chapter: {record['chapter']}")

    if definition_number is not None:
        parts.append(f"Definition number: {definition_number}")

    parts.append(f"Legal text:\n{text.strip()}")
    return "\n".join(parts)


def make_chunk(
    record: dict,
    chunk_id: str,
    text: str,
    chunk_type: str,
    definition_number: int | None = None,
) -> dict:
    text = text.strip()

    if not text:
        raise ValueError(f"Empty chunk: {chunk_id}")

    metadata = {
        key: record.get(key)
        for key in [
            "id",
            "law_id",
            "law_title",
            "section_number",
            "section_type",
            "title",
            "chapter",
            "preceding_headings",
            "language",
            "source_url",
            "source_document_id",
            "content_sha256",
            "verification_status",
        ]
    }

    metadata["parent_section_id"] = record["id"]
    metadata["chunk_type"] = chunk_type
    metadata["definition_number"] = definition_number

    return {
        "chunk_id": chunk_id,
        "embedding_text": build_embedding_text(
            record, text, definition_number
        ),
        "metadata": metadata,
        "text": text,
    }


def split_definitions(record: dict) -> list[dict]:
    text = record["text"]
    matches = list(DEFINITION_PATTERN.finditer(text))

    # Fail safely if the source structure changes.
    if len(matches) != 22:
        raise ValueError(
            f"Expected 22 definitions in section 2, "
            f"found {len(matches)}"
        )

    numbers = [int(match.group(1)) for match in matches]
    if numbers != list(range(1, 23)):
        raise ValueError(f"Unexpected definition numbering: {numbers}")

    chunks = []
    section_prefix = record["id"]

    # Keep the introductory legal text as a separate chunk.
    intro = text[:matches[0].start()].strip()

    chunks.append(
        make_chunk(
            record,
            f"{section_prefix}:intro",
            intro,
            "section_introduction",
        )
    )

    # Each definition remains intact, including its subclauses.
    for i, match in enumerate(matches):
        start = match.start()
        end = (
            matches[i + 1].start()
            if i + 1 < len(matches)
            else len(text)
        )

        definition_text = text[start:end].strip()
        number = int(match.group(1))

        chunks.append(
            make_chunk(
                record,
                f"{section_prefix}:definition:{number}",
                definition_text,
                "definition",
                number,
            )
        )

    return chunks


def main():
    if not INPUT_PATH.exists():
        raise FileNotFoundError(INPUT_PATH)

    records = []
    with INPUT_PATH.open(encoding="utf-8") as file:
        for line in file:
            if line.strip():
                records.append(json.loads(line))

    output_chunks = []

    for record in records:
        if not record.get("text", "").strip():
            raise ValueError(f"Empty source text: {record.get('id')}")

        if str(record.get("section_number")) == "2":
            output_chunks.extend(split_definitions(record))
        else:
            output_chunks.append(
                make_chunk(
                    record,
                    record["id"],
                    record["text"],
                    "section",
                )
            )

    chunk_ids = [chunk["chunk_id"] for chunk in output_chunks]

    if len(chunk_ids) != len(set(chunk_ids)):
        raise ValueError("Duplicate chunk IDs detected")

    # Write only after all validation succeeds.
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp_path = OUTPUT_PATH.with_suffix(".jsonl.tmp")

    with temp_path.open("w", encoding="utf-8") as file:
        for chunk in output_chunks:
            file.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    temp_path.replace(OUTPUT_PATH)

    print(f"Input records: {len(records)}")
    print(f"Output chunks: {len(output_chunks)}")
    print(f"Unique chunk IDs: {len(set(chunk_ids))}")
    print(f"Section 2 chunks: {sum(
        c['metadata']['section_number'] == 2
        for c in output_chunks
    )}")
    print(f"Output: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

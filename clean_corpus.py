import json
import re
import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parent
METADATA_PATH = ROOT / "data" / "metadata.jsonl"
OUTPUT_DIR = ROOT / "data" / "cleaned"
OUTPUT_PATH = OUTPUT_DIR / "sections.jsonl"
REPORT_PATH = OUTPUT_DIR / "report.json"

LAW_ID = "consumer_rights_protection_act_2009"
LAW_TITLE_BN = "ভোক্তা অধিকার সংরক্ষণ আইন, ২০০৯"

SOURCE_URL = (
    "https://bdlaws.minlaw.gov.bd/"
    "act-details-1014.html?lang=bn"
)

# Recognize section numbers such as ১।, ৫। and ৬১।
# Supports Bengali and Western digits, and both Bengali danda forms.
SECTION_PATTERN = re.compile(
    r"(?m)^[ \t]*([০-৯0-9]{1,3})[ \t]*[।৷](?=[ \t(০-৯0-9]|$)"
)

BANGLA_DIGITS = str.maketrans(
    "০১২৩৪৫৬৭৮৯",
    "0123456789",
)

# Known source heading that the automatic heuristic can miss.
KNOWN_TITLES = {
    "44": "মিথ্যা বিজ্ঞাপন দ্বারা ক্রেতা সাধারণকে প্রতারিত করিবার দণ্ড",
}


def normalize_text(text):
    """Normalize whitespace without changing legal wording."""
    text = text.replace("\ufeff", "")
    text = text.replace("\u200b", "")
    text = text.replace("\xa0", " ")
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Collapse repeated spaces while preserving line boundaries.
    lines = [
        re.sub(r"[ \t]+", " ", line).strip()
        for line in text.splitlines()
    ]

    result = "\n".join(lines)
    result = re.sub(r"\n{3,}", "\n\n", result)

    return result.strip()


def load_metadata():
    """Load source metadata from JSONL."""
    records = []

    with METADATA_PATH.open(encoding="utf-8") as file:
        for line in file:
            if line.strip():
                records.append(json.loads(line))

    return records


def find_bangla_source(metadata):
    """Find the explicitly configured Bengali source."""
    for record in metadata:
        if record.get("source_url") == SOURCE_URL:
            return record

    raise RuntimeError(
        f"Bangla source not found in {METADATA_PATH}"
    )


def get_trailing_headings(block):
    """
    Identify heading lines after the last line that appears
    to end a legal sentence or clause.
    """
    lines = [
        line.strip()
        for line in block.splitlines()
        if line.strip()
    ]

    last_punctuation = -1

    for i, line in enumerate(lines):
        if (
            re.search(r"[।৷!?;:]$", line)
            or line.endswith(":-")
        ):
            last_punctuation = i

    return lines[last_punctuation + 1:]


def remove_heading_suffix(block, headings):
    """Remove identified heading lines from the end of a block."""
    if not headings:
        return block

    lines = block.splitlines(keepends=True)

    for heading in reversed(headings):
        while lines and not lines[-1].strip():
            lines.pop()

        if not lines or lines[-1].strip() != heading:
            # Preserve the original block if matching fails.
            return block

        lines.pop()

    return "".join(lines).rstrip()


def split_sections(text):
    """
    Split the source into a preamble and numbered provisions.
    Attach heading and chapter metadata where detectable.
    """
    matches = list(SECTION_PATTERN.finditer(text))

    if not matches:
        raise RuntimeError(
            "No section headings found. "
            "Inspect the source text and update SECTION_PATTERN."
        )

    sections = []
    current_chapter = None

    # Capture the preamble and headings before Section 1.
    first_heading_block = text[:matches[0].start()]
    first_headings = get_trailing_headings(first_heading_block)

    preamble = remove_heading_suffix(
        first_heading_block,
        first_headings,
    ).strip()

    if preamble:
        sections.append({
            "section_number": None,
            "section_type": "preamble",
            "title": None,
            "chapter": None,
            "preceding_headings": [],
            "text": preamble,
        })

    for index, match in enumerate(matches):
        start = match.start()

        end = (
            matches[index + 1].start()
            if index + 1 < len(matches)
            else len(text)
        )

        section_text = text[start:end].strip()

        # Trailing headings belong to the next provision, not
        # to the legal text of the current provision.
        if index + 1 < len(matches):
            next_headings = get_trailing_headings(section_text)

            section_text = remove_heading_suffix(
                section_text,
                next_headings,
            ).strip()

        raw_number = match.group(1)
        section_number = raw_number.translate(BANGLA_DIGITS)

        previous_start = (
            matches[index - 1].start()
            if index > 0
            else 0
        )

        preceding_block = text[previous_start:start]
        heading_lines = get_trailing_headings(preceding_block)

        title = heading_lines[-1] if heading_lines else None

        # Detect chapter headings such as "প্রথম অধ্যায়".
        for i, line in enumerate(heading_lines):
            if line.endswith("অধ্যায়"):
                chapter_title = (
                    heading_lines[i + 1]
                    if i + 1 < len(heading_lines) - 1
                    else None
                )

                current_chapter = (
                    f"{line} — {chapter_title}"
                    if chapter_title
                    else line
                )

        # Apply known title corrections using string section IDs.
        if section_number in KNOWN_TITLES:
            title = KNOWN_TITLES[section_number]

        preceding_headings = heading_lines[:-1]

        if section_number in KNOWN_TITLES:
            preceding_headings = [title]

        sections.append({
            "section_number": section_number,
            "section_type": "section",
            "title": title,
            "chapter": current_chapter,
            "preceding_headings": preceding_headings,
            "text": section_text,
        })

    return sections


def remove_source_boilerplate(text):
    """Remove known website print labels and its copyright footer."""

    # Remove the print-view label.
    text = re.sub(
        r"(?m)^[ \t]*প্রিন্ট ভিউ[ \t]*\n?",
        "",
        text,
    )

    # Remove the print label and standalone date.
    text = re.sub(
        r"(?m)^[ \t]*প্রিন্ট[ \t]*\n"
        r"[ \t]*\d{1,2}/\d{1,2}/\d{4}[ \t]*\n?",
        "",
        text,
    )

    # Remove only the known website copyright footer.
    # Do not remove English law names appearing inside provisions.
    text = re.sub(
        r"(?m)^[ \t]*Copyright[ \t]*\n"
        r"[ \t]*©[ \t]*\n"
        r"[ \t]*2019, Legislative and Parliamentary Affairs Division[ \t]*\n"
        r"[ \t]*Ministry of Law, Justice and Parliamentary Affairs[ \t]*\n?",
        "",
        text,
    )

    return normalize_text(text)


def main():
    metadata = load_metadata()
    source = find_bangla_source(metadata)

    source_path = ROOT / source["text_path"]

    if not source_path.is_file():
        raise FileNotFoundError(source_path)

    raw_text = source_path.read_text(encoding="utf-8")
    text = normalize_text(raw_text)

    # Avoid indexing a failed scrape.
    if text.strip().lower() in {
        "no result",
        "no results",
        "no result found",
    }:
        raise RuntimeError("Source contains no legal text.")

    text = remove_source_boilerplate(text)

    sections = split_sections(text)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    seen_hashes = set()
    written = 0
    duplicates = 0

    with OUTPUT_PATH.open("w", encoding="utf-8") as output:
        for item in sections:
            content_hash = hashlib.sha256(
                item["text"].encode("utf-8")
            ).hexdigest()

            if content_hash in seen_hashes:
                duplicates += 1
                continue

            seen_hashes.add(content_hash)

            record = {
                "id": (
                    f"{LAW_ID}:"
                    f"{item['section_number'] or 'preamble'}"
                ),
                "law_id": LAW_ID,
                "law_title": LAW_TITLE_BN,
                "section_number": item["section_number"],
                "section_type": item["section_type"],
                "title": item.get("title"),
                "chapter": item.get("chapter"),
                "preceding_headings": item.get(
                    "preceding_headings", []
                ),
                "language": "bn",
                "text": item["text"],
                "source_url": SOURCE_URL,
                "source_document_id": source["id"],
                "content_sha256": content_hash,
                "verification_status": "pending",
            }

            output.write(
                json.dumps(record, ensure_ascii=False) + "\n"
            )
            written += 1

    section_numbers = [
        item["section_number"]
        for item in sections
        if item["section_type"] == "section"
    ]

    report = {
        "law_id": LAW_ID,
        "source_url": SOURCE_URL,
        "source_file": str(source_path.relative_to(ROOT)),
        "output_file": str(OUTPUT_PATH.relative_to(ROOT)),
        "source_characters": len(text),
        "section_records_detected": len(section_numbers),
        "unique_records_written": written,
        "duplicate_records_skipped": duplicates,
        "section_numbers": section_numbers,
        "warning": (
            "Section boundaries and titles are heuristic. "
            "Review the output against the official source "
            "before embedding."
        ),
    }

    REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("Corpus cleaning completed.")
    print(f"Source: {source_path.relative_to(ROOT)}")
    print(f"Output: {OUTPUT_PATH.relative_to(ROOT)}")
    print(f"Section records detected: {len(section_numbers)}")
    print(f"Unique records written: {written}")
    print(f"Duplicates skipped: {duplicates}")
    print(f"Report: {REPORT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

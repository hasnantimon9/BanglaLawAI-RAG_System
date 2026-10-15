"""Collect real BanglaLaw-AI API responses for offline evaluation."""

import json
import urllib.error
import urllib.request
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_PATH = BASE_DIR / "data" / "evaluation" / "actual_answers.jsonl"
API_URL = "http://127.0.0.1:8000/api/v1/ask"

CASES = [
    {
        "id": "live_section_41_bangla_001",
        "question": "ভেজাল পণ্য বিক্রি করলে কী শাস্তি হতে পারে?",
        "expected_section": "41",
        "required_facts": [
            "জ্ঞাতসারে",
            "অনূর্ধ্ব তিন বৎসর",
            "অনধিক দুই লক্ষ টাকা",
        ],
        "expected_abstention": False,
    },
    {
        "id": "live_section_60_english_001",
        "question": (
            "How long does a consumer have to submit a complaint "
            "under the Consumer Rights Protection Act, 2009?"
        ),
        "expected_section": "60",
        "required_facts": [
            "30 days",
            "Director General",
        ],
        "expected_abstention": False,
    },
    {
        "id": "live_section_44_english_001",
        "question": (
            "What is the penalty for false advertising intended "
            "to deceive consumers?"
        ),
        "expected_section": "44",
        "required_facts": [
            "false",
            "deceive consumers",
            "one year",
            "200,000 taka",
            "or both",
        ],
        "expected_abstention": False,
    },
    {
        "id": "live_section_55_english_001",
        "question": (
            "What happens if someone commits the same offence again "
            "after already being punished for it?"
        ),
        "expected_section": "55",
        "required_facts": [
            "same offence",
            "double",
            "maximum punishment",
        ],
        "expected_abstention": False,
    },
    {
        "id": "live_out_of_scope_fifa_001",
        "question": "Who won the FIFA World Cup in 2022?",
        "expected_section": None,
        "required_facts": [],
        "expected_abstention": True,
    },
]


def request_answer(question):
    """Call the existing local API without exposing credentials."""
    body = json.dumps({"question": question}).encode("utf-8")
    request = urllib.request.Request(
        API_URL,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))


def main():
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    existing = []
    if OUTPUT_PATH.exists():
        with OUTPUT_PATH.open(encoding="utf-8") as file:
            existing = [
                json.loads(line)
                for line in file
                if line.strip()
            ]

    existing_ids = {record["id"] for record in existing}
    added = 0

    for case in CASES:
        if case["id"] in existing_ids:
            print(f"[SKIP] {case['id']} already exists")
            continue

        print(f"\nRequesting: {case['id']}")

        try:
            response = request_answer(case["question"])
        except urllib.error.HTTPError as exc:
            print(f"[ERROR] HTTP {exc.code} for {case['id']}")
            print(exc.read().decode("utf-8", errors="replace")[:500])
            continue
        except Exception as exc:
            print(f"[ERROR] {case['id']}: {type(exc).__name__}: {exc}")
            continue

        record = {
            **case,
            "answer": response["answer"],
            "sources": response.get("sources", []),
            "retrieved_sources": response.get("retrieved_sources", []),
            "record_type": "live_api_response",
        }

        # Pick the actual cited label for the expected section, if present.
        expected_section = case["expected_section"]
        record["expected_citation"] = next(
            (
                source["source_id"]
                for source in record["sources"]
                if expected_section is not None
                and str(source["section_number"]) == expected_section
            ),
            None,
        )

        with OUTPUT_PATH.open("a", encoding="utf-8") as file:
            file.write(
                json.dumps(record, ensure_ascii=False) + "\n"
            )

        existing_ids.add(case["id"])
        added += 1

        print("Answer:", response["answer"])
        print(
            "Cited sections:",
            [source["section_number"] for source in record["sources"]],
        )
        print(
            "Retrieved sections:",
            [
                source["section_number"]
                for source in record["retrieved_sources"]
            ],
        )

    print(f"\nAdded {added} response(s).")
    print(f"Dataset: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

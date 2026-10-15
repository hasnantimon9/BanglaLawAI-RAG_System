"""Collect real BanglaLaw-AI API responses for offline evaluation."""

import argparse
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
        "required_facts": ["30 days", "Director General"],
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
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Regenerate existing test records from the live API.",
    )
    args = parser.parse_args()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    existing = []
    if OUTPUT_PATH.exists():
        with OUTPUT_PATH.open(encoding="utf-8") as file:
            existing = [
                json.loads(line)
                for line in file
                if line.strip()
            ]

    cases_by_id = {case["id"]: case for case in CASES}
    existing_by_id = {record["id"]: record for record in existing}

    # Preserve records unrelated to these live API test cases.
    if args.refresh:
        records = [
            record
            for record in existing
            if record["id"] not in cases_by_id
        ]
    else:
        records = list(existing)

    records_by_id = {record["id"]: record for record in records}
    updated = 0
    added = 0

    for case in CASES:
        old_record = existing_by_id.get(case["id"])

        if old_record and not args.refresh:
            print(f"[SKIP] {case['id']} already exists")
            continue

        action = "Refreshing" if old_record else "Requesting"
        print(f"\n{action}: {case['id']}")

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

        records_by_id[case["id"]] = record

        if old_record:
            updated += 1
        else:
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

    # Write atomically so an interrupted write does not truncate the dataset.
    temporary_path = OUTPUT_PATH.with_suffix(".jsonl.tmp")
    with temporary_path.open("w", encoding="utf-8") as file:
        for record in records_by_id.values():
            file.write(json.dumps(record, ensure_ascii=False) + "\n")

    temporary_path.replace(OUTPUT_PATH)

    print(f"\nAdded {added} response(s).")
    print(f"Refreshed {updated} response(s).")
    print(f"Dataset: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

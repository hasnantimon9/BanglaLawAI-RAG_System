"""Offline evaluation of saved BanglaLaw-AI API responses."""

import json
import re
from pathlib import Path


DATA_PATH = (
    Path(__file__).resolve().parent
    / "data" / "evaluation" / "actual_answers.jsonl"
)

# Accept simple wording variants without changing the legal meaning
# of the expected fact being tested.
FACT_VARIANTS = {
    "অনূর্ধ্ব তিন বৎসর": [
        "অনূর্ধ্ব তিন বৎসর",
        "সর্বোচ্চ তিন বছরের",
        "সর্বোচ্চ তিন বছর",
    ],
    "অনধিক দুই লক্ষ টাকা": [
        "অনধিক দুই লক্ষ টাকা",
        "সর্বোচ্চ দুই লক্ষ টাকা",
    ],
    "deceive consumers": [
        "deceive consumers",
        "deceives consumers",
    ],
    "maximum punishment": [
        "maximum punishment",
        "maximum penalty",
    ],
}

ABSTENTION_PATTERNS = [
    r"evidence provided is insufficient",
    r"insufficient evidence to answer",
    r"do not contain any information",
    r"not contain.*information",
    r"could not find relevant provisions",
]


def normalize(text):
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def contains_fact(answer, fact):
    variants = FACT_VARIANTS.get(fact, [fact])
    normalized_answer = normalize(answer)
    return any(
        normalize(variant) in normalized_answer
        for variant in variants
    )


def evaluate_record(record):
    answer = record.get("answer", "")
    question = record.get("question", "")
    expected_section = record.get("expected_section")
    expected_abstention = record.get("expected_abstention", False)

    # Detect answer language from Bengali script. This is a simple
    # script check, not a full language-identification model.
    question_is_bengali = bool(re.search(r"[\u0980-\u09FF]", question))
    answer_is_bengali = bool(re.search(r"[\u0980-\u09FF]", answer))
    language_ok = question_is_bengali == answer_is_bengali

    required_facts = record.get("required_facts", [])
    missing_facts = [
        fact for fact in required_facts
        if not contains_fact(answer, fact)
    ]
    facts_ok = not missing_facts

    cited_ids = set(re.findall(r"\[(S\d+)\]", answer))
    sources = record.get("sources", [])
    source_sections = {
        source["source_id"]: str(source["section_number"])
        for source in sources
    }

    # Detect Bengali-style citations such as [স১] that the API's
    # current ASCII citation parser does not recognize.
    malformed_bengali_citation = bool(
        re.search(r"\[\s*স\s*[০-৯0-9]+\s*\]", answer)
    )

    all_citations_resolve = cited_ids.issubset(source_sections.keys())

    if expected_abstention:
        abstention_ok = any(
            re.search(pattern, answer, flags=re.IGNORECASE)
            for pattern in ABSTENTION_PATTERNS
        )
        section_ok = True  # No legal section is expected here.
        citation_ok = not cited_ids and not malformed_bengali_citation
    else:
        abstention_ok = True
        section_ok = (
            expected_section is not None
            and any(
                section == str(expected_section)
                for section in source_sections.values()
            )
        )
        expected_citation = record.get("expected_citation")
        citation_ok = (
            expected_citation is not None
            and expected_citation in cited_ids
            and source_sections.get(expected_citation)
            == str(expected_section)
            and all_citations_resolve
            and not malformed_bengali_citation
        )

    return {
        "facts_ok": facts_ok,
        "missing_facts": missing_facts,
        "language_ok": language_ok,
        "citation_ok": citation_ok,
        "section_ok": section_ok,
        "abstention_ok": abstention_ok,
        "malformed_bengali_citation": malformed_bengali_citation,
    }


def main():
    with DATA_PATH.open(encoding="utf-8") as file:
        records = [
            json.loads(line)
            for line in file
            if line.strip()
        ]

    print("\nBanglaLaw-AI Live Response Evaluation")
    print("=" * 48)

    totals = {
        "facts_ok": 0,
        "language_ok": 0,
        "citation_ok": 0,
        "section_ok": 0,
        "abstention_ok": 0,
    }

    for record in records:
        result = evaluate_record(record)
        print(f"\n[{record['id']}]")
        print("Question:", record["question"])

        for key, label in [
            ("facts_ok", "Required facts"),
            ("language_ok", "Question/answer language"),
            ("citation_ok", "Citation integrity"),
            ("section_ok", "Expected section retrieved and cited"),
            ("abstention_ok", "Out-of-scope abstention"),
        ]:
            passed = result[key]
            totals[key] += int(passed)
            print(f"{label}: {'PASS' if passed else 'FAIL'}")

        if result["missing_facts"]:
            print("Missing required facts:", result["missing_facts"])

        if result["malformed_bengali_citation"]:
            print("Problem: Bengali-style citation such as [স১] detected.")

    print("\n" + "=" * 48)
    print(f"Records evaluated: {len(records)}")

    for key, label in [
        ("facts_ok", "Required-fact checks"),
        ("language_ok", "Language checks"),
        ("citation_ok", "Citation-integrity checks"),
        ("section_ok", "Expected-section checks"),
        ("abstention_ok", "Abstention checks"),
    ]:
        print(f"{label}: {totals[key]}/{len(records)}")

    print(
        "\nThese are automated screening checks. They do not establish "
        "that a legal answer is complete or legally correct."
    )


if __name__ == "__main__":
    main()

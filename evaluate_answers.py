"""
Offline answer-quality evaluator for BanglaLaw-AI.

Checks manually written examples and saved API responses.
No Groq or Gemini API calls are made.
"""

import json
import re
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
ACTUAL_ANSWERS_PATH = (
    BASE_DIR / "data" / "evaluation" / "actual_answers.jsonl"
)


# These are manually written examples, not live model outputs.
EVALUATION_CASES = [
    {
        "id": "section_40_english",
        "question": "What is the penalty for selling above the fixed price?",
        "answer": (
            "Selling or offering to sell goods, drugs, or services above "
            "a price fixed by law may be punished by up to one year "
            "imprisonment, a fine up to 50,000 taka, or both. [S1]"
        ),
        "required_facts": [
            "above a price fixed by law",
            "one year",
            "50,000 taka",
            "or both",
        ],
    },
    {
        "id": "section_41_english",
        "question": "What is the penalty for selling adulterated goods?",
        "answer": (
            "A person who knowingly sells adulterated goods or drugs "
            "may face up to 3 years imprisonment, a fine up to "
            "200,000 taka, or both. [S1]"
        ),
        "required_facts": [
            "knowingly",
            "adulterated goods or drugs",
            "3 years",
            "200,000 taka",
            "or both",
        ],
    },
    {
        "id": "section_44_english",
        "question": "What is the penalty for deceptive false advertising?",
        "answer": (
            "A person who deceives consumers through false or untrue "
            "advertising to sell goods or services may face up to one "
            "year imprisonment, a fine up to 200,000 taka, or both. [S1]"
        ),
        "required_facts": [
            "false or untrue advertising",
            "deceives consumers",
            "sell goods or services",
            "one year",
            "200,000 taka",
            "or both",
        ],
    },
    {
        "id": "section_51_english",
        "question": "What is the penalty for selling expired products?",
        "answer": (
            "Selling or offering to sell expired goods or drugs may be "
            "punished by up to one year imprisonment, a fine up to "
            "50,000 taka, or both. [S1]"
        ),
        "required_facts": [
            "expired goods or drugs",
            "selling or offering to sell",
            "one year",
            "50,000 taka",
            "or both",
        ],
    },
    {
        "id": "section_55_english",
        "question": "What happens if someone repeats the same offence?",
        "answer": (
            "If a person has been punished for an offence and commits "
            "the same offence again, the person may receive double "
            "the maximum punishment for that offence. [S1]"
        ),
        "required_facts": [
            "been punished",
            "same offence",
            "double",
            "maximum punishment",
        ],
    },
    {
        "id": "section_60_english",
        "question": "How long does a consumer have to submit a complaint?",
        "answer": (
            "A complaint must be submitted within 30 days of the cause "
            "arising to the Director General or an authorized officer. "
            "A complaint outside this period is not admissible. [S1]"
        ),
        "required_facts": [
            "within 30 days",
            "cause arising",
            "Director General",
            "authorized officer",
            "not admissible",
        ],
    },
    {
        "id": "section_41_bangla",
        "question": "ভেজাল পণ্য বিক্রি করলে কী শাস্তি হয়?",
        "answer": (
            "কোন ব্যক্তি জ্ঞাতসারে ভেজাল মিশ্রিত পণ্য বা ঔষধ বিক্রয় "
            "করিলে বা করিতে প্রস্তাব করিলে তিনি অনূর্ধ্ব তিন বৎসর "
            "কারাদণ্ড, বা অনধিক দুই লক্ষ টাকা অর্থদণ্ড, বা উভয় দণ্ডে "
            "দণ্ডিত হইবেন। [S1]"
        ),
        "required_facts": [
            "জ্ঞাতসারে",
            "বিক্রয় করিলে বা করিতে প্রস্তাব করিলে",
            "অনূর্ধ্ব তিন বৎসর",
            "অনধিক দুই লক্ষ টাকা",
            "উভয় দণ্ডে",
        ],
    },
    {
        "id": "section_60_bangla",
        "question": "ভোক্তা অধিকার লঙ্ঘনের অভিযোগ কত দিনের মধ্যে করতে হয়?",
        "answer": (
            "কারণ উদ্ভব হইবার ৩০ (ত্রিশ) দিনের মধ্যে মহাপরিচালক "
            "কিংবা অধিদপ্তরের ক্ষমতাপ্রাপ্ত কোন কর্মকর্তার নিকট "
            "অভিযোগ করতে হবে। নির্ধারিত সময়ের মধ্যে অভিযোগ না "
            "করিলে উক্ত অভিযোগ গ্রহণযোগ্য হইবে না। [S1]"
        ),
        "required_facts": [
            "৩০ (ত্রিশ) দিনের মধ্যে",
            "মহাপরিচালক",
            "ক্ষমতাপ্রাপ্ত কোন কর্মকর্তার",
            "গ্রহণযোগ্য হইবে না",
        ],
    },
]


def normalize(text):
    """Normalize text for case-insensitive phrase matching."""
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def evaluate_answer(answer, required_facts):
    """Check whether all required phrases appear in an answer."""
    normalized_answer = normalize(answer)

    missing_facts = [
        fact
        for fact in required_facts
        if normalize(fact) not in normalized_answer
    ]

    return {
        "passed": not missing_facts,
        "missing_facts": missing_facts,
    }


def load_actual_answers():
    """Load saved API responses without calling any API."""
    if not ACTUAL_ANSWERS_PATH.exists():
        return []

    records = []

    with ACTUAL_ANSWERS_PATH.open(encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON on line {line_number} "
                    f"of {ACTUAL_ANSWERS_PATH}"
                ) from exc

            required_fields = {
                "id",
                "question",
                "answer",
                "expected_section",
                "required_facts",
                "expected_citation",
            }

            missing_fields = required_fields - record.keys()
            if missing_fields:
                raise ValueError(
                    f"Record on line {line_number} is missing: "
                    f"{', '.join(sorted(missing_fields))}"
                )

            records.append(record)

    return records


def evaluate_actual_record(record):
    """Check facts and whether citations map to expected sections."""
    result = evaluate_answer(
        record["answer"],
        record["required_facts"],
    )

    cited_ids = set(
        re.findall(r"\[(S\d+)\]", record["answer"])
    )

    source_sections = {
        source["source_id"]: str(source["section_number"])
        for source in record.get("sources", [])
    }

    expected_citation = record["expected_citation"]
    expected_section = str(record["expected_section"])

    citation_present = expected_citation in cited_ids
    citation_resolves = expected_citation in source_sections
    citation_matches_section = (
        citation_resolves
        and source_sections[expected_citation] == expected_section
    )
    all_citations_resolve = cited_ids.issubset(source_sections.keys())

    passed = (
        result["passed"]
        and citation_present
        and citation_matches_section
        and all_citations_resolve
    )

    return {
        **result,
        "citation_present": citation_present,
        "citation_matches_section": citation_matches_section,
        "all_citations_resolve": all_citations_resolve,
        "passed": passed,
    }


def main():
    print("\nBanglaLaw-AI Offline Evaluation")
    print("=" * 42)

    sample_passed = 0

    for case in EVALUATION_CASES:
        result = evaluate_answer(
            case["answer"],
            case["required_facts"],
        )
        status = "PASS" if result["passed"] else "FAIL"

        if result["passed"]:
            sample_passed += 1

        print(f"\n[SAMPLE {status}] {case['id']}")

        if result["missing_facts"]:
            print("Missing facts:", result["missing_facts"])

    print(
        f"\nManual examples: {sample_passed}/"
        f"{len(EVALUATION_CASES)} passed"
    )

    actual_records = load_actual_answers()
    actual_passed = 0

    print("\nSaved API Responses")
    print("-" * 42)

    for record in actual_records:
        result = evaluate_actual_record(record)
        status = "PASS" if result["passed"] else "FAIL"

        if result["passed"]:
            actual_passed += 1

        print(f"\n[ACTUAL {status}] {record['id']}")
        print(f"Question: {record['question']}")
        print(f"Expected section: {record['expected_section']}")
        print(
            "Required facts:",
            "PASS" if not result["missing_facts"] else "FAIL",
        )
        print(
            "Expected citation present:",
            result["citation_present"],
        )
        print(
            "Citation matches expected section:",
            result["citation_matches_section"],
        )
        print(
            "All citations resolve:",
            result["all_citations_resolve"],
        )

        if result["missing_facts"]:
            print("Missing facts:", result["missing_facts"])

    print("\n" + "=" * 42)
    print(
        f"Manual examples: {sample_passed}/"
        f"{len(EVALUATION_CASES)} passed"
    )
    print(
        f"Saved-answer checks: {actual_passed}/"
        f"{len(actual_records)} passed"
    )

    if not actual_records:
        print("No saved API answers found.")

    print(
        "\nNote: Phrase and metadata checks do not independently "
        "establish legal correctness."
    )


if __name__ == "__main__":
    main()

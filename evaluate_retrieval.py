from retriever import retrieve


TEST_CASES = [
    # Existing baseline
    {
        "question": "What is the penalty for selling adulterated goods?",
        "expected_sections": {"41"},
    },
    {
        "question": "What is the penalty for mixing prohibited substances into food?",
        "expected_sections": {"42"},
    },
    {
        "question": "What is the penalty for selling expired products?",
        "expected_sections": {"51"},
    },
    {
        "question": "What is the penalty for false advertising?",
        "expected_sections": {"44"},
    },
    {
        "question": "What is the penalty for manipulating weights?",
        "expected_sections": {"46"},
    },

    # More English queries
    {
        "question": "What punishment applies to producing counterfeit goods?",
        "expected_sections": {"50"},
    },
    {
        "question": "What happens if a seller charges more than the legally fixed price?",
        "expected_sections": {"40"},
    },
    {
        "question": "What penalty applies when a business does not display its price list?",
        "expected_sections": {"38"},
    },
    {
        "question": "What is the punishment for failing to supply goods or services as promised?",
        "expected_sections": {"45"},
    },
    {
        "question": "What punishment applies to using a tampered weighing scale in a shop?",
        "expected_sections": {"47"},
    },
    {
        "question": "What is the penalty for selling less quantity than promised?",
        "expected_sections": {"48"},
    },
    {
        "question": "What happens when a consumer service provider causes harm through negligence?",
        "expected_sections": {"53"},
    },
    {
        "question": "How long does a consumer have to submit a complaint under this Act?",
        "expected_sections": {"60"},
    },
    {
        "question": "How many days are allowed to appeal a magistrate's judgment?",
        "expected_sections": {"65"},
    },
    {
        "question": "What happens if someone commits the same offence again?",
        "expected_sections": {"55"},
    },

    # Bangla queries
    {
        "question": "ভেজাল পণ্য বিক্রি করলে কী শাস্তি হয়?",
        "expected_sections": {"41"},
    },
    {
        "question": "মেয়াদোত্তীর্ণ ঔষধ বিক্রি করলে কী শাস্তি হতে পারে?",
        "expected_sections": {"51"},
    },
    {
        "question": "পণ্যের নির্ধারিত মূল্যের চেয়ে বেশি দাম নিলে কী শাস্তি?",
        "expected_sections": {"40"},
    },
    {
        "question": "ভোক্তা অধিকার লঙ্ঘনের অভিযোগ কত দিনের মধ্যে করতে হয়?",
        "expected_sections": {"60"},
    },
    {
        "question": "একই অপরাধ আবার করলে কী ধরনের শাস্তি হতে পারে?",
        "expected_sections": {"55"},
    },
]


def main():
    k = 5
    hit_counts = {1: 0, 3: 0, 5: 0}
    reciprocal_ranks = []
    failures = []

    print("Running retrieval evaluation...")
    print(f"Test cases: {len(TEST_CASES)}\n")

    for index, case in enumerate(TEST_CASES, start=1):
        results = retrieve(case["question"], k=k)

        ranked_sections = [
            str(result["metadata"].get("section_number", ""))
            for result in results
        ]

        expected = case["expected_sections"]

        rank = next(
            (
                i
                for i, section in enumerate(ranked_sections, start=1)
                if section in expected
            ),
            None,
        )

        for cutoff in hit_counts:
            if rank is not None and rank <= cutoff:
                hit_counts[cutoff] += 1

        reciprocal_ranks.append(1 / rank if rank is not None else 0)

        if rank is None:
            failures.append(
                {
                    "index": index,
                    "question": case["question"],
                    "expected": sorted(expected),
                    "retrieved": ranked_sections,
                }
            )

        print(f"[{index}/{len(TEST_CASES)}] {case['question']}")
        print(f"Expected: {sorted(expected)}")
        print(f"Retrieved: {ranked_sections}")
        print(f"Correct section rank: {rank or 'NOT FOUND'}")
        print("-" * 60)

    total = len(TEST_CASES)

    print("\n" + "=" * 60)
    print("RETRIEVAL EVALUATION SUMMARY")
    print("=" * 60)
    print(f"Test questions: {total}")

    for cutoff, hits in hit_counts.items():
        print(
            f"Hit Rate@{cutoff}: "
            f"{hits}/{total} = {hits / total:.1%}"
        )

    mrr = sum(reciprocal_ranks) / total if total else 0
    print(f"MRR@{k}: {mrr:.3f}")
    print(f"Questions with no correct section in top {k}: {len(failures)}")

    if failures:
        print("\nFAILURES TO INVESTIGATE")
        for failure in failures:
            print(f"\nCase {failure['index']}: {failure['question']}")
            print(f"Expected: {failure['expected']}")
            print(f"Retrieved: {failure['retrieved']}")


if __name__ == "__main__":
    main()

from types import SimpleNamespace

import pytest
import answer_service


def make_fake_client(answer):
    """Create a fake Groq client response without an API call."""

    def fake_create(**kwargs):
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=answer)
                )
            ]
        )

    return SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=fake_create)
        )
    )


def make_result(section_number, title, similarity=0.9):
    return {
        "text": f"Legal text for section {section_number}.",
        "metadata": {
            "section_number": section_number,
            "title": title,
            "source_url": "https://example.com/law",
        },
        "similarity": similarity,
    }


def test_citation_normalization_and_source_filtering(monkeypatch):
    monkeypatch.setattr(
        answer_service,
        "retrieve",
        lambda question, k=5: [
            make_result("41", "Adulterated goods"),
            make_result("42", "Prohibited substances in food"),
        ],
    )

    monkeypatch.setattr(
        answer_service,
        "client",
        make_fake_client(
            "The penalty is described in Section 41. 【S1】"
        ),
    )

    result = answer_service.answer_question(
        "What is the penalty for adulterated goods?"
    )

    assert result["answer"].endswith("[S1]")
    assert "【S1】" not in result["answer"]

    # Only the cited source should appear here.
    assert [s["source_id"] for s in result["sources"]] == ["S1"]

    # Both retrieved passages remain available for debugging.
    assert [
        s["source_id"] for s in result["retrieved_sources"]
    ] == ["S1", "S2"]


def test_invalid_citation_is_rejected(monkeypatch):
    monkeypatch.setattr(
        answer_service,
        "retrieve",
        lambda question, k=5: [
            make_result("41", "Adulterated goods"),
        ],
    )

    monkeypatch.setattr(
        answer_service,
        "client",
        make_fake_client(
            "The penalty is described in Section 41. [S9]"
        ),
    )

    result = answer_service.answer_question(
        "What is the penalty for adulterated goods?"
    )

    assert "invalid source references" in result["answer"]
    assert result["sources"] == []
    assert len(result["retrieved_sources"]) == 1


def test_no_retrieved_results(monkeypatch):
    monkeypatch.setattr(
        answer_service,
        "retrieve",
        lambda question, k=5: [],
    )

    result = answer_service.answer_question(
        "What is the penalty for adulterated goods?"
    )

    assert "insufficient evidence" in result["answer"].lower()
    assert result["sources"] == []
    assert result["retrieved_sources"] == []


def test_answer_without_citations_has_no_cited_sources(monkeypatch):
    monkeypatch.setattr(
        answer_service,
        "retrieve",
        lambda question, k=5: [
            make_result("41", "Adulterated goods"),
        ],
    )

    monkeypatch.setattr(
        answer_service,
        "client",
        make_fake_client(
            "The retrieved passages do not provide enough information."
        ),
    )

    result = answer_service.answer_question(
        "Explain this legal provision."
    )

    assert result["sources"] == []
    assert len(result["retrieved_sources"]) == 1


def test_retrieval_failure_is_wrapped(monkeypatch):
    def fail_retrieval(question, k=5):
        raise RuntimeError("Database connection details")

    monkeypatch.setattr(answer_service, "retrieve", fail_retrieval)

    with pytest.raises(
        answer_service.UpstreamServiceError,
        match="Retrieval failed",
    ) as exc_info:
        answer_service.answer_question("Explain consumer rights.")

    assert isinstance(exc_info.value.__cause__, RuntimeError)


def test_generation_failure_is_wrapped(monkeypatch):
    monkeypatch.setattr(
        answer_service,
        "retrieve",
        lambda question, k=5: [
            make_result("41", "Adulterated goods")
        ],
    )

    def fail_generation(**kwargs):
        raise RuntimeError("Provider credentials or internal details")

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=fail_generation)
        )
    )

    monkeypatch.setattr(answer_service, "client", fake_client)

    with pytest.raises(
        answer_service.UpstreamServiceError,
        match="Answer generation failed",
    ) as exc_info:
        answer_service.answer_question(
            "What is the penalty for adulterated goods?"
        )

    assert isinstance(exc_info.value.__cause__, RuntimeError)


def test_system_prompt_preserves_legal_conditions():
    prompt = answer_service.SYSTEM_PROMPT.lower()

    assert "knowingly" in prompt
    assert "condition" in prompt
    assert "exception" in prompt
    assert "qualification" in prompt


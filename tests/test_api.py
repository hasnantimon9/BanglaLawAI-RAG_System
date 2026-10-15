from fastapi.testclient import TestClient

import main

client = TestClient(main.app)


def test_health_check():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "BanglaLawAI",
    }


def test_question_too_short():
    response = client.post(
        "/api/v1/ask",
        json={"question": "ab"},
    )

    assert response.status_code == 422


def test_question_too_long():
    response = client.post(
        "/api/v1/ask",
        json={"question": "a" * 1001},
    )

    assert response.status_code == 422


def test_missing_question():
    response = client.post("/api/v1/ask", json={})

    assert response.status_code == 422


def test_successful_answer(monkeypatch):
    def fake_answer_question(question):
        assert question == "What is the penalty for adulterated goods?"

        return {
            "answer": "The penalty is specified in Section 41. [S1]",
            "sources": [
                {
                    "source_id": "S1",
                    "section_number": "41",
                    "title": "Penalty for selling adulterated goods",
                    "url": "https://example.com/law",
                    "similarity": 0.95,
                }
            ],
        }

    monkeypatch.setattr(
        main,
        "answer_question",
        fake_answer_question,
    )

    response = client.post(
        "/api/v1/ask",
        json={
            "question": "What is the penalty for adulterated goods?"
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert data["answer"] == (
        "The penalty is specified in Section 41. [S1]"
    )
    assert len(data["sources"]) == 1
    assert data["sources"][0]["section_number"] == "41"
    assert data["sources"][0]["source_id"] == "S1"


def test_internal_error_is_not_exposed(monkeypatch):
    def fake_answer_question(question):
        raise RuntimeError("Sensitive internal details")

    monkeypatch.setattr(
        main,
        "answer_question",
        fake_answer_question,
    )

    response = client.post(
        "/api/v1/ask",
        json={"question": "Explain consumer rights."},
    )

    assert response.status_code == 500
    assert response.json() == {
        "detail": "Failed to process the question. Please try again."
    }
    assert "Sensitive internal details" not in response.text


def test_upstream_service_failure_returns_503(monkeypatch):
    def fail_answer_question(question):
        raise main.UpstreamServiceError("Upstream provider details")

    monkeypatch.setattr(main, "answer_question", fail_answer_question)

    response = client.post(
        "/api/v1/ask",
        json={"question": "Explain consumer rights."},
    )

    assert response.status_code == 503
    assert response.json() == {
        "detail": (
            "A required service is temporarily unavailable. "
            "Please try again later."
        )
    }
    assert "Upstream provider details" not in response.text


def test_whitespace_only_question_is_rejected():
    response = client.post(
        "/api/v1/ask",
        json={"question": "   "},
    )

    assert response.status_code == 422

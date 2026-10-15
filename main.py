import logging
import os
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from answer_service import UpstreamServiceError, answer_question

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="BanglaLawAI",
    description=(
        "Bilingual legal information API for Bangladesh's "
        "Consumer Rights Protection Act, 2009."
    ),
    version="0.3.0",
)

allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "FRONTEND_ORIGINS",
        "http://localhost:5173",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

class AskRequest(BaseModel):
    question: str = Field(
        min_length=3,
        max_length=1000,
        description="A question about Bangladesh consumer rights law.",
    )


class Source(BaseModel):
    source_id: str
    section_number: str
    title: str
    url: str | None
    similarity: float


class AskResponse(BaseModel):
    answer: str
    sources: list[Source]
    retrieved_sources: list[Source] = Field(default_factory=list)


# --------------------------------------------------
# Health check
# --------------------------------------------------

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "BanglaLawAI",
    }


# --------------------------------------------------
# Ask endpoint
# --------------------------------------------------

@app.post("/api/v1/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    question = request.question.strip()

    if len(question) < 3:
        raise HTTPException(
            status_code=422,
            detail=(
                "Question must contain at least 3 "
                "non-whitespace characters."
            ),
        )

    try:
        result = answer_question(question)
        return AskResponse(**result)

    except UpstreamServiceError as exc:
        # Log the failure stage and exception class only.
        # Do not expose provider messages or credentials.
        cause = exc.__cause__
        cause_type = type(cause).__name__ if cause else "UnknownError"

        logger.error(
            "Upstream service failure: stage=%s cause_type=%s",
            str(exc),
            cause_type,
        )

        raise HTTPException(
            status_code=503,
            detail=(
                "A required service is temporarily unavailable. "
                "Please try again later."
            ),
        ) from None

    except Exception:
        logger.exception(
            "Unexpected error while processing a legal question"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to process the question. Please try again."
            ),
        ) from None

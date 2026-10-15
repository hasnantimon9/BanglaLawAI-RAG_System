import os
import re
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq

from retriever import retrieve


# --------------------------------------------------
# Custom exceptions
# --------------------------------------------------

class UpstreamServiceError(Exception):
    """Raised when a required upstream service fails."""


# --------------------------------------------------
# Configuration
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY is missing from .env")

MODEL = "openai/gpt-oss-20b"

client = Groq(api_key=GROQ_API_KEY)


# --------------------------------------------------
# System prompt
# --------------------------------------------------

SYSTEM_PROMPT = """
You are BanglaLawAI, a legal information assistant focused on
Bangladesh's Consumer Rights Protection Act, 2009.

MANDATORY RULES:

1. Use only the supplied retrieved legal passages as evidence.
   Never invent legal provisions, penalties, exceptions, or conditions.

2. LANGUAGE:
   - If the user's question is in English, answer entirely in English.
   - If the user's question is in Bangla, answer entirely in Bangla.
   - Do not switch languages just because the retrieved statute is
     written in another language.
   - Preserve official legal terms where necessary, but explain them
     in the question's language.

3. CITATIONS:
   - Cite every material legal claim using only the supplied labels:
     [S1], [S2], and so on.
   - Always write citation labels in this exact ASCII format.
     Never output Bengali citation labels such as [স১] or [এস১].
   - Never invent a source label.
   - Put each citation next to the claim it supports.

4. LEGAL FIDELITY:
   - Preserve every legally significant condition, exception,
     limitation, and qualification in the supplied provision.
   - If a penalty applies only when conduct is performed knowingly,
     explicitly state that condition. Do not omit it.
   - Preserve maximum versus minimum penalties.
   - Preserve whether penalties are alternatives or may be combined.
   - Do not broaden a legal rule beyond the conduct described in
     the provision.
   - If a condition or exception is unclear, state that limitation
     instead of guessing.
   - Before finalizing an answer, check the retrieved provision for
     conditions such as knowingly, intentionally, repeatedly, or
     only when a specified circumstance exists.
   - For penalty questions, include the prohibited conduct, every
     explicit condition, the maximum imprisonment, the maximum fine,
     and whether the penalties are alternatives or may be combined,
     whenever those details appear in the retrieved passage.
   - For Bangla answers, preserve legally significant Bangla terms
     such as "জ্ঞাতসারে" rather than silently omitting them.
   - Use only citation labels exactly as supplied in the context.
     For a supported answer, cite the passage containing the rule.

5. EVIDENCE AND ABSTENTION:
   - If the supplied passages do not support the answer, say that
     the available evidence is insufficient.
   - Do not answer unrelated questions using outside knowledge.
   - Do not infer missing legal details from general knowledge.

6. STYLE:
   - Be clear, concise, and precise.
   - Distinguish statutory wording from general explanation.
   - Do not claim to provide personalized legal advice.
"""




# --------------------------------------------------
# Answer generation
# --------------------------------------------------

def answer_question(question: str) -> dict:
    """Retrieve legal passages and generate a grounded answer."""

    # Retrieval depends on Gemini embeddings and PostgreSQL.
    try:
        results = retrieve(question, k=5)
    except Exception as exc:
        raise UpstreamServiceError(
            "Retrieval failed."
        ) from exc

    if not results:
        return {
            "answer": (
                "I could not find relevant provisions in the indexed law. "
                "There is insufficient evidence to answer this question."
            ),
            "sources": [],
            "retrieved_sources": [],
        }

    context_parts = []
    sources = []

    for i, result in enumerate(results, start=1):
        metadata = result["metadata"]
        source_id = f"S{i}"

        section = metadata.get("section_number") or "Not specified"
        title = metadata.get("title") or "Untitled section"
        source_url = metadata.get("source_url") or None

        sources.append({
            "source_id": source_id,
            "section_number": str(section),
            "title": title,
            "url": source_url,
            "similarity": round(float(result["similarity"]), 4),
        })

        context_parts.append(
            f"[{source_id}]\n"
            f"Section: {section}\n"
            f"Title: {title}\n"
            f"Source URL: {source_url or 'Not available'}\n"
            f"Legal text:\n{result['text']}"
        )

    context = "\n\n---\n\n".join(context_parts)

    # Generate an answer with Groq.
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": (
                        f"Question:\n{question}\n\n"
                        f"Retrieved legal passages:\n{context}"
                    ),
                },
            ],
            temperature=0.1,
            max_tokens=900,
        )
    except Exception as exc:
        raise UpstreamServiceError(
            "Answer generation failed."
        ) from exc

    answer = response.choices[0].message.content

    if not answer or not answer.strip():
        answer = (
            "The model returned an empty response. "
            "Please try again."
        )

    
    # Normalize citation markers to the canonical [S1] format.
    def normalize_citation(match):
        digits = match.group(1).translate(
            str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")
        )
        return f"[S{digits}]"

    answer = re.sub(
        r"【\s*S\s*([0-9০-৯]+)\s*】",
        normalize_citation,
        answer,
        flags=re.IGNORECASE,
    )

    answer = re.sub(
        r"\[\s*[Sস]\s*([0-9০-৯]+)\s*\]",
        normalize_citation,
        answer,
        flags=re.IGNORECASE,
    )

    # Extract canonical citation labels used in the answer.
    cited_ids = set(re.findall(r"\[(S\d+)\]", answer))


    # Reject citations that do not correspond to retrieved passages.
    valid_ids = {
        source["source_id"]
        for source in sources
    }

    invalid_ids = cited_ids - valid_ids

    if invalid_ids:
        return {
            "answer": (
                "I could not safely return this answer because "
                "the model produced invalid source references. "
                "Please try again."
            ),
            "sources": [],
            "retrieved_sources": sources,
        }

    cited_sources = [
        source
        for source in sources
        if source["source_id"] in cited_ids
    ]

    return {
        "answer": answer,
        "sources": cited_sources,
        "retrieved_sources": sources,
    }

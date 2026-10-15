import os
import sys

from dotenv import load_dotenv
from groq import Groq

from retriever import retrieve

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    sys.exit("ERROR: GROQ_API_KEY is missing from .env")

# Change this to a model currently available to your Groq account.
MODEL = "openai/gpt-oss-20b"

client = Groq(api_key=GROQ_API_KEY)


def answer_question(question: str) -> None:
    results = retrieve(question, k=5)

    if not results:
        print("I could not find relevant provisions in the indexed law.")
        return

    context_parts = []
    citations = {}

    for i, result in enumerate(results, start=1):
        metadata = result["metadata"]
        source_id = f"S{i}"

        section = metadata.get("section_number") or "Not specified"
        title = metadata.get("title") or "Untitled section"
        source_url = metadata.get("source_url") or "Not available"

        citations[source_id] = {
            "section": section,
            "title": title,
            "url": source_url,
        }

        context_parts.append(
            f"[{source_id}]\n"
            f"Section: {section}\n"
            f"Title: {title}\n"
            f"Source URL: {source_url}\n"
            f"Legal text:\n{result['text']}"
        )

    context = "\n\n---\n\n".join(context_parts)

    system_prompt = """
You are BanglaLawAI, a legal information assistant focused on
Bangladesh's Consumer Rights Protection Act, 2009.

Rules:
1. Answer using only the supplied legal passages.
2. Never invent statutory provisions, section numbers, or penalties.
3. Cite every legal claim using the provided source labels, such as [S2].
4. If the passages do not answer the question, say the available
   evidence is insufficient and do not guess.
5. Respond in the same language as the user's question.
6. Distinguish what the statute says from any general explanation.
7. Do not claim to provide personalized legal advice.
8. Be clear and concise. Do not cite a source label unless it
   supports the statement.
"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
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

    answer = response.choices[0].message.content
    print("\n" + "=" * 70)
    print("BANGLALAWAI ANSWER")
    print("=" * 70)
    print(answer or "The model returned an empty response.")

    print("\nSOURCES")
    print("-" * 70)

    for source_id, source in citations.items():
        print(
            f"[{source_id}] Section {source['section']}: "
            f"{source['title']}\n"
            f"    {source['url']}"
        )


if __name__ == "__main__":
    question = input("Ask a question about Bangladesh consumer rights law: ").strip()

    if not question:
        sys.exit("Please enter a question.")

    try:
        answer_question(question)
    except Exception as exc:
        sys.exit(f"Request failed: {type(exc).__name__}: {exc}")

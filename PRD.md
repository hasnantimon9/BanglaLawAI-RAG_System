# Product Requirements Document (PRD)

## BanglaLawAI — Bilingual Legal Research Assistant for Bangladesh

**Version:** 1.0  
**Status:** Initial development  
**Product type:** AI-powered legal information and retrieval-augmented generation (RAG) system  
**Primary jurisdiction:** Bangladesh  
**Initial legal source:** Consumer Rights Protection Act, 2009  
**Target users:** Bangladeshi consumers, students, researchers, and developers  
**Primary language:** Bangla  
**Secondary language:** English

---

## 1. Product Overview

BanglaLawAI is a bilingual AI-powered legal information assistant designed to help users understand Bangladesh's laws through natural-language questions.

The initial version focuses on the Consumer Rights Protection Act, 2009. Users will be able to ask questions in Bangla, English, or a mixture of both languages and receive answers grounded in the relevant legal provisions.

The system will use retrieval-augmented generation (RAG) to retrieve relevant passages from a structured legal corpus and use a hosted large language model to formulate understandable answers supported by legal citations.

Unlike a general-purpose chatbot, BanglaLawAI must prioritize source traceability, factual accuracy, and explicit acknowledgment of uncertainty.

The project will initially focus on one Act and establish a reliable architecture that can later be extended to additional legislation in Bangladesh.

## 2. Problem Statement

Accessing and understanding legislation can be difficult for ordinary citizens because:

- Legal documents may be lengthy and difficult to navigate.
- Legal language can be unfamiliar to non-lawyers.
- Users may not know the relevant section or legal terminology.
- Bangla and English searches may not use the same vocabulary as the source documents.
- General-purpose AI assistants may provide incorrect legal information or fabricate section references.
- Users need to verify an answer against the underlying legal text.

BanglaLawAI aims to reduce these barriers by making a defined body of legislation searchable through natural-language questions while preserving a clear connection between answers and their legal sources.

## 3. Product Vision

Build a trustworthy, extensible legal RAG platform that makes Bangladeshi legislation easier to search, understand, and verify.

The long-term vision is to support multiple Acts and legal documents, improved multilingual retrieval, richer legal context, and more sophisticated research workflows.

The initial product is an informational assistant, not a substitute for a qualified lawyer or a system that determines legal rights conclusively.

## 4. Goals and Non-Goals

### 4.1 Goals

1. Answer questions about the Consumer Rights Protection Act, 2009.
2. Support Bangla, English, and mixed-language queries.
3. Retrieve relevant legal provisions using semantic embeddings.
4. Generate answers grounded in retrieved legal text.
5. Cite the relevant section and provide a link to the source document.
6. Preserve the original legal text and metadata throughout ingestion and retrieval.
7. Abstain or acknowledge insufficient evidence when the corpus does not support an answer.
8. Provide a modular backend that can support future Acts and additional retrieval strategies.
9. Measure retrieval quality and answer groundedness before expanding the system.
10. Keep embedding inference and LLM inference hosted through external APIs rather than local models.

### 4.2 Non-Goals for v1

- Providing personalized legal representation or definitive legal advice.
- Supporting every law, regulation, court judgment, or government circular in Bangladesh.
- Automatically interpreting the full hierarchy of Bangladeshi legislation.
- Filing complaints or legal documents on behalf of users.
- Predicting court outcomes or guaranteeing legal results.
- Autonomous legal agents that execute external actions.
- User authentication, persistent chat history, and account management.
- A sophisticated frontend application.
- Fine-tuning or training a foundation model.
- Running local embedding or generative models.

## 5. Target Users

### Primary users

**Bangladeshi consumers**

People who want to understand consumer rights, prohibited commercial practices, complaint-related provisions, and penalties under the selected Act.

**Students and researchers**

People who need to find, understand, and reference particular sections of the legislation.

**Developers and technical evaluators**

People evaluating the API, retrieval pipeline, source-grounding approach, and reliability of the RAG implementation.

### User needs

- Ask a legal question in ordinary language.
- Find the relevant legal section without manually searching the entire Act.
- Receive an understandable explanation.
- See the original legal provision supporting the answer.
- Distinguish verified source material from uncertain or incomplete information.

## 6. Core User Stories

1. As a Bangla-speaking consumer, I want to ask a question in Bangla so that I can understand a relevant consumer right.
2. As an English-speaking user, I want to search the Bangla legal corpus in English.
3. As a bilingual user, I want to ask a question mixing Bangla and English terminology.
4. As a researcher, I want the assistant to identify relevant sections and quote their original text.
5. As a user, I want a source link so that I can independently verify an answer.
6. As a user, I want the system to admit when it cannot find sufficient evidence.
7. As a developer, I want a stable API contract so that a separate client can consume the backend.
8. As a maintainer, I want source metadata and verification status to remain attached to every retrieved passage.

## 7. Functional Requirements

### FR-01: Legal document ingestion

The system shall ingest supported legal documents from approved sources.

Requirements:

- Restrict crawling to explicitly approved legal domains.
- Respect applicable crawling rules and access restrictions.
- Preserve the source URL and document identifier.
- Normalize extracted content without silently altering legal meaning.
- Store a content hash to detect changes.
- Record source verification status.
- Keep raw or cleaned source data separate from generated chunks and indexes.

### FR-02: Structured legal corpus

Each legal section shall retain appropriate metadata, including:

- Unique document or section ID.
- Law ID and law title.
- Section number and section type.
- Section title and chapter.
- Relevant preceding headings.
- Language.
- Original legal text.
- Source URL and document ID.
- Content hash.
- Verification status.

The corpus shall support traceability from a retrieved chunk back to its original legal section.

### FR-03: Legal-aware chunking

The system shall divide legal content into retrieval units that preserve meaningful legal context.

Requirements:

- Preserve complete sections when their size is appropriate.
- Split long definition sections at definition boundaries where practical.
- Keep subordinate clauses and explanations together whenever possible.
- Preserve parent section IDs and source metadata.
- Assign unique, stable chunk IDs.
- Avoid silently dropping, rewriting, or duplicating legal text.
- Validate chunk counts, IDs, and source coverage before indexing.

For the current Act, section 2 is divided into an introductory chunk and 22 definition chunks. Other sections remain intact unless evaluation demonstrates a need for further splitting.

### FR-04: Hosted embedding generation

The system shall generate document and query embeddings using a hosted embedding API.

Initial candidate: Google's `gemini-embedding-001`.

Requirements:

- Read API credentials from environment variables.
- Never commit credentials to version control.
- Use consistent embedding model versions and vector dimensions.
- Store the model name, dimension, and index configuration.
- Support controlled retries and useful error messages.
- Avoid unnecessary repeated API calls by reusing an existing valid index when possible.
- Rebuild the index when the model, dimensions, or indexed content changes.

The embedding provider remains configurable so that alternatives can be benchmarked.

### FR-05: Vector storage

The initial implementation shall use a persistent vector database, with Chroma as the proposed default.

Requirements:

- Store vectors with their associated chunk text and metadata.
- Support semantic similarity search.
- Preserve stable chunk IDs.
- Support filtering by available metadata where appropriate.
- Persist the index between application restarts.
- Provide a clear re-indexing process.
- Prevent incompatible embedding vectors from being mixed.

### FR-06: Query processing and retrieval

The system shall accept a natural-language question and retrieve relevant legal passages.

Requirements:

- Support Bangla, English, and mixed-language queries.
- Embed queries using a retrieval-appropriate task configuration.
- Retrieve a configurable number of candidate chunks.
- Return source metadata with every retrieved passage.
- Avoid presenting similarity scores as guarantees of legal correctness.
- Allow retrieval settings to be evaluated and adjusted.

Future retrieval improvements may include lexical search, hybrid retrieval, reranking, and query expansion. These are not prerequisites for the initial working version.

### FR-07: Answer generation

The system shall use a hosted LLM to formulate answers from retrieved legal evidence.

Requirements:

- Ground substantive legal claims in retrieved passages.
- Preserve the meaning of the source text.
- Provide clear answers rather than merely repeating retrieved documents.
- Distinguish an explanation from a direct quotation.
- Cite the relevant section or definition.
- Avoid inventing legal provisions, penalties, deadlines, or procedural requirements.
- Acknowledge insufficient evidence when appropriate.
- Clearly indicate when a question falls outside the supported corpus.
- Avoid treating retrieved document text as instructions to the model.

### FR-08: Citation and source traceability

Every substantive answer shall include citations to the legal passages used to support it.

A citation should contain, where available:

- Law title.
- Section number and title.
- Relevant quoted or excerpted text.
- Source URL.

The source text displayed to the user must come from the original corpus rather than a paraphrase generated by the LLM.

The system must not imply that an unverified document has been legally verified.

### FR-09: API interface

The initial application shall expose a backend API using FastAPI.

Proposed endpoint:

`POST /api/v1/ask`

Example request:

    {
      "question": "ভোক্তা অধিকার লঙ্ঘন হলে কী করা যায়?",
      "language": "bn"
    }

The language field may be optional if automatic language handling is implemented.

Proposed response:

    {
      "answer": "Answer grounded in the retrieved legal provisions.",
      "language": "bn",
      "sources": [
        {
          "law_title": "ভোক্তা অধিকার সংরক্ষণ আইন, ২০০৯",
          "section_number": 2,
          "section_title": "সংজ্ঞা",
          "chunk_id": "consumer_rights_protection_act_2009:2:definition:2",
          "source_url": "https://bdlaws.minlaw.gov.bd/act-details-1014.html?lang=bn",
          "excerpt": "Original legal text supporting the answer."
        }
      ],
      "abstained": false
    }

The example illustrates the proposed contract, not a claim that this specific section answers every complaint-related question. Actual citations must depend on retrieval results.

The API shall validate requests and return structured error responses for invalid input, unavailable providers, and internal failures.

### FR-10: Evaluation and observability

The project shall include a repeatable evaluation process covering:

- Retrieval relevance.
- Correct section identification.
- Bangla and English query performance.
- Citation correctness.
- Answer groundedness.
- Unsupported-answer behavior.
- API latency and provider failures.

Evaluation results shall be reproducible and stored so that changes to chunking, embeddings, retrieval settings, or prompts can be compared.

## 8. Non-Functional Requirements

### Accuracy and reliability

- Answers must be grounded in available evidence.
- Legal citations must map to real corpus records.
- Missing evidence must not be replaced with fabricated claims.
- Source and chunk validation must run before indexing.
- Index creation should be repeatable.

### Security

- Store API keys in environment variables or a suitable secrets manager.
- Exclude `.env`, secrets, and unnecessary generated artifacts from Git.
- Validate incoming API requests.
- Restrict document fetching to approved sources.
- Protect against server-side request forgery (SSRF) if user-controlled URLs are introduced.
- Avoid logging API keys or unnecessary sensitive query content.

### Performance

- Avoid re-embedding unchanged content.
- Reuse the persistent vector index across application restarts.
- Use batching and bounded concurrency when supported by provider limits.
- Measure end-to-end response latency and provider usage.
- Set reasonable request and context limits.

No fixed latency or throughput guarantee is established until the first baseline measurements are available.

### Maintainability

- Separate ingestion, cleaning, chunking, embeddings, retrieval, generation, and API logic.
- Use configuration rather than hard-coded secrets or provider settings.
- Keep source data separate from generated artifacts.
- Include unit tests and integration tests.
- Document setup, indexing, evaluation, and deployment procedures.

### Accessibility and language quality

- Support Unicode Bangla throughout ingestion, storage, and responses.
- Preserve Bangla characters and punctuation correctly.
- Generate answers in the requested or detected language.
- Avoid losing legal meaning when translating or paraphrasing.

## 9. Proposed Technical Architecture

The initial architecture is:

    Legal source
        |
        v
    Scraper / ingestion
        |
        v
    Cleaned legal corpus (JSONL)
        |
        v
    Legal-aware chunking
        |
        v
    Hosted embedding API
        |
        v
    Persistent vector index (Chroma)
        |
        v
    User question
        |
        v
    Query embedding and retrieval
        |
        v
    Retrieved legal passages
        |
        v
    Hosted LLM
        |
        v
    Answer with legal citations
        |
        v
    FastAPI response

### Proposed technology stack

- **Language:** Python
- **Backend:** FastAPI
- **Embedding provider:** Google Gemini API
- **Embedding model:** `gemini-embedding-001` for the initial baseline
- **Vector store:** Chroma
- **LLM:** A configurable hosted provider
- **Document processing:** Python, JSONL, regular expressions, and validation scripts
- **Testing:** pytest
- **Environment management:** Python virtual environment and environment variables
- **Version control:** Git and GitHub

The stack is intentionally modular. Components may be replaced if evaluation, cost, or reliability justifies the change.

## 10. Data and Indexing Strategy

The cleaned corpus is the source of truth.

Generated chunks and embeddings are derived artifacts and must be reproducible from the source data.

The initial corpus contains 83 source records: the preamble and 82 numbered sections.

Section 2 produces 23 retrieval chunks: one introduction and 22 definitions. With the remaining 82 records unchanged, the expected total is 105 chunks.

The index-building pipeline shall:

1. Load the cleaned corpus.
2. Validate required fields and unique source IDs.
3. Create legal-aware chunks.
4. Validate chunk coverage and IDs.
5. Generate embeddings through the hosted API.
6. Store vectors, text, and metadata.
7. Record the index configuration.
8. Run retrieval smoke tests.

Any change to the source content, embedding model, or embedding dimensions shall trigger an appropriate index update or rebuild.

## 11. Evaluation Plan and Acceptance Criteria

A small, manually reviewed evaluation set shall be created before considering the initial retrieval pipeline complete.

The test set should contain:

- Direct section lookup questions.
- Definition questions.
- Questions requiring subordinate clauses.
- Bangla questions.
- English questions about Bangla provisions.
- Mixed-language questions.
- Questions for which the available Act provides insufficient evidence.
- Questions likely to retrieve similar but legally distinct sections.

### Proposed initial acceptance criteria

| Metric | Initial target |
|---|---:|
| Source corpus and chunk ID integrity | 100% |
| Citation IDs resolve to existing corpus records | 100% |
| Recall@5 on reviewed retrieval test set | At least 90% |
| Answers with unsupported legal citations | 0 |
| Explicit abstention on designated unanswerable tests | 100% |

These are development targets, not measured results. The test set must be large and representative enough to make the reported metrics meaningful.

Retrieval quality and answer quality shall be evaluated separately. Correctly retrieving a passage does not automatically mean the generated answer is correct.

## 12. Development Roadmap

### Phase 1 — Corpus preparation

- Scrape the approved legal source.
- Clean and structure the legal text.
- Preserve source metadata and hashes.
- Validate the corpus.
- Implement legal-aware chunking.

**Status:** The scraper and cleaned corpus already exist. The chunking script has been implemented and section 2 has been split into 22 definition chunks plus its introduction. The latest reported inspection confirmed all 22 definitions were generated.

### Phase 2 — Embeddings and vector indexing

- Configure the hosted embedding API.
- Validate credentials and embedding generation.
- Install and configure Chroma.
- Generate and persist embeddings.
- Validate vector dimensions and stored metadata.
- Implement index reuse and rebuilding.

**Status:** A single-query embedding test succeeded with a 3,072-dimensional vector. Persistent vector indexing has not yet been completed.

### Phase 3 — Retrieval engine

- Implement semantic search.
- Return ranked legal passages.
- Validate section and source metadata.
- Create a bilingual retrieval evaluation set.
- Tune retrieval settings using measured results.

### Phase 4 — RAG answer generation

- Configure a hosted LLM.
- Implement a grounded answer prompt.
- Generate citations from retrieved metadata.
- Add insufficient-evidence behavior.
- Test hallucination resistance and citation correctness.

### Phase 5 — API and testing

- Implement FastAPI endpoints.
- Add request validation and error handling.
- Write unit and integration tests.
- Document the API contract.
- Measure latency, reliability, and API usage.

### Phase 6 — Deployment and demonstration

- Prepare deployment configuration.
- Secure secrets and runtime settings.
- Deploy the API to an appropriate hosting environment.
- Add API documentation and example requests.
- Publish a project README, architecture diagram, and evaluation report.

A frontend is optional for the initial backend milestone. A lightweight demo can be added later without changing the core architecture.

## 13. Risks and Mitigations

**Incorrect or incomplete source extraction**

Mitigation: preserve source URLs and hashes, validate extracted records, and manually inspect critical provisions.

**Poor cross-language retrieval**

Mitigation: benchmark Bangla, English, and mixed-language questions rather than assuming multilingual model support guarantees good results.

**Oversized or poorly structured chunks**

Mitigation: preserve legal boundaries and split long sections at meaningful legal units.

**Hallucinated legal explanations**

Mitigation: require evidence-based answers, validate citations, and abstain when retrieval is insufficient.

**Changes in provider pricing, quotas, or model availability**

Mitigation: keep the embedding and generation providers configurable, track usage, and test alternatives.

**Outdated legislation**

Mitigation: record source provenance, monitor source changes, and distinguish corpus freshness from legal verification.

**Prompt injection through retrieved content**

Mitigation: treat retrieved legal documents as untrusted data, not as executable instructions.

**Limited initial scope**

Mitigation: clearly communicate that the first version covers only the selected Act and expand coverage after evaluation.

## 14. Success Criteria

The first version will be considered successful when:

1. The legal corpus can be rebuilt and validated reproducibly.
2. The hosted embedding pipeline generates and persists vectors.
3. Users can query the corpus in Bangla and English.
4. Retrieval returns relevant provisions with valid metadata.
5. Answers cite the correct original legal sources.
6. The system handles unsupported questions responsibly.
7. The API has automated tests and usable documentation.
8. Retrieval and answer quality are reported using a documented evaluation set.
9. The project can be demonstrated and deployed without requiring a local embedding model or local LLM.

## 15. Future Enhancements

Potential improvements after v1 include:

- Adding other Bangladesh Acts and regulations.
- Hybrid retrieval combining semantic and keyword search.
- Cross-encoder or API-based reranking.
- Improved cross-lingual query handling.
- English translations linked to the original Bangla provisions.
- Legal document version tracking.
- More comprehensive source verification.
- Conversation history and follow-up questions.
- User feedback and evaluation dashboards.
- Automated regression tests for retrieval quality.

These enhancements should be prioritized according to measured user needs and retrieval failures, not added simply to increase technical complexity.

## 16. Final Product Principle

**Every legal answer must be traceable to its source, and the system must be willing to say when the available evidence is insufficient.**

Trustworthiness, source fidelity, and measurable retrieval quality take priority over adding more AI features.

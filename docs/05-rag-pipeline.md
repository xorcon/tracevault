# 05 - RAG Pipeline

## Pipeline Objective

Create a retrieval-augmented generation pipeline that improves answer quality while preserving evidence traceability.

## RAG Pipeline Stages

```text
1. Ingest
2. Chunk
3. Clean / Normalize
4. Store Raw + Cleaned + Metadata + Proof
5. Embed Cleaned Text
6. Build Vector Index
7. Build Keyword Index
8. Retrieve
9. Rerank
10. Build Evidence Pack
11. Generate Grounded Answer
12. Verify Answer
13. Return Answer + Evidence Trace
```

## Semantic Refinement Stage

Purpose:

- reduce noise
- normalize writing style
- remove irrelevant filler
- preserve technical meaning
- improve embedding quality

Input:

```json
{
  "chunk_id": "doc_001_chunk_003",
  "raw_text": "..."
}
```

Output:

```json
{
  "chunk_id": "doc_001_chunk_003",
  "cleaned_text": "...",
  "summary": "...",
  "entities": [],
  "keywords": [],
  "risk_flags": [],
  "confidence": 0.92
}
```

## Hybrid Retrieval

Hermes Agent should combine:

| Retrieval Type | Best For |
|---|---|
| Vector search | semantic similarity and concept matching |
| BM25 / keyword search | exact names, IDs, terms, and policies |
| Metadata filter | time, source, topic, sensitivity, document type |
| Reranking | final relevance optimization |

## Retrieval Merge Logic

```text
vector_results = vector_search(query)
keyword_results = keyword_search(query)
metadata_filtered = apply_filters(vector_results + keyword_results)
merged = deduplicate_by_chunk_id(metadata_filtered)
reranked = rerank(query, merged)
evidence_pack = top_k(reranked)
```

## Evidence Pack Format

```json
{
  "query": "What are the main risks in this project?",
  "reasoning_mode": "pattern_detection",
  "evidence": [
    {
      "chunk_id": "doc_001_chunk_003",
      "document_id": "doc_001",
      "raw_text": "original source text",
      "cleaned_text": "normalized source text",
      "score": 0.87,
      "retrieval_source": "hybrid",
      "metadata": {
        "source_type": "project_note",
        "document_date": "2026-04-25"
      }
    }
  ]
}
```

## Grounding Rules

The reasoning model must follow these constraints:

1. Use only retrieved evidence.
2. Do not answer from general memory.
3. Cite supporting chunk IDs for major claims.
4. If evidence is weak, state uncertainty.
5. If evidence is missing, say what is missing.
6. Prefer raw text when verifying claims.

## Verification Stage

The verification layer checks:

- Are all major claims supported by evidence?
- Does each cited chunk actually support the claim?
- Did the model introduce facts not present in evidence?
- Are dates, names, numbers, and entities preserved correctly?
- Are there conflicts across evidence chunks?

## MVP Acceptance Test

A query is considered successful when:

- correct chunks are retrieved
- answer is grounded in retrieved evidence
- citations map to raw evidence
- unsupported claims are flagged
- the answer includes confidence and gaps

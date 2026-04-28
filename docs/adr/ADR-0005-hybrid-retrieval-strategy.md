# ADR-0005: Hybrid Retrieval Strategy

## Status

Proposed

## Date

2026-04-28

## Decision Owner

Natthakit Thussanaphan

## Related Phases

```text
Phase 3  — Semantic Refinement
Phase 4  — Hybrid Retrieval
Phase 5  — Grounded Reasoning and Validation
```

---

## Context

TraceVault requires a retrieval mechanism that is:

- accurate across documents, logs, configs, notes, and structured text
- deterministic and reproducible
- robust against semantic ambiguity
- capable of exact-match retrieval for critical enterprise tokens
- traceable back to `document_id`, `chunk_id`, and source hashes

Pure vector similarity search is insufficient for enterprise use cases because:

- embeddings may fail on exact identifiers
- semantic similarity may miss critical exact matches
- short or structured text is often poorly represented
- IP addresses, error codes, file paths, ticket IDs, and config keys require lexical precision

Pure keyword search is also insufficient because:

- it lacks semantic understanding
- it performs poorly on paraphrased queries
- it has weak recall for concept-based questions

Therefore, TraceVault will use a hybrid retrieval strategy.

---

## Decision

TraceVault will implement retrieval using both:

```text
Vector Similarity Search
+
BM25 Keyword Search
```

Results will be merged, normalized, deduplicated, and ranked with a configurable hybrid score.

```text
final_score = α * semantic_score + (1 - α) * keyword_score
```

Where:

- `semantic_score` is normalized vector similarity
- `keyword_score` is normalized BM25 score
- `α` is configurable

---

## Architecture

```text
User Query
   ↓
Query Processing
   ↓
┌──────────────────┬──────────────────┐
│ Vector Retrieval │ BM25 Retrieval   │
└────────┬─────────┴────────┬─────────┘
         ↓                  ↓
       Candidate Set Merge / Deduplication
         ↓
       Score Normalization
         ↓
       Hybrid Ranking
         ↓
       Top-K Evidence Candidates
```

---

## Default Configuration

| Parameter | Default |
|---|---:|
| vector_top_k | 20 |
| keyword_top_k | 20 |
| final_top_k | 8 |
| hybrid_alpha | 0.6 |

These defaults may be tuned through configuration, but scoring behavior must remain transparent and deterministic.

---

## Retrieval Result Model

Each retrieval result must preserve traceability:

```json
{
  "document_id": "doc_123",
  "chunk_id": "chunk_doc_123_0001",
  "source_raw_hash": "...",
  "cleaned_text": "...",
  "raw_text": "...",
  "semantic_score": 0.82,
  "keyword_score": 0.67,
  "final_score": 0.75,
  "retrieval_sources": ["vector", "bm25"]
}
```

The retrieval layer must not drop source metadata required for evidence pack construction.

---

## Retrieval Guarantees

### 1. Exact-match Preservation

The retrieval system must support exact matching for:

```text
IP addresses
error codes
ticket IDs
file paths
hostnames
config keys
command names
log fragments
version numbers
```

### 2. Semantic Recall

Conceptual or paraphrased queries must retrieve semantically relevant content even when exact keywords differ.

### 3. Deterministic Ranking

Given the same:

- query
- index state
- configuration

The same ranked result set must be produced.

### 4. Evidence Traceability

Every candidate result must be traceable to:

```text
document_id → chunk_id → raw_text_hash
```

---

## Merge Strategy

### Step 1 — Independent Retrieval

```text
vector_results  = top_k(vector_search)
keyword_results = top_k(bm25_search)
```

### Step 2 — Deduplication

Deduplicate by:

```text
(document_id, chunk_id)
```

### Step 3 — Score Normalization

Normalize score families independently into a comparable range.

```text
semantic_score ∈ [0, 1]
keyword_score  ∈ [0, 1]
```

### Step 4 — Hybrid Ranking

```text
final_score = α * semantic_score + (1 - α) * keyword_score
```

### Step 5 — Final Selection

Return `final_top_k` results with full metadata.

---

## Query Processing Constraints

Before retrieval, TraceVault may:

- trim the query
- normalize whitespace
- lowercase for lexical processing
- extract keywords for BM25

TraceVault must not:

- rewrite the query with an LLM in Phase 4
- add inferred tokens
- expand the query using external knowledge
- hide query transformations from debug output

---

## Indexing Strategy

Phase 4 indexing should use `cleaned_text` for retrieval quality while preserving links to `raw_text`.

Required index metadata:

- `document_id`
- `chunk_id`
- `chunk_index`
- `source_raw_hash`
- `content_hash`
- `source_path`
- `refinement_method`

The retrieval index must never become the source of truth. It is a derived artifact.

---

## Alternatives Considered

### Alternative 1 — Pure Vector Search

Rejected.

Vector search is useful for semantic recall but unreliable for exact identifiers and structured enterprise text.

### Alternative 2 — Pure BM25

Rejected.

BM25 is strong for lexical retrieval but weak for semantic or paraphrased queries.

### Alternative 3 — LLM-based Retrieval

Rejected for Phase 4.

LLM retrieval is non-deterministic, harder to test, and introduces cost and reproducibility risks.

### Alternative 4 — External SaaS Search Service

Rejected for baseline implementation.

TraceVault must remain local-first and portfolio-safe.

---

## Consequences

### Positive

- improves retrieval precision and recall
- supports both conceptual and exact-match queries
- better enterprise search behavior
- deterministic and auditable ranking
- prepares high-quality evidence packs for Phase 5

### Negative

- increases implementation complexity
- requires dual index maintenance
- score normalization must be tested
- hybrid weighting requires tuning

---

## Risk Mitigation

| Risk | Mitigation |
|---|---|
| Score imbalance | Normalize semantic and BM25 scores separately |
| Duplicate candidates | Deduplicate by `(document_id, chunk_id)` |
| Missing exact identifiers | Keep BM25 as first-class retrieval path |
| Semantic false positives | Preserve keyword score and evidence traceability |
| Latency growth | Bound top-k values |
| Ranking opacity | Expose semantic, keyword, and final scores |

---

## Acceptance Criteria

Phase 4 is complete when:

- vector retrieval exists
- BM25 retrieval exists
- hybrid score merging exists
- score normalization is deterministic
- duplicate candidates are merged
- results include full traceability metadata
- exact-match tests pass
- semantic-match tests pass
- mixed-query tests pass
- ranking tests pass
- no reasoning or validation logic is implemented in Phase 4

---

## Review Rules

A Phase 4 PR must be rejected if it:

- implements retrieval without `document_id` and `chunk_id`
- drops source raw hash metadata
- uses only vector search
- uses only BM25 without semantic retrieval
- performs LLM query rewriting without approved ADR
- makes external SaaS dependencies mandatory
- produces non-deterministic ranking for identical inputs
- implements reasoning or validation prematurely
- mutates `raw_text`
- commits generated indexes or private runtime data

---

## Decision Summary

TraceVault adopts hybrid retrieval combining vector similarity and BM25 keyword search.

This strategy provides:

- semantic recall
- exact-match reliability
- deterministic ranking
- traceable evidence candidates
- enterprise-grade retrieval quality

This ADR establishes the retrieval foundation required for Phase 5 grounded reasoning and validation.

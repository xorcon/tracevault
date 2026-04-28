# ADR-0005: Hybrid Retrieval Strategy

## Decision

Use hybrid retrieval:

score = α * semantic + (1 - α) * keyword

## Rationale

- Semantic handles meaning
- BM25 handles exact match

## Outcome

Deterministic, enterprise-grade retrieval.

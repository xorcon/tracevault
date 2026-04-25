# ADR-0002 - Use Hybrid Retrieval

## Status

Accepted

## Context

Vector search is strong for semantic matching but can miss exact terms. Enterprise knowledge often requires exact names, IDs, policies, vendors, and project terms.

## Decision

Hermes Agent will use hybrid retrieval:

- vector search over cleaned text
- keyword/BM25 search over raw and cleaned text
- metadata filtering
- reranking

## Consequences

Benefits:

- better recall
- stronger exact-match support
- improved enterprise search experience

Trade-offs:

- more complex retrieval pipeline
- scoring merge logic required
- evaluation needed to tune results

# ADR-0001 - Use Dual Context Storage

## Status

Accepted

## Context

Enterprise AI systems need both high-quality semantic retrieval and strong auditability. Cleaned text improves retrieval and reasoning, but original raw text is required for source-of-truth verification.

## Decision

TraceVault will store both:

- `raw_text`: original source evidence
- `cleaned_text`: normalized semantic version for retrieval and reasoning

All generated answers must trace back to raw evidence.

## Consequences

Benefits:

- stronger auditability
- better retrieval quality
- improved user trust
- explicit proof chain

Trade-offs:

- more storage required
- more metadata management
- additional verification logic needed

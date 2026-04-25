# 04 - Data Governance and Proof Chain

## Governance Objective

TraceVault must be able to answer this question for every output:

> Which exact source evidence caused the system to generate this answer?

This is the central design difference between a demo chatbot and an enterprise knowledge reasoning system.

## Source-of-Truth Rule

`raw_text` is the source of truth.

`cleaned_text` is a retrieval and reasoning optimization artifact.

If `raw_text` and `cleaned_text` conflict, `raw_text` wins.

## Dual Context Storage

| Field | Purpose | Trust Level |
|---|---|---|
| raw_text | Original source evidence | Highest |
| cleaned_text | Semantic normalized version | Medium |
| summary | Retrieval preview and UI display | Medium |
| metadata | Filtering, lineage, governance | High if system-generated |
| proof | Integrity, model trace, versioning | High |

## Proof Chain

A proof chain records how a piece of knowledge moved through the system:

```text
Source file
  -> document_id
  -> raw_text
  -> raw_hash
  -> cleaned_text
  -> cleaned_hash
  -> embedding_id
  -> retrieved evidence
  -> cited answer
```

## Required Metadata

| Metadata | Reason |
|---|---|
| document_id | Link chunks to original document |
| chunk_id | Cite exact evidence unit |
| source_type | Know if source is note, PDF, issue, meeting, etc. |
| imported_at | Audit import timing |
| document_date | Support temporal reasoning |
| author | Useful for trust and ownership |
| topic_tags | Filtering and discovery |
| sensitivity | Data protection and access control |
| retention_class | Governance and lifecycle management |

## Chunk Integrity

Each chunk should have at least two hashes:

- `raw_hash`: hash of original raw text
- `cleaned_hash`: hash of cleaned text

This allows detection of accidental or unauthorized changes.

## Cleaning Governance

The semantic refinement model must follow these rules:

1. Do not add facts not present in raw text.
2. Do not remove important qualifiers.
3. Preserve names, dates, IDs, numbers, and technical terms.
4. Preserve uncertainty.
5. Mark unclear statements rather than inventing clarity.
6. Keep raw text available for user verification.

## Answer Governance

Every answer should include:

- direct answer
- evidence-based reasoning
- supporting evidence references
- confidence level
- assumptions
- gaps or limitations
- recommended next step

## Audit Events

The system should log:

- document imported
- chunk created
- chunk refined
- index updated
- query submitted
- evidence retrieved
- answer generated
- verification result
- unsupported claim detected

## Enterprise Value

This governance layer supports:

- auditability
- compliance review
- hallucination reduction
- executive trust
- knowledge reuse
- AI risk management

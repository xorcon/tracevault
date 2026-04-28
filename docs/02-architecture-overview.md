# Architecture Overview — TraceVault

## Purpose

This document defines the end-state architecture of TraceVault as an **enterprise-grade, traceable AI knowledge system**.

TraceVault is designed to:

- preserve raw source truth
- improve retrieval quality through semantic refinement
- support hybrid retrieval across semantic and exact-match queries
- generate answers only from bounded evidence
- validate unsupported claims
- convert validated answers into durable knowledge artifacts

---

## End-to-End Architecture

```text
Raw Sources
  → Ingestion
  → Differential Ingest
  → Chunking
  → Semantic Refinement
  → Dual-Context Storage
  → Hybrid Retrieval
  → Evidence Pack
  → Grounded Reasoning
  → Validation
  → Evidence-backed Wiki Export
  → Wiki Health / Lint / Drift Check
  → Optional Obsidian Vault Adapter
```

---

## Architecture Diagram

```text
                ┌────────────────────────────┐
                │   Compiled Knowledge Wiki  │
                │   (auditable, versioned)   │
                └────────────┬───────────────┘
                             ↑
                     Evidence-backed synthesis
                             ↑
┌────────────┐    ┌──────────────┐    ┌──────────────┐
│ Raw Source │ →  │ Refinement   │ →  │ Retrieval    │
│ (truth)    │    │ (cleaned)    │    │ (hybrid)     │
└────────────┘    └──────────────┘    └──────────────┘
                             ↓
                      Reasoning Engine
                             ↓
                     Validation Layer
                             ↓
                     Evidence Pack Output
```

---

## Architecture Layers

### 1. Raw Source Layer

```text
raw_text = source of truth
```

Responsibilities:

- preserve original decoded source text
- compute deterministic content hash
- maintain source metadata
- preserve canonical source path
- support differential ingest

Guarantees:

- raw source is never overwritten by refinement
- raw source wins over all derived artifacts

---

### 2. Semantic Refinement Layer

```text
raw_text → cleaned_text
```

Responsibilities:

- deterministic chunking
- raw chunk preservation
- cleaned-text derivation
- refinement metadata
- no-new-facts safeguard
- source raw hash tracking

Core record:

```json
{
  "document_id": "...",
  "chunk_id": "...",
  "chunk_index": 0,
  "raw_text": "...",
  "cleaned_text": "...",
  "source_raw_hash": "...",
  "metadata": {
    "refinement_method": "...",
    "prompt_version": "...",
    "no_new_facts_checked": true
  }
}
```

---

### 3. Hybrid Retrieval Layer

```text
cleaned_text → candidate evidence
```

Components:

- vector similarity search
- BM25 keyword search
- score normalization
- candidate deduplication
- final ranking

Scoring model:

```text
score = α * semantic_score + (1 - α) * keyword_score
```

Retrieval result must include:

```json
{
  "document_id": "...",
  "chunk_id": "...",
  "source_raw_hash": "...",
  "semantic_score": 0.82,
  "keyword_score": 0.67,
  "final_score": 0.75
}
```

---

### 4. Evidence Pack Layer

```text
top-k retrieval → bounded evidence context
```

The evidence pack is the only allowed context for grounded reasoning.

It should include:

- retrieved chunks
- source metadata
- retrieval scores
- deduplication metadata
- confidence signals
- traceability references

---

### 5. Grounded Reasoning Layer

```text
evidence_pack → answer
```

Constraints:

- no free-form memory-based answers
- no unsupported claims
- no hidden source assumptions
- answer must be bounded by evidence

---

### 6. Validation Layer

```text
answer → validated_answer
```

Checks:

- unsupported claims
- contradiction detection
- source coverage
- confidence scoring
- evidence completeness

Example validation output:

```json
{
  "validation_status": "passed",
  "confidence": 0.92,
  "unsupported_claims": [],
  "contradictions": []
}
```

---

### 7. Compiled Knowledge Wiki Layer

```text
validated_answer → compiled_wiki_note
```

Purpose:

- convert validated answers into durable knowledge artifacts
- preserve claim-to-evidence mapping
- support audit and review
- enable enterprise knowledge lifecycle management

The wiki layer is downstream of validation and must not become source of truth.

---

## Source-of-Truth Hierarchy

```text
1. raw_text
2. cleaned_text
3. evidence_pack
4. validated_answer
5. compiled_wiki_note
```

Conflict resolution:

```text
raw_text wins over cleaned_text
evidence_pack wins over validated_answer
validated evidence wins over compiled_wiki_note
```

---

## Design Guarantees

### Traceability

Every answer must map back to:

```text
document_id → chunk_id → raw_text
```

### Determinism

Core pipeline behavior must be reproducible:

- ingest hashing
- document identity
- chunking
- manifest change detection
- hybrid ranking given the same index state

### Auditability

TraceVault must be able to answer:

```text
Why did the AI say this?
Which source supports this?
Which chunk produced this claim?
Has the source changed since this note was generated?
```

### No-new-facts Rule

```text
No evidence → No claim
```

---

## Architecture Constraints

- local-first baseline
- no mandatory SaaS dependency
- no silent mutation of raw source
- no destructive wiki overwrites by default
- no model output accepted without validation
- public repository must not contain private runtime data

---

## Future Evolution

| Phase | Capability |
|---|---|
| 3B | Optional local model refinement |
| 4 | Hybrid retrieval |
| 5 | Grounded reasoning and validation |
| 6A | Evidence-backed wiki export |
| 6B | Wiki health / lint / drift check |
| 6C | Optional Obsidian vault adapter |

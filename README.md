# TraceVault

TraceVault is an enterprise-grade, local-first AI knowledge system designed for **traceable, auditable, and evidence-grounded reasoning**.

Unlike traditional RAG systems, TraceVault enforces a strict proof-chain model:

```text
raw_text → cleaned_text → evidence → validated answer → knowledge artifact
```

Every output is:

- traceable to source documents
- verifiable at chunk level
- bounded by evidence
- designed for audit-ready AI reasoning

---

## System Architecture

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

## Core Design Principles

### 1. Source of Truth Hierarchy

```text
raw_text      = authoritative truth
cleaned_text  = processing layer
evidence_pack = bounded reasoning context
answer        = derived output
wiki_note     = human-readable artifact, not truth
```

Conflict resolution:

```text
raw_text > evidence_pack > validated_answer > compiled_wiki_note
```

### 2. Dual Context Architecture

TraceVault stores both:

- `raw_text` for traceability and audit
- `cleaned_text` for semantic processing and retrieval

This enables high-signal retrieval without sacrificing source verification.

### 3. Evidence-first Reasoning

TraceVault does not generate free-form answers from memory.

It follows this model:

```text
retrieve → constrain → reason → validate
```

All major claims must map back to evidence.

### 4. No-new-facts Constraint

```text
No evidence → No claim
```

This rule is central to enterprise use cases where reliability, governance, and auditability matter.

---

## Pipeline Stages

### Phase 1 — Python Foundation

- Python package baseline
- CLI foundation
- environment-based settings
- test infrastructure

### Phase 2 — Ingestion and Differential Ingest

- local plaintext ingestion
- SHA-256 content hashing
- deterministic document identity
- manifest-based change detection
- canonical path normalization
- corrupted-manifest fail-closed behavior

### Phase 3A — Semantic Refinement Foundation

- deterministic chunking
- hard chunk-size boundaries
- `raw_text` / `cleaned_text` dual-context records
- rule-based refinement
- no-new-facts safeguard
- per-chunk proof metadata

### Phase 3B — Optional Local Model Refinement

- optional local model adapter
- deterministic fallback
- model-output guardrails
- no-new-facts validation after model refinement

### Phase 4 — Hybrid Retrieval

- vector similarity search
- BM25 keyword search
- score normalization
- deterministic candidate merging
- traceable evidence candidates

### Phase 5 — Grounded Reasoning and Validation

- evidence pack construction
- constrained reasoning
- unsupported-claim detection
- contradiction detection
- confidence scoring

### Phase 6 — Compiled Knowledge Wiki

#### Phase 6A — Evidence-backed Wiki Export

- Markdown knowledge notes
- claim-to-evidence mapping
- proposal-first, non-destructive export

#### Phase 6B — Wiki Health / Lint / Drift Check

- missing evidence checks
- stale source hash detection
- contradiction and orphan note detection

#### Phase 6C — Optional Obsidian Vault Adapter

- Obsidian-compatible Markdown export
- no Obsidian runtime dependency
- TraceVault metadata preserved

---

## What Makes TraceVault Different

| Capability | Traditional RAG | TraceVault |
|---|---|---|
| Source traceability | Partial | Full chunk-level traceability |
| Raw vs cleaned context | Usually absent | Explicit dual-context model |
| Exact-match retrieval | Weak | BM25 + vector hybrid retrieval |
| Evidence mapping | Weak | Required |
| Validation layer | Rare | Built into roadmap |
| Knowledge persistence | None | Evidence-backed wiki layer |
| Audit readiness | Low | High |

---

## Positioning

TraceVault is not:

```text
chatbot
vector search demo
personal note-taking tool
```

TraceVault is:

```text
Enterprise Knowledge Governance System
Grounded AI Reasoning Platform
Hybrid Cloud + AI Architecture Portfolio Project
```

---

## Roadmap

```text
Phase 3B → Optional Local Model Refinement
Phase 4  → Hybrid Retrieval
Phase 5  → Grounded Reasoning + Validation
Phase 6  → Evidence-backed Knowledge Wiki Layer
```

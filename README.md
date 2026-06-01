# TraceVault

TraceVault is an enterprise-grade, local-first AI knowledge governance system designed for **traceable, auditable, and evidence-grounded knowledge workflows**.

Unlike traditional RAG prototypes, TraceVault enforces a strict proof-chain model:

```text
raw_text → cleaned_text → retrieval result → evidence pack → derived knowledge artifact
```

Every output is designed to be:

- traceable to source documents
- verifiable at chunk level
- bounded by evidence
- safe for audit-oriented enterprise AI workflows

---

## Current Status

TraceVault currently includes implemented foundations for:

- local-first ingestion and differential manifest tracking
- deterministic semantic refinement with raw/cleaned dual context
- optional local model refinement with guardrails
- deterministic hybrid retrieval foundation
- retrieval contract hardening for custom retriever injection
- evidence pack and grounded context assembly
- evidence-backed Markdown wiki export
- wiki health / lint / drift checking
- optional Obsidian-friendly vault adaptation

Phase 6C is complete and hardened through follow-up review.

```text
Phase 6C — Optional Obsidian-Friendly Vault Adapter: complete
Primary PR: #11
Follow-up PR: #13
Final merge commit: 1269b805a184b6a61680a90bd7915af89ae02a8d
Worklog: docs/worklogs/TraceVault_Phase_6C_Worklog.md
```

Near-term focus is repository stabilization, agent guidance alignment, and cleanup of non-blocking tooling warnings before the next major feature phase.

---

## System Architecture

```text
┌────────────────────────────────────────────────────┐
│          Optional Vault Adapter Layer              │
│  Obsidian-friendly organization, no dependency     │
└──────────────────────────▲─────────────────────────┘
                           │
┌──────────────────────────┴─────────────────────────┐
│          Compiled Knowledge Wiki Layer             │
│  Evidence-backed export + health validation        │
└──────────────────────────▲─────────────────────────┘
                           │
                  Evidence-backed artifacts
                           │
┌────────────┐    ┌──────────────┐    ┌──────────────┐
│ Raw Source │ →  │ Refinement   │ →  │ Retrieval    │
│ (truth)    │    │ (cleaned)    │    │ (hybrid)     │
└────────────┘    └──────────────┘    └──────┬───────┘
                                             ↓
                                      Evidence Pack
                                             ↓
                                  Derived Knowledge Output
```

Phase 6 is split into:

```text
Phase 6A — Evidence-backed Wiki Export
Phase 6B — Wiki Health / Lint / Drift Check
Phase 6C — Optional Obsidian-Friendly Vault Adapter
```

---

## Core Design Principles

### 1. Source of Truth Hierarchy

```text
raw_text      = authoritative truth
cleaned_text  = processing layer
retrieval     = candidate selection layer
evidence_pack = bounded grounded context
wiki_note     = human-readable derived artifact, not truth
vault_copy    = organized copy of a wiki note, not truth
```

Conflict resolution:

```text
raw_text > evidence_pack > derived_answer > compiled_wiki_note > vault_copy
```

### 2. Dual Context Architecture

TraceVault stores both:

- `raw_text` for traceability and audit
- `cleaned_text` for semantic processing and retrieval

This enables high-signal retrieval without sacrificing source verification.

### 3. Evidence-first Reasoning Boundary

TraceVault does not generate free-form answers from memory.

It follows this model:

```text
retrieve → constrain → assemble evidence → validate before downstream use
```

All major claims must map back to evidence.

### 4. No-new-facts Constraint

```text
No evidence → No claim
```

This rule is central to enterprise use cases where reliability, governance, and auditability matter.

### 5. Artifact Validation Before Knowledge Persistence

Compiled wiki notes are derived artifacts. They must remain inspectable and health-checkable before downstream use.

Phase 6B validates wiki artifacts for:

- frontmatter integrity
- TraceVault metadata consistency
- claim-to-evidence citation mapping
- evidence reference identity
- source hash drift when an explicit manifest is provided

### 6. Filesystem-Safe Adapter Boundary

The vault adapter is organization-only. It must not become a source of truth or an Obsidian runtime integration.

Phase 6C enforces:

- Phase 6B health preflight before adaptation
- path-scoped `vault_dir` exclusion only
- byte-preserving note copy via `shutil.copy2`
- case-insensitive destination collision protection
- marker/ownership-based generated artifact cleanup
- pre-write reserved-path ownership validation
- preservation of `generate_index=False` semantics
- no `.obsidian/`, plugin, sync, publishing, LLM, or claim/evidence rewriting behavior

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

### Phase 4 — Hybrid Retrieval Foundation

- deterministic in-memory keyword retrieval
- deterministic vector placeholder
- metadata filtering
- text retrieval policy
- hybrid score merge
- traceable `RetrievalResult` / `RetrievalTrace`
- no real vector database or embedding dependency yet

### Phase 4.1 — Retrieval Contract Hardening

- pipeline-owned default text policy
- custom keyword retriever compatibility
- provenance preservation from retrieval candidates
- execution metadata aligned with response metadata

### Phase 5 — Evidence Pack & Grounded Context Assembly

- `EvidencePack` request / response models
- deterministic evidence item selection
- duplicate and budget exclusion tracking
- retrieval provenance preservation
- assembled grounded context
- no answer generation, reasoning, citation validation, or contradiction detection

### Phase 6 — Compiled Knowledge Wiki

#### Phase 6A — Evidence-backed Wiki Export

- Markdown knowledge notes
- YAML frontmatter
- claim-to-evidence mapping
- proposal-first, non-destructive export
- deterministic filename identity
- strict proof-chain checks

#### Phase 6B — Wiki Health / Lint / Drift Check

- YAML frontmatter validation
- `note_id` / `note_type` / `schema_version` / `status` checks
- `source_policy` and `validation_status` checks
- `evidence_count` consistency checks
- claim citation resolution
- evidence reference `document_id` / `chunk_id` checks
- duplicate evidence label detection
- duplicate `note_id` detection across directories
- orphan / malformed note detection
- source hash drift checks via explicit manifest
- structured JSON health reports
- fail-closed malformed note / manifest handling

#### Phase 6C — Optional Obsidian-Friendly Vault Adapter

- optional vault adapter under `src/tracevault/wiki/vault/`
- plan-first adaptation
- health preflight via Phase 6B
- byte-preserving Markdown copy
- deterministic vault layout
- metadata-only index generation
- deterministic vault manifest
- case-insensitive collision detection
- marker/ownership-based stale generated artifact cleanup
- reserved-path pre-write validation
- no Obsidian dependency, plugin, `.obsidian/`, sync, publishing, or LLM behavior

---

## CLI Examples

### Diagnose package health

```bash
python3 -m tracevault diagnose
```

### Ingest local source files

```bash
python3 -m tracevault ingest <path>
python3 -m tracevault ingest <path> --json
```

### Validate exported wiki notes

```bash
python3 -m tracevault wiki-health <path>
python3 -m tracevault wiki-health <path> --json
python3 -m tracevault wiki-health <path> --strict
python3 -m tracevault wiki-health <path> --source-manifest <manifest.json>
```

The wiki health checker validates frontmatter, evidence references, citation resolution, duplicate note identity, malformed notes, and source hash drift when an explicit manifest is provided.

### Plan an Obsidian-friendly vault adaptation

```bash
python3 -m tracevault wiki-vault-plan <exported-wiki-dir> --vault-dir <vault-dir>
python3 -m tracevault wiki-vault-plan <exported-wiki-dir> --vault-dir <vault-dir> --json
```

The plan command runs health preflight and writes nothing.

### Apply an Obsidian-friendly vault adaptation

```bash
python3 -m tracevault wiki-vault-adapt <exported-wiki-dir> <vault-dir>
python3 -m tracevault wiki-vault-adapt <exported-wiki-dir> <vault-dir> --json
```

The adapt command copies healthy exported notes into a deterministic vault structure and may generate metadata-only indexes and a manifest. It fails closed on health errors, destination collisions, unsafe reserved paths, and write failures.

---

## Implementation Status

```text
Phase 1   — Python Foundation                         complete
Phase 2   — Ingestion + Differential Ingest            complete
Phase 3A  — Semantic Refinement Foundation             complete
Phase 3B  — Optional Local Model Refinement            complete
Phase 4   — Hybrid Retrieval Foundation                complete
Phase 4.1 — Retrieval Contract Hardening               complete
Phase 5   — Evidence Pack & Grounded Context Assembly  complete
Phase 6A  — Evidence-backed Wiki Export                complete
Phase 6B  — Wiki Health / Lint / Drift Check           complete
Phase 6C  — Optional Obsidian-Friendly Vault Adapter   complete
```

---

## Worklogs

Phase worklogs capture implementation decisions, review loops, merge evidence, and lessons learned.

```text
docs/worklogs/TraceVault_Phase_6C_Worklog.md
```

Phase 6C worklog covers:

- adapter-only boundary
- health preflight design
- path-scoped exclusion
- byte-preserving copy
- collision safety
- stale manifest/index cleanup
- marker/ownership semantics
- `generate_index=False` behavior
- PR #11 / #13 merge evidence

---

## What Makes TraceVault Different

| Capability | Traditional RAG | TraceVault |
|---|---|---|
| Source traceability | Partial | Full chunk-level traceability |
| Raw vs cleaned context | Usually absent | Explicit dual-context model |
| Retrieval governance | Often opaque | Deterministic keyword baseline + labeled vector placeholder |
| Evidence mapping | Weak | Required |
| Evidence pack assembly | Often implicit | Explicit, inspectable, budget-aware |
| Wiki artifact validation | Rare | Built-in wiki health / lint / drift check |
| Vault organization | External/manual | Optional adapter with health preflight and ownership safety |
| Knowledge persistence | Usually external | Evidence-backed wiki layer |
| Audit readiness | Low | High |

---

## Positioning

TraceVault is not:

```text
chatbot
vector search demo
personal note-taking tool
Obsidian plugin
```

TraceVault is:

```text
Enterprise Knowledge Governance System
Grounded AI Evidence Platform
Hybrid Cloud + AI Architecture Portfolio Project
```

---

## Roadmap

Near-term focus:

```text
repository stabilization
documentation and agent guidance alignment
non-blocking tooling cleanup, including Ruff config migration
```

Future extensions may include:

```text
real vector index lifecycle
embedding integration with explicit provenance
reasoning engine implementation
validation / verification engine implementation
portfolio-grade deployment packaging
```

These future extensions must preserve TraceVault's proof-chain model and source-of-truth hierarchy.

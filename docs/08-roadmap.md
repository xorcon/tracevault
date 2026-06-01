# 08 - Roadmap

## Roadmap Philosophy

Build the smallest system that demonstrates enterprise-grade architecture maturity, then expand toward AI platform depth.

TraceVault's roadmap is intentionally proof-chain first:

```text
source preservation
  -> deterministic processing
  -> traceable retrieval
  -> evidence assembly
  -> derived artifact validation
  -> optional organization adapters
  -> later reasoning / validation layers
```

Do not add advanced AI features unless they preserve traceability, local-first operation, and auditability.

---

## Completed Foundation Through Phase 6C

### Phase 1 — Python Foundation

Status: Complete

Delivered:

- Python package baseline
- CLI foundation
- environment-based settings
- test infrastructure

### Phase 2 — Ingestion and Differential Ingest

Status: Complete

Delivered:

- local plaintext ingestion
- SHA-256 content hashing
- deterministic document identity
- manifest-based change detection
- canonical path normalization
- corrupted-manifest fail-closed behavior

### Phase 3A — Semantic Refinement Foundation

Status: Complete

Delivered:

- deterministic chunking
- hard chunk-size boundaries
- `raw_text` / `cleaned_text` dual-context records
- rule-based refinement
- no-new-facts safeguard
- per-chunk proof metadata

### Phase 3B — Optional Local Model Refinement

Status: Complete

Delivered:

- optional local model adapter
- deterministic fallback
- model-output guardrails
- no-new-facts validation after model refinement

### Phase 4 — Hybrid Retrieval Foundation

Status: Complete

Delivered:

- deterministic in-memory keyword retrieval
- deterministic vector placeholder
- metadata filtering
- text retrieval policy
- hybrid score merge
- traceable `RetrievalResult` / `RetrievalTrace`
- no real vector database or embedding dependency yet

### Phase 4.1 — Retrieval Contract Hardening

Status: Complete

Delivered:

- pipeline-owned default text policy
- custom keyword retriever compatibility
- provenance preservation from retrieval candidates
- execution metadata aligned with response metadata

### Phase 5 — Evidence Pack and Grounded Context Assembly

Status: Complete

Delivered:

- `EvidencePack` request / response models
- deterministic evidence item selection
- duplicate and budget exclusion tracking
- retrieval provenance preservation
- assembled grounded context
- no answer generation, reasoning, citation validation, or contradiction detection

### Phase 6A — Evidence-backed Wiki Export

Status: Complete

Delivered:

- Markdown knowledge notes
- YAML frontmatter
- claim-to-evidence mapping
- proposal-first, non-destructive export
- deterministic filename identity
- strict proof-chain checks

### Phase 6B — Wiki Health / Lint / Drift Check

Status: Complete

Delivered:

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

### Phase 6C — Optional Obsidian-Friendly Vault Adapter

Status: Complete

Delivered:

- optional vault adapter package under `src/tracevault/wiki/vault/`
- plan-first adaptation
- Phase 6B health preflight
- byte-preserving note copy
- deterministic vault layout
- metadata-only index generation
- deterministic vault manifest
- case-insensitive collision detection
- marker/ownership-based stale artifact cleanup
- reserved-path pre-write validation
- `generate_index=False` semantics
- CLI commands for plan/apply
- synthetic test coverage for repeated-run and failure-path behavior

Merge evidence:

```text
Primary PR: #11 — feat: add optional obsidian vault adapter
Follow-up PR: #13 — fix: harden phase 6c vault adapter follow-up behavior
Final merge commit: 1269b805a184b6a61680a90bd7915af89ae02a8d
Worklog: docs/worklogs/TraceVault_Phase_6C_Worklog.md
```

---

## Current Near-Term Focus

The recommended next work is stabilization, not a large new feature.

### Stabilization Workstream

Recommended next items:

1. Keep documentation aligned with Phase 6C completion.
2. Keep local agent guidance aligned with the Phase 6C worklog.
3. Migrate deprecated Ruff settings into the current `[tool.ruff.lint]` layout.
4. Review documentation for stale phase references.
5. Keep `main` green after each small documentation or tooling update.

Success criteria:

```text
git status clean
python3 -m pytest -q passes
python3 -m ruff check . passes
python3 -m tracevault diagnose passes
python3 -m compileall src tests passes
```

---

## Future Feature Candidates

Future work should be selected only after the stabilization workstream is clean.

### Candidate A — Real Vector Index Lifecycle

Goal: Replace or supplement the deterministic vector placeholder with a real vector index while preserving explicit provenance.

Required guardrails:

- no loss of `document_id` / `chunk_id`
- index build traceability
- stale index detection
- reproducible local fallback
- no hidden external API dependency for baseline tests

### Candidate B — Embedding Integration With Explicit Provenance

Goal: Add embedding generation while making model, version, source hash, and embedding timestamp auditable.

Required guardrails:

- source raw hash recorded
- embedding model identity recorded
- embedding generation deterministic where possible
- model failure does not corrupt source data

### Candidate C — Reasoning Engine Implementation

Goal: Generate answers from evidence packs only.

Required guardrails:

- answer from evidence pack only
- no answer from memory
- unsupported claims flagged
- citations map to evidence labels
- contradiction and low-confidence behavior explicit

### Candidate D — Validation / Verification Engine

Goal: Validate generated answers against evidence.

Required guardrails:

- claim extraction
- citation coverage checks
- unsupported claim detection
- contradiction detection
- JSON and human-readable reports

### Candidate E — Portfolio-grade Deployment Packaging

Goal: Create a credible local/hybrid deployment path without weakening local-first operation.

Required guardrails:

- no secrets in repo
- local default deployment
- documented cloud/hybrid extension path
- observability and security design

---

## Portfolio Milestones

| Milestone | Portfolio Output |
|---|---|
| Architecture docs complete | GitHub repo shows architect thinking |
| Ingestion/refinement/retrieval foundation | Local walkthrough of traceable pipeline |
| Evidence pack and wiki export | Proof of grounded AI artifact generation |
| Wiki health / vault adapter | Evidence of filesystem safety and governance maturity |
| Evaluation / verification scorecard | Evidence of engineering maturity |
| Deployment blueprint | Hybrid cloud architecture credibility |
| Case study published | Resume / LinkedIn leverage |

---

## Roadmap Rule

Every future phase must preserve this hierarchy:

```text
raw_text > cleaned_text > retrieval result > evidence pack > wiki note > vault copy > final answer
```

If a proposed feature weakens this hierarchy, it is out of scope until an ADR explicitly approves the change.

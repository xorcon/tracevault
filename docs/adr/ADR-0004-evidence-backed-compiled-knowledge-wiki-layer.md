# ADR-0004: Evidence-backed Compiled Knowledge Wiki Layer

## Status

Proposed

## Date

2026-04-28

## Decision Owner

Natthakit Thussanaphan

## Related Phases

```text
Phase 3B — Optional Local Model Refinement
Phase 4  — Hybrid Retrieval
Phase 5  — Grounded Reasoning and Validation
Phase 6  — Evidence-backed Compiled Knowledge Wiki Layer
```

Phase 6 is split into:

```text
Phase 6A — Evidence-backed Wiki Export
Phase 6B — Wiki Health / Lint / Drift Check
Phase 6C — Optional Obsidian Vault Adapter
```

## Context

TraceVault is an enterprise-grade, local-first AI knowledge system designed around source traceability, dual-context storage, grounded retrieval, evidence-backed reasoning, and validation against unsupported claims.

The current architecture establishes this hierarchy:

```text
raw_text      = source of truth
cleaned_text  = processing and retrieval aid
evidence pack = bounded reasoning context
answer        = generated from evidence only
```

After Phase 5, TraceVault needs a way to convert validated answers and evidence-backed insights into durable knowledge artifacts that humans can inspect, version, review, and reuse.

A compiled wiki layer provides this capability.

However, compiled notes must not become an unverified source of truth. The original raw source and evidence chain must remain authoritative. The wiki is a human-facing knowledge artifact, not a replacement for the underlying proof chain.

## Decision

TraceVault will introduce an Evidence-backed Compiled Knowledge Wiki Layer after reasoning and validation are implemented.

The wiki layer will generate human-readable Markdown knowledge artifacts from validated evidence packs and grounded answers.

The wiki layer must preserve source traceability and must never override the raw source proof chain.

Source-of-truth hierarchy:

```text
1. raw_text
   Authoritative source of truth.

2. cleaned_text
   Derived retrieval/reasoning aid.

3. evidence_pack
   Bounded set of retrieved source-backed evidence.

4. validated_answer
   Generated answer checked against evidence.

5. compiled_wiki_note
   Human-readable knowledge artifact derived from validated evidence.
```

Conflict rule:

```text
raw_text wins over cleaned_text
evidence_pack wins over validated_answer
validated evidence wins over compiled_wiki_note
```

## Architecture Position

The wiki layer is downstream of validation.

```text
Raw Sources
  -> Ingestion
  -> Differential Ingest
  -> Chunking
  -> Semantic Refinement
  -> Dual-Context Storage
  -> Hybrid Retrieval
  -> Evidence Pack
  -> Grounded Reasoning
  -> Validation
  -> Evidence-backed Wiki Export
  -> Wiki Health / Lint / Drift Check
  -> Optional Obsidian Vault Adapter
```

The wiki layer must not be implemented before:

- Phase 4 hybrid retrieval exists
- Phase 5 evidence pack construction exists
- Phase 5 validation can detect unsupported claims
- each answer claim can be mapped back to evidence

## Phase 6A — Evidence-backed Wiki Export

### Objective

Generate Markdown knowledge artifacts from validated answers and evidence packs.

### Non-negotiable Rules

A wiki note may only be generated when:

- an evidence pack exists
- the answer has passed validation
- major claims are mapped to evidence
- unsupported claims are removed or explicitly flagged
- each generated note carries traceability metadata

### Initial Output Structure

Recommended local directory:

```text
wiki/
  concepts/
  systems/
  projects/
  decisions/
  faq/
  glossary/
  indexes/
```

This directory is local runtime output by default and must not be committed unless the content is explicitly synthetic and safe for public release.

### Wiki Note Format

Each note should be Markdown with YAML frontmatter.

```markdown
---
title: "Hybrid Retrieval Strategy"
note_type: "concept"
status: "draft"
generated_by: "tracevault"
generated_at: "2026-04-28T00:00:00Z"
source_policy: "evidence-backed"
validation_status: "validated"
confidence: 0.91
evidence_count: 5
source_documents:
  - document_id: "doc_abc"
    content_hash: "..."
source_chunks:
  - document_id: "doc_abc"
    chunk_id: "chunk_doc_abc_0001"
    source_raw_hash: "..."
---

# Hybrid Retrieval Strategy

## Summary

...

## Key Points

...

## Evidence Map

| Claim | Evidence |
|---|---|
| ... | `document_id:chunk_id` |

## Open Questions

...

## Limitations

...
```

### Required Metadata

Every wiki note must include:

- `title`
- `note_type`
- `status`
- `generated_by`
- `generated_at`
- `source_policy`
- `validation_status`
- `confidence`
- `evidence_count`
- `source_documents`
- `source_chunks`

### Supported Note Types

Initial allowed values:

```text
concept
system
project
decision
faq
glossary
index
```

### Export Modes

The first implementation should support conservative export mode:

```text
proposal-only
```

Meaning:

- the system generates a proposed wiki note
- the proposal is reviewable
- it does not automatically overwrite existing notes
- human approval is required before promotion

Future modes may include:

```text
draft
approved
archived
```

### CLI Direction

Future CLI commands may include:

```bash
python3 -m tracevault wiki export <answer-or-evidence-pack>
python3 -m tracevault wiki propose <query>
python3 -m tracevault wiki list
```

The first implementation should prefer deterministic file generation over autonomous updates.

## Phase 6B — Wiki Health / Lint / Drift Check

### Objective

Detect weak, stale, unsupported, contradictory, or poorly linked wiki artifacts.

### Required Checks

Wiki health checks should detect:

- notes without evidence
- claims without source mapping
- broken `document_id` references
- broken `chunk_id` references
- source hash drift
- stale notes after source changes
- duplicate notes
- orphan notes
- contradictory claims
- notes with unsupported confidence
- notes generated from failed validation
- notes missing required metadata

### CLI Direction

Future CLI commands may include:

```bash
python3 -m tracevault wiki lint
python3 -m tracevault wiki health
python3 -m tracevault wiki drift-check
python3 -m tracevault wiki evidence-check
```

### Health Report Format

Health checks should return both human-readable and machine-readable output.

```json
{
  "status": "warning",
  "checked_at": "2026-04-28T00:00:00Z",
  "notes_checked": 42,
  "issues": [
    {
      "severity": "important",
      "note_path": "wiki/concepts/hybrid-retrieval.md",
      "issue_type": "stale_source_hash",
      "message": "Referenced source chunk hash differs from current index.",
      "evidence_ref": {
        "document_id": "doc_abc",
        "chunk_id": "chunk_doc_abc_0001"
      }
    }
  ]
}
```

### Severity Levels

```text
critical  = must fix before publishing or using note as decision support
important = should fix before relying on note
minor     = style, completeness, or maintainability issue
```

### Critical Conditions

A wiki note must fail lint when:

- it contains no evidence references
- it references missing source chunks
- it claims validation passed but no validation record exists
- it contains major claims without evidence mapping
- source hash drift is detected and not acknowledged
- it is generated from failed or incomplete validation

## Phase 6C — Optional Obsidian Vault Adapter

### Objective

Provide optional compatibility with Obsidian-style vaults without making Obsidian a required runtime dependency.

### Decision

TraceVault will not become an Obsidian-specific application.

Instead, it may provide an optional adapter that exports evidence-backed Markdown notes into an Obsidian-compatible folder structure.

### Adapter Rules

The Obsidian adapter must:

- be optional
- require no Obsidian runtime
- write standard Markdown files
- preserve TraceVault metadata
- preserve evidence references
- avoid automatic destructive rewrites
- support proposal/draft workflow
- avoid committing private vault contents to the public repo

### Suggested Vault Structure

```text
vault/
  00-inbox/
  10-concepts/
  20-systems/
  30-projects/
  40-decisions/
  50-faq/
  90-indexes/
  _tracevault/
    manifests/
    health-reports/
    export-log.jsonl
```

### Mapping from TraceVault Wiki to Obsidian

| TraceVault note_type | Obsidian folder |
|---|---|
| concept | `10-concepts/` |
| system | `20-systems/` |
| project | `30-projects/` |
| decision | `40-decisions/` |
| faq | `50-faq/` |
| glossary | `10-concepts/glossary/` |
| index | `90-indexes/` |

### Obsidian Links

The adapter may optionally generate wiki links:

```markdown
[[Hybrid Retrieval Strategy]]
[[Evidence Pack]]
[[Source Traceability]]
```

But wiki links must not replace machine-readable evidence references.

## Design Constraints

### Public Repository Safety

The following must remain ignored or excluded from public commits unless explicitly synthetic:

```text
wiki/
vault/
.tracevault/
data/
storage/
uploads/
documents/
corpus/
indexes/
vector_store/
vector-db/
chroma/
qdrant_storage/
lancedb/
```

Synthetic examples may be committed only if they are clearly safe and contain no private source material.

### Local-first Requirement

The wiki layer must work locally by default.

No cloud service, SaaS API, hosted vector DB, or external note-taking platform may be required for baseline operation.

### Evidence-first Requirement

The system must not generate wiki notes from memory.

A wiki note must be generated from:

```text
validated_answer + evidence_pack + source metadata
```

Not from a free-form prompt alone.

### Non-destructive Write Requirement

The first implementation must be proposal-only or draft-only.

No automatic overwrite of existing wiki notes is allowed unless:

- diff is generated
- prior version is preserved
- human approval is explicit
- audit log is updated

### Audit Log Requirement

Wiki exports and updates should emit an append-only audit log.

Suggested file:

```text
.tracevault/wiki-export-log.jsonl
```

Each event should include:

```json
{
  "event_type": "wiki_export_proposed",
  "timestamp": "2026-04-28T00:00:00Z",
  "note_path": "wiki/concepts/hybrid-retrieval.md",
  "source_evidence_count": 5,
  "validation_status": "validated",
  "content_hash": "...",
  "operator": "local"
}
```

### Versioning Requirement

Wiki notes should include enough metadata to determine whether they are stale relative to current sources.

Required:

- source document IDs
- source chunk IDs
- source raw hashes
- generated timestamp
- validation status
- note content hash

## Alternatives Considered

### Alternative 1 — Use RAG answers only

Rejected.

RAG answers are useful but ephemeral. They do not create durable, reviewable organizational knowledge assets.

### Alternative 2 — Treat compiled wiki as source of truth

Rejected.

This would weaken the proof-chain model. Compiled notes are derived artifacts and may contain synthesis errors. Raw source must remain authoritative.

### Alternative 3 — Implement Obsidian-first

Rejected.

Obsidian compatibility is useful, but TraceVault must remain enterprise-oriented, model-agnostic, local-first, and not dependent on a personal knowledge management tool.

### Alternative 4 — Auto-update wiki notes without review

Rejected for initial implementation.

Automatic writes create governance risk, especially when model-generated synthesis is involved. Proposal-first export is safer and more enterprise-appropriate.

## Consequences

### Positive

- Converts validated answers into durable knowledge assets.
- Improves enterprise usability.
- Creates a clear bridge from RAG to knowledge governance.
- Supports audit, review, and versioning.
- Differentiates TraceVault from generic RAG demos.
- Enables future Obsidian-compatible workflows without vendor lock-in.

### Negative

- Adds a new layer requiring linting and health checks.
- Requires strict evidence mapping to avoid hallucinated notes.
- Requires careful handling of stale source hashes.
- Adds complexity to roadmap and testing.

### Risk Mitigations

| Risk | Mitigation |
|---|---|
| Wiki note becomes false source of truth | Raw source hierarchy and metadata warnings |
| Hallucinated note content | Generate only from validated answer + evidence pack |
| Stale notes | Wiki drift-check and source hash comparison |
| Private data leakage | Ignore wiki/vault runtime output by default |
| Destructive updates | Proposal-only export mode initially |
| Scope creep | Implement only after Phase 5 validation exists |

## Implementation Roadmap

### Phase 3B — Optional Local Model Refinement

Purpose:

- Add optional local refinement adapter.
- Keep tests deterministic with mocks.
- Fall back to rule-based refinement.
- Preserve raw source.
- Run no-new-facts safeguard after model refinement.

Must not implement wiki functionality.

### Phase 4 — Hybrid Retrieval

Purpose:

- Build vector + keyword retrieval.
- Return traceable evidence candidates.
- Preserve `document_id`, `chunk_id`, raw hash, and retrieval scores.

Must not implement wiki functionality.

### Phase 5 — Grounded Reasoning and Validation

Purpose:

- Build evidence packs.
- Generate grounded answers.
- Validate unsupported claims.
- Compute confidence and contradiction flags.
- Map claims to source evidence.

Must not implement wiki export until validation exists.

### Phase 6A — Evidence-backed Wiki Export

Purpose:

- Generate proposal-only Markdown notes from validated evidence.
- Include required metadata.
- Include claim-to-evidence map.
- Emit audit log.

### Phase 6B — Wiki Health / Lint / Drift Check

Purpose:

- Detect stale, unsupported, missing, or contradictory wiki artifacts.
- Provide machine-readable health reports.

### Phase 6C — Optional Obsidian Vault Adapter

Purpose:

- Export compatible Markdown to an Obsidian-like vault.
- Preserve TraceVault metadata and evidence mapping.
- Avoid runtime dependency on Obsidian.

## Acceptance Criteria

Phase 6A is complete when:

- evidence-backed wiki notes can be generated from validated evidence packs
- wiki notes contain required frontmatter
- notes contain claim-to-evidence mapping
- notes are proposal-only by default
- raw source remains authoritative
- audit log is emitted
- tests cover missing evidence, failed validation, and successful export

Phase 6B is complete when:

- lint detects notes without evidence
- lint detects missing source references
- lint detects stale source hashes
- lint emits human-readable and JSON reports
- tests cover critical, important, and minor issues

Phase 6C is complete when:

- Obsidian-compatible folder export works locally
- generated notes preserve TraceVault metadata
- wiki links are optional
- no Obsidian runtime dependency is required
- destructive overwrites are prevented by default

## Review Rules

A PR implementing wiki functionality must be rejected if it:

- writes wiki notes without evidence
- writes wiki notes from unvalidated answers
- treats wiki notes as source of truth
- drops `document_id` or `chunk_id`
- drops source hash metadata
- overwrites existing notes without review
- commits private wiki/vault output
- requires Obsidian for baseline operation
- introduces external APIs without approved ADR
- implements autonomous background writing without explicit approval

## Decision Summary

TraceVault will adopt a compiled knowledge wiki layer as a downstream, evidence-backed artifact system.

The wiki layer will help transform validated answers into durable enterprise knowledge assets while preserving the raw source proof chain.

This strengthens TraceVault’s positioning as an enterprise knowledge governance and grounded AI platform, not merely a RAG chatbot or personal note-taking tool.

# 08 - Roadmap

## Roadmap Philosophy

Build the smallest system that demonstrates enterprise-grade architecture maturity, then expand toward AI platform depth.

## Phase 0 - Repository and Architecture Foundation

Status: Started

Deliverables:

- repository initialized
- project charter
- architecture overview
- system design
- governance model
- RAG pipeline design
- security threat model
- evaluation strategy
- deployment architecture
- portfolio case study draft

## Phase 1 - Traceable Grounded RAG MVP

Goal: Build a working evidence-preserving RAG pipeline.

Deliverables:

- document ingestion
- chunking engine
- semantic refinement prompt
- raw/cleaned chunk storage
- embedding pipeline
- vector index
- keyword index
- hybrid retriever
- evidence pack builder
- grounded answer prompt
- answer with citations

Success criteria:

- user can query a small knowledge base
- answer cites evidence chunks
- raw source evidence is visible
- confidence and limitations are shown

## Phase 2 - Self-Verifying RAG

Goal: Add verification and quality controls.

Deliverables:

- citation checker
- unsupported claim detector
- conflict detector
- answer confidence scoring
- retrieval evaluation set
- prompt injection warning logic
- audit event logging

Success criteria:

- unsupported claims are flagged
- citation quality is measurable
- evaluation scorecard can be produced

## Phase 3 - Enterprise Knowledge Governance

Goal: Add stronger governance patterns.

Deliverables:

- sensitivity tagging
- source trust score
- retention metadata
- document versioning
- policy-aware answer controls
- admin review workflow

Success criteria:

- system can distinguish public/internal/restricted knowledge
- answer behavior changes based on sensitivity metadata

## Phase 4 - Knowledge Graph Extension

Goal: Evolve from grounded RAG to graph-assisted reasoning.

Deliverables:

- entity extraction
- relationship extraction
- node/edge schema
- graph persistence
- graph-aware retrieval
- relationship synthesis mode

Success criteria:

- system can answer relationship questions using explicit entities and edges

## Phase 5 - Hybrid Cloud / AI Platform Deployment

Goal: Demonstrate platform deployment architecture.

Deliverables:

- Docker Compose deployment
- local model deployment path
- cloud model gateway path
- PostgreSQL + pgvector deployment
- observability integration
- Kubernetes architecture blueprint
- security and secrets design

Success criteria:

- system can be deployed locally
- system has a credible path to cloud or hybrid deployment

## Portfolio Milestones

| Milestone | Portfolio Output |
|---|---|
| Architecture docs complete | GitHub repo shows architect thinking |
| MVP working | Live demo or local walkthrough video |
| Evaluation scorecard | Evidence of engineering maturity |
| Security controls | Enterprise AI governance credibility |
| Deployment blueprint | Hybrid cloud architecture credibility |
| Case study published | Resume / LinkedIn leverage |

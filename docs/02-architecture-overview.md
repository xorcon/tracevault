# 02 - Architecture Overview

## Architecture Style

TraceVault follows a modular AI platform architecture:

- ingestion-first
- evidence-preserving
- retrieval-augmented
- verification-aware
- hybrid-deployment-ready

The system is designed as a set of independently replaceable components rather than a single monolithic chatbot.

## High-Level Architecture

```text
+---------------------+
| Source Documents    |
| md, txt, pdf, notes |
+----------+----------+
           |
           v
+---------------------+
| Ingestion Service   |
| source + metadata   |
+----------+----------+
           |
           v
+---------------------+
| Chunking Engine     |
| stable chunk IDs    |
+----------+----------+
           |
           v
+-----------------------------+
| Semantic Refinement Layer   |
| clean, normalize, classify  |
+----------+------------------+
           |
           v
+-----------------------------+
| Dual Context Store          |
| raw_text                    |
| cleaned_text                |
| metadata                    |
| proof                       |
+----------+------------------+
           |
           v
+-----------------------------+
| Indexing Layer              |
| vector index + BM25 index   |
+----------+------------------+
           |
           v
+-----------------------------+
| Hybrid Retriever            |
| semantic + exact matching   |
+----------+------------------+
           |
           v
+-----------------------------+
| Evidence Builder            |
| rerank + evidence pack      |
+----------+------------------+
           |
           v
+-----------------------------+
| Grounded Reasoning Core     |
| constrained LLM reasoning   |
+----------+------------------+
           |
           v
+-----------------------------+
| Verification Layer          |
| citation + support checks   |
+----------+------------------+
           |
           v
+-----------------------------+
| Grounded Answer             |
| answer + evidence trace     |
+-----------------------------+
```

## Component Responsibilities

| Component | Responsibility |
|---|---|
| Ingestion Service | Accept files, assign document IDs, capture metadata |
| Chunking Engine | Split source content into stable, retrievable units |
| Semantic Refinement Layer | Normalize noisy text without changing meaning |
| Dual Context Store | Preserve raw evidence and retrieval-optimized text |
| Indexing Layer | Build vector and keyword indexes |
| Hybrid Retriever | Combine semantic similarity, exact match, and filters |
| Evidence Builder | Create a structured context pack for the reasoning model |
| Grounded Reasoning Core | Generate answers only from retrieved evidence |
| Verification Layer | Check support, citation quality, and unsupported claims |

## Why Dual Context Matters

Enterprise users need both reasoning quality and auditability.

- `cleaned_text` improves semantic retrieval and model reasoning.
- `raw_text` preserves original source evidence for trust and verification.

This creates a proof chain between the original knowledge and the AI-generated answer.

## Why Hybrid Retrieval Matters

Vector search is strong for conceptual similarity, but enterprise search often depends on exact terms:

- project names
- incident IDs
- policy numbers
- vendor names
- regulation references
- architecture decisions

TraceVault uses both vector retrieval and BM25 keyword retrieval to improve coverage.

## Architecture Quality Attributes

| Attribute | Design Response |
|---|---|
| Traceability | raw_text, chunk IDs, citation mapping, checksum |
| Reliability | deterministic metadata, repeatable chunking, evaluation set |
| Security | prompt injection control, source isolation, audit log |
| Portability | local model support, cloud model support, modular components |
| Maintainability | clean module boundaries and ADR documentation |
| Explainability | evidence pack and answer support mapping |

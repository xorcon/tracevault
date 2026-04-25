# 03 - System Design

## Logical Data Flow

1. User provides documents or knowledge files.
2. Ingestion service stores original source metadata.
3. Chunking engine splits text into stable chunks.
4. Semantic refinement model creates cleaned text.
5. System stores raw text, cleaned text, metadata, and proof data.
6. Embedding service embeds cleaned text.
7. Keyword index stores raw and cleaned searchable text.
8. User submits a query.
9. Query analyzer expands and classifies the query.
10. Retriever performs vector search, BM25 search, and metadata filtering.
11. Reranker merges and ranks candidate chunks.
12. Evidence builder sends a structured evidence pack to the reasoning model.
13. Reasoning model answers only from evidence.
14. Verification layer checks citation support and unsupported claims.
15. User receives answer, confidence, evidence, and gaps.

## Main Modules

```text
src/
|-- ingestion/
|-- chunking/
|-- refinement/
|-- storage/
|-- indexing/
|-- retrieval/
|-- reasoning/
|-- verification/
|-- api/
`-- shared/
```

## Suggested Technology Stack

This repository starts with architecture documentation. Implementation can use one of two stacks.

### Option A - Fast MVP Stack

| Layer | Technology |
|---|---|
| Runtime | Node.js / TypeScript |
| API | Fastify or Next.js Route Handlers |
| Database | PostgreSQL |
| Vector Store | pgvector |
| Keyword Search | PostgreSQL full-text search or MiniSearch |
| Local Model Runtime | Ollama |
| Embedding | Local embedding model or API-based embedding |
| UI | Next.js |

### Option B - AI Platform Stack

| Layer | Technology |
|---|---|
| Runtime | Python / FastAPI |
| Orchestration | LangGraph or custom pipeline |
| Database | PostgreSQL + pgvector |
| Search | OpenSearch / Elasticsearch BM25 |
| Model Gateway | LiteLLM / OpenAI-compatible gateway |
| Observability | OpenTelemetry + Langfuse-style tracing |
| Deployment | Docker Compose, then Kubernetes |

## Recommended First Implementation Path

For portfolio speed and architecture clarity:

1. Start with TypeScript + PostgreSQL + pgvector.
2. Add local model support through Ollama.
3. Use PostgreSQL full-text search for BM25-like keyword retrieval in MVP.
4. Add OpenSearch later if scale or search quality requires it.
5. Keep all interfaces abstract so components can be replaced.

## Domain Objects

### Document

A source-level object representing the uploaded or imported knowledge artifact.

### Chunk

A stable knowledge unit derived from a document.

### Evidence Pack

The structured set of retrieved chunks passed to the reasoning model.

### Answer Trace

The final mapping from answer claims to supporting chunks.

## Core Interfaces

```ts
interface DocumentRecord {
  documentId: string;
  sourceType: string;
  title: string;
  author?: string;
  createdAt?: string;
  importedAt: string;
  checksum: string;
}

interface KnowledgeChunk {
  chunkId: string;
  documentId: string;
  chunkIndex: number;
  rawText: string;
  cleanedText: string;
  metadata: Record<string, unknown>;
  proof: ProofRecord;
}

interface ProofRecord {
  rawHash: string;
  cleanedHash: string;
  refinementModel: string;
  refinementPromptVersion: string;
  createdAt: string;
}

interface EvidenceItem {
  chunkId: string;
  rawText: string;
  cleanedText: string;
  score: number;
  retrievalSource: 'vector' | 'keyword' | 'hybrid';
  metadata: Record<string, unknown>;
}
```

## Design Rule

Any module that generates, transforms, or retrieves knowledge must preserve traceability back to `document_id` and `chunk_id`.

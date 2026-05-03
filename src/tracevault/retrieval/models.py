"""Data models for hybrid retrieval.

Defines structured types for retrieval requests, responses, evidence candidates,
scores, traces, filters, and text policy.

Key concepts:
- RetrievalRequest: Input to the retrieval pipeline
- RetrievalResponse: Output of the retrieval pipeline
- CandidateEvidence: A single retrieved chunk with scores and traceability
- RetrievalResult: A ranked candidate with full audit metadata
- RetrievalScore: Score components for a single candidate
- RetrievalTrace: Full audit trail for a retrieval run
- MetadataFilter: Filter criteria for narrowing the corpus
- TextRetrievalPolicy: Controls which text fields are used for retrieval
"""

import hashlib
from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class TextRetrievalPolicy:
    """Controls which text fields are used for retrieval.

    Policies:
        RAW_ONLY: Index and search only raw_text
        CLEANED_ONLY: Index and search only cleaned_text
        DUAL_CONTEXT: Index and search both, preserve both in results
    """

    mode: Literal["RAW_ONLY", "CLEANED_ONLY", "DUAL_CONTEXT"]

    def __post_init__(self):
        if self.mode not in ("RAW_ONLY", "CLEANED_ONLY", "DUAL_CONTEXT"):
            raise ValueError(f"Invalid TextRetrievalPolicy mode: {self.mode}")

    @classmethod
    def raw_only(cls) -> "TextRetrievalPolicy":
        return cls(mode="RAW_ONLY")

    @classmethod
    def cleaned_only(cls) -> "TextRetrievalPolicy":
        return cls(mode="CLEANED_ONLY")

    @classmethod
    def dual_context(cls) -> "TextRetrievalPolicy":
        return cls(mode="DUAL_CONTEXT")

    def uses_raw(self) -> bool:
        """Return True if raw_text is used for retrieval."""
        return self.mode in ("RAW_ONLY", "DUAL_CONTEXT")

    def uses_cleaned(self) -> bool:
        """Return True if cleaned_text is used for retrieval."""
        return self.mode in ("CLEANED_ONLY", "DUAL_CONTEXT")

    def preserves_raw(self) -> bool:
        """Return True if raw_text should be preserved in results."""
        return self.mode in ("RAW_ONLY", "DUAL_CONTEXT")

    def preserves_cleaned(self) -> bool:
        """Return True if cleaned_text should be preserved in results."""
        return self.mode in ("CLEANED_ONLY", "DUAL_CONTEXT")


@dataclass(frozen=True)
class MetadataFilter:
    """Filter criteria for narrowing the retrieval corpus.

    All fields are optional. A candidate matches if it satisfies ALL specified filters.

    Attributes:
        document_id: Exact match on document_id
        source_path: Exact match on source_path
        source_type: Exact match on source_type
        key_value: Additional key/value exact-match filters
    """

    document_id: str | None = None
    source_path: str | None = None
    source_type: str | None = None
    key_value: dict[str, str] = field(default_factory=dict)

    def is_empty(self) -> bool:
        """Return True if no filters are specified."""
        return (
            self.document_id is None
            and self.source_path is None
            and self.source_type is None
            and not self.key_value
        )

    def matches(self, candidate: "CandidateEvidence") -> bool:
        """Check if a candidate satisfies all filter criteria."""
        if self.document_id is not None and candidate.document_id != self.document_id:
            return False
        if self.source_path is not None and candidate.source_path != self.source_path:
            return False
        if self.source_type is not None and candidate.source_type != self.source_type:
            return False
        for key, value in self.key_value.items():
            if candidate.metadata.get(key) != value:
                return False
        return True

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        result = {}
        if self.document_id is not None:
            result["document_id"] = self.document_id
        if self.source_path is not None:
            result["source_path"] = self.source_path
        if self.source_type is not None:
            result["source_type"] = self.source_type
        if self.key_value:
            result["key_value"] = dict(self.key_value)
        return result


@dataclass
class RetrievalScore:
    """Score components for a single retrieval candidate.

    Attributes:
        keyword_score: Normalized BM25/keyword score [0.0, 1.0]
        vector_score: Normalized vector similarity score [0.0, 1.0]
        hybrid_score: alpha * vector + (1 - alpha) * keyword
        alpha: Hybrid weight used to compute hybrid_score
    """

    keyword_score: float = 0.0
    vector_score: float = 0.0
    hybrid_score: float = 0.0
    alpha: float = 0.5

    def to_dict(self) -> dict:
        return {
            "keyword_score": self.keyword_score,
            "vector_score": self.vector_score,
            "hybrid_score": self.hybrid_score,
            "alpha": self.alpha,
        }


@dataclass
class RetrievalTrace:
    """Full audit trail for a single retrieval result.

    Attributes:
        document_id: Source document identifier
        chunk_id: Source chunk identifier
        source_path: Original file path
        raw_text_hash: SHA-256 of raw_text
        cleaned_text_hash: SHA-256 of cleaned_text (if available)
        retrieval_source: Which retrieval path(s) returned this candidate
        matched_fields: Which text fields matched the query
        applied_filters: Filters that were applied
    """

    document_id: str = ""
    chunk_id: str = ""
    source_path: str = ""
    raw_text_hash: str = ""
    cleaned_text_hash: str | None = None
    retrieval_source: str = ""
    matched_fields: list[str] = field(default_factory=list)
    applied_filters: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "document_id": self.document_id,
            "chunk_id": self.chunk_id,
            "source_path": self.source_path,
            "raw_text_hash": self.raw_text_hash,
            "cleaned_text_hash": self.cleaned_text_hash,
            "retrieval_source": self.retrieval_source,
            "matched_fields": self.matched_fields,
            "applied_filters": self.applied_filters,
        }


@dataclass
class CandidateEvidence:
    """A single retrieved chunk with scores and traceability.

    This is the internal representation before final ranking.

    Attributes:
        document_id: Source document identifier
        chunk_id: Source chunk identifier
        chunk_index: Zero-based index within document
        source_path: Original file path
        source_type: File type (txt, md, etc.)
        raw_text: Original source text (source of truth)
        cleaned_text: Normalized text for retrieval
        raw_text_hash: SHA-256 of raw_text
        cleaned_text_hash: SHA-256 of cleaned_text
        score: RetrievalScore with component scores
        trace: RetrievalTrace with audit metadata
        metadata: Additional chunk metadata from refinement
    """

    document_id: str
    chunk_id: str
    chunk_index: int
    source_path: str
    source_type: str
    raw_text: str
    cleaned_text: str
    raw_text_hash: str
    cleaned_text_hash: str | None = None
    score: RetrievalScore = field(default_factory=RetrievalScore)
    trace: RetrievalTrace = field(default_factory=RetrievalTrace)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "document_id": self.document_id,
            "chunk_id": self.chunk_id,
            "chunk_index": self.chunk_index,
            "source_path": self.source_path,
            "source_type": self.source_type,
            "raw_text": self.raw_text,
            "cleaned_text": self.cleaned_text,
            "raw_text_hash": self.raw_text_hash,
            "cleaned_text_hash": self.cleaned_text_hash,
            "score": self.score.to_dict(),
            "trace": self.trace.to_dict(),
            "metadata": self.metadata,
        }


@dataclass
class RetrievalResult:
    """A ranked retrieval candidate ready for evidence pack construction.

    Attributes:
        rank: 1-based rank position
        candidate: The underlying CandidateEvidence
        retrieval_run_id: Unique identifier for this retrieval run
        query_hash: SHA-256 of the query string
    """

    rank: int
    candidate: CandidateEvidence
    retrieval_run_id: str
    query_hash: str

    @property
    def document_id(self) -> str:
        return self.candidate.document_id

    @property
    def chunk_id(self) -> str:
        return self.candidate.chunk_id

    @property
    def source_path(self) -> str:
        return self.candidate.source_path

    @property
    def raw_text_hash(self) -> str:
        return self.candidate.raw_text_hash

    @property
    def cleaned_text_hash(self) -> str | None:
        return self.candidate.cleaned_text_hash

    def to_dict(self) -> dict:
        return {
            "rank": self.rank,
            "candidate": self.candidate.to_dict(),
            "retrieval_run_id": self.retrieval_run_id,
            "query_hash": self.query_hash,
        }


@dataclass
class RetrievalRequest:
    """Input to the retrieval pipeline.

    Attributes:
        query: Search query text
        top_k: Maximum number of results to return
        alpha: Hybrid weight (0.0 = keyword only, 1.0 = vector only)
        filters: Metadata filters to apply
        text_policy: Controls which text fields are used
        retrieval_run_id: Optional run identifier (auto-generated if not provided)
    """

    query: str
    top_k: int = 5
    alpha: float = 0.5
    filters: MetadataFilter | None = None
    text_policy: TextRetrievalPolicy | None = None
    retrieval_run_id: str | None = None

    def __post_init__(self):
        if self.text_policy is None:
            object.__setattr__(self, "text_policy", TextRetrievalPolicy.dual_context())

    def validate(self) -> list[str]:
        """Validate the request. Returns list of error messages."""
        errors = []
        if not self.query or not self.query.strip():
            errors.append("Query must not be empty")
        if self.top_k < 1:
            errors.append("top_k must be >= 1")
        if not (0.0 <= self.alpha <= 1.0):
            errors.append("alpha must be between 0.0 and 1.0")
        return errors

    @staticmethod
    def compute_query_hash(query: str) -> str:
        """Compute SHA-256 hash of the query string."""
        return hashlib.sha256(query.encode("utf-8")).hexdigest()


@dataclass
class RetrievalResponse:
    """Output of the retrieval pipeline.

    Attributes:
        retrieval_run_id: Unique identifier for this retrieval run
        query: Original query text
        query_hash: SHA-256 of the query
        results: Ranked list of RetrievalResult
        total_candidates: Number of candidates before top-k selection
        alpha: Hybrid weight used
        text_policy: Text policy used
        applied_filters: String representation of applied filters
    """

    retrieval_run_id: str
    query: str
    query_hash: str
    results: list[RetrievalResult]
    total_candidates: int
    alpha: float
    text_policy: TextRetrievalPolicy
    applied_filters: str = ""

    def to_dict(self) -> dict:
        return {
            "retrieval_run_id": self.retrieval_run_id,
            "query": self.query,
            "query_hash": self.query_hash,
            "results": [r.to_dict() for r in self.results],
            "total_candidates": self.total_candidates,
            "alpha": self.alpha,
            "text_policy": self.text_policy.mode,
            "applied_filters": self.applied_filters,
        }

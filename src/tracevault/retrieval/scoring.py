"""Hybrid score merging and normalization.

Combines keyword and vector scores into a hybrid score with deterministic
tie-breaking.
"""

from tracevault.retrieval.models import (
    CandidateEvidence,
    RetrievalScore,
    RetrievalTrace,
)


def normalize_scores(
    candidates: list[CandidateEvidence],
    score_field: str = "keyword_score",
) -> list[CandidateEvidence]:
    """Normalize scores to [0.0, 1.0] range using min-max normalization."""
    if not candidates:
        return []

    scores = [getattr(c.score, score_field) for c in candidates]
    min_score = min(scores)
    max_score = max(scores)

    if max_score == min_score:
        return list(candidates)

    range_score = max_score - min_score

    result = []
    for c in candidates:
        new_score = RetrievalScore(
            keyword_score=(c.score.keyword_score - min_score) / range_score
            if score_field == "keyword_score"
            else c.score.keyword_score,
            vector_score=(c.score.vector_score - min_score) / range_score
            if score_field == "vector_score"
            else c.score.vector_score,
            hybrid_score=c.score.hybrid_score,
            alpha=c.score.alpha,
        )
        new_candidate = CandidateEvidence(
            document_id=c.document_id,
            chunk_id=c.chunk_id,
            chunk_index=c.chunk_index,
            source_path=c.source_path,
            source_type=c.source_type,
            raw_text=c.raw_text,
            cleaned_text=c.cleaned_text,
            raw_text_hash=c.raw_text_hash,
            cleaned_text_hash=c.cleaned_text_hash,
            score=new_score,
            trace=c.trace,
            metadata=c.metadata,
        )
        result.append(new_candidate)
    return result


class HybridScoreMerger:
    """Merges keyword and vector retrieval results into hybrid scores.

    Formula: hybrid_score = alpha * vector_score + (1 - alpha) * keyword_score

    Tie-breaking order:
        1. hybrid_score descending
        2. keyword_score descending
        3. vector_score descending
        4. document_id ascending
        5. chunk_id ascending
    """

    def __init__(self, alpha: float = 0.5):
        if not (0.0 <= alpha <= 1.0):
            raise ValueError(f"alpha must be between 0.0 and 1.0, got {alpha}")
        self.alpha = alpha

    def merge(
        self,
        keyword_results: list[CandidateEvidence],
        vector_results: list[CandidateEvidence],
    ) -> list[CandidateEvidence]:
        """Merge keyword and vector results with hybrid scoring.

        Deduplicates by (document_id, chunk_id). If a candidate appears in
        both result sets, combines the scores.
        """
        keyword_map: dict[tuple[str, str], CandidateEvidence] = {}
        for c in keyword_results:
            key = (c.document_id, c.chunk_id)
            keyword_map[key] = c

        vector_map: dict[tuple[str, str], CandidateEvidence] = {}
        for c in vector_results:
            key = (c.document_id, c.chunk_id)
            vector_map[key] = c

        all_keys = set(keyword_map.keys()) | set(vector_map.keys())

        merged = []
        for key in all_keys:
            kw = keyword_map.get(key)
            vec = vector_map.get(key)

            keyword_score = kw.score.keyword_score if kw else 0.0
            vector_score = vec.score.vector_score if vec else 0.0

            hybrid_score = self.alpha * vector_score + (1 - self.alpha) * keyword_score

            base = kw if kw else vec

            if kw and vec:
                retrieval_source = "hybrid"
                matched_fields = list(set(kw.trace.matched_fields) | set(vec.trace.matched_fields))
            elif kw:
                retrieval_source = "keyword"
                matched_fields = list(kw.trace.matched_fields)
            else:
                retrieval_source = "vector"
                matched_fields = list(vec.trace.matched_fields)

            result = CandidateEvidence(
                document_id=base.document_id,
                chunk_id=base.chunk_id,
                chunk_index=base.chunk_index,
                source_path=base.source_path,
                source_type=base.source_type,
                raw_text=base.raw_text,
                cleaned_text=base.cleaned_text,
                raw_text_hash=base.raw_text_hash,
                cleaned_text_hash=base.cleaned_text_hash,
                score=RetrievalScore(
                    keyword_score=keyword_score,
                    vector_score=vector_score,
                    hybrid_score=hybrid_score,
                    alpha=self.alpha,
                ),
                trace=RetrievalTrace(
                    document_id=base.document_id,
                    chunk_id=base.chunk_id,
                    source_path=base.source_path,
                    raw_text_hash=base.raw_text_hash,
                    cleaned_text_hash=base.cleaned_text_hash,
                    retrieval_source=retrieval_source,
                    matched_fields=matched_fields,
                ),
                metadata=base.metadata,
            )
            merged.append(result)

        # Deterministic sort
        merged.sort(
            key=lambda c: (
                -c.score.hybrid_score,
                -c.score.keyword_score,
                -c.score.vector_score,
                c.document_id,
                c.chunk_id,
            )
        )

        return merged

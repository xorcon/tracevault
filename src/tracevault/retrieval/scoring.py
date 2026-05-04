"""Hybrid score merging.

Combines keyword and vector scores into hybrid scores with deterministic
tie-breaking.
"""

from tracevault.retrieval.models import (
    CandidateEvidence,
    RetrievalScore,
    ScoringCandidate,
)


def _derive_source_retrievers(s: ScoringCandidate) -> list[str]:
    """Derive source retriever names from a ScoringCandidate.

    Uses source_retrievers if present, otherwise falls back to
    [retrieval_source].
    """
    if s.source_retrievers:
        return s.source_retrievers
    return [s.retrieval_source] if s.retrieval_source else []


def _deduplicate_ordered(items: list[str]) -> list[str]:
    """Deduplicate strings while preserving order."""
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
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
        keyword_results: list[ScoringCandidate],
        vector_results: list[ScoringCandidate],
    ) -> list[ScoringCandidate]:
        """Merge keyword and vector results with hybrid scoring.

        Deduplicates by (document_id, chunk_id). If a candidate appears in
        both result sets, combines the scores.
        """
        keyword_map: dict[tuple[str, str], ScoringCandidate] = {}
        for s in keyword_results:
            key = (s.candidate.document_id, s.candidate.chunk_id)
            keyword_map[key] = s

        vector_map: dict[tuple[str, str], ScoringCandidate] = {}
        for s in vector_results:
            key = (s.candidate.document_id, s.candidate.chunk_id)
            vector_map[key] = s

        all_keys = set(keyword_map.keys()) | set(vector_map.keys())

        merged: list[ScoringCandidate] = []
        for key in all_keys:
            kw = keyword_map.get(key)
            vec = vector_map.get(key)

            keyword_score = kw.score.keyword_score if kw else 0.0
            vector_score = vec.score.vector_score if vec else 0.0

            hybrid_score = self.alpha * vector_score + (1 - self.alpha) * keyword_score

            base = kw.candidate if kw else vec.candidate

            # Determine retrieval source and matched fields from ScoringCandidate
            if kw and vec:
                retrieval_source = "hybrid"
                matched_fields = sorted(set(kw.matched_fields) | set(vec.matched_fields))
                source_retrievers = _deduplicate_ordered(
                    _derive_source_retrievers(kw) + _derive_source_retrievers(vec)
                )
                score_policy = "hybrid"
            elif kw:
                retrieval_source = kw.retrieval_source
                matched_fields = sorted(kw.matched_fields)
                source_retrievers = _derive_source_retrievers(kw)
                score_policy = kw.score.score_policy
            else:
                retrieval_source = vec.retrieval_source
                matched_fields = sorted(vec.matched_fields)
                source_retrievers = _derive_source_retrievers(vec)
                score_policy = vec.score.score_policy

            merged.append(
                ScoringCandidate(
                    candidate=CandidateEvidence(
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
                            score_policy=score_policy,
                        ),
                        metadata=dict(base.metadata),
                    ),
                    score=RetrievalScore(
                        keyword_score=keyword_score,
                        vector_score=vector_score,
                        hybrid_score=hybrid_score,
                        alpha=self.alpha,
                        score_policy=score_policy,
                    ),
                    matched_fields=matched_fields,
                    retrieval_source=retrieval_source,
                    source_retrievers=source_retrievers,
                )
            )

        # Deterministic sort
        merged.sort(
            key=lambda s: (
                -s.score.hybrid_score,
                -s.score.keyword_score,
                -s.score.vector_score,
                s.candidate.document_id,
                s.candidate.chunk_id,
            )
        )

        return merged

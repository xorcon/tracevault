"""Tests for evidence pack policy defaults."""

from tracevault.evidence.policy import (
    default_context_policy,
    default_selection_policy,
)


class TestDefaultSelectionPolicy:
    def test_order_by_is_retrieval_rank(self):
        policy = default_selection_policy()
        assert policy.order_by == "retrieval_rank"

    def test_deduplicate_by_is_document_chunk(self):
        policy = default_selection_policy()
        assert policy.deduplicate_by == "document_chunk"


class TestDefaultContextPolicy:
    def test_include_raw_text_is_true(self):
        policy = default_context_policy()
        assert policy.include_raw_text is True

    def test_include_cleaned_text_is_true(self):
        policy = default_context_policy()
        assert policy.include_cleaned_text is True


class TestPolicyInstancesAreIndependent:
    def test_selection_policy_new_instance_each_call(self):
        p1 = default_selection_policy()
        p2 = default_selection_policy()
        assert p1 is not p2

    def test_context_policy_new_instance_each_call(self):
        p1 = default_context_policy()
        p2 = default_context_policy()
        assert p1 is not p2

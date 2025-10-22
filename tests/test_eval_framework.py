"""Tests for evaluation framework."""

import pytest
from evaluation import (
    QueryType,
    EvaluationMetrics,
    EvaluationThresholds,
    EvaluationSuite,
    TestCase
)


def test_evaluation_metrics_validation():
    """Test that evaluation metrics are properly validated."""
    metrics = EvaluationMetrics(
        retrieval_precision=0.85,
        retrieval_recall=0.80,
        context_relevance=0.90,
        answer_correctness=0.88,
        answer_completeness=0.85,
        hallucination_score=0.95,
        latency_ms=2500,
        retrieval_latency_ms=1500,
        generation_latency_ms=1000,
        query_type=QueryType.FACTUAL_LOOKUP
    )

    assert metrics.retrieval_precision == 0.85
    assert metrics.query_type == QueryType.FACTUAL_LOOKUP


def test_evaluation_thresholds():
    """Test evaluation thresholds."""
    thresholds = EvaluationThresholds(
        min_context_relevance=0.7,
        min_answer_correctness=0.8,
        min_hallucination_score=0.9,
        max_latency_ms=5000
    )

    # Passing metrics
    passing_metrics = EvaluationMetrics(
        retrieval_precision=0.9,
        retrieval_recall=0.85,
        context_relevance=0.8,
        answer_correctness=0.85,
        answer_completeness=0.8,
        hallucination_score=0.95,
        latency_ms=3000,
        retrieval_latency_ms=1800,
        generation_latency_ms=1200,
        query_type=QueryType.FACTUAL_LOOKUP
    )

    assert passing_metrics.is_passing(thresholds) is True

    # Failing metrics (low hallucination score)
    failing_metrics = EvaluationMetrics(
        retrieval_precision=0.9,
        retrieval_recall=0.85,
        context_relevance=0.8,
        answer_correctness=0.85,
        answer_completeness=0.8,
        hallucination_score=0.5,  # Too low
        latency_ms=3000,
        retrieval_latency_ms=1800,
        generation_latency_ms=1200,
        query_type=QueryType.FACTUAL_LOOKUP
    )

    assert failing_metrics.is_passing(thresholds) is False


def test_minimal_test_suite():
    """Test that minimal test suite is properly defined."""
    test_suite = EvaluationSuite.get_minimal_test_suite()

    assert len(test_suite) >= 5
    assert all(isinstance(tc, TestCase) for tc in test_suite)

    # Check query types are covered
    query_types = set(tc.query_type for tc in test_suite)
    assert QueryType.FACTUAL_LOOKUP in query_types
    assert QueryType.SUMMARIZATION in query_types
    assert QueryType.SEMANTIC_LINKAGE in query_types


def test_failure_scenarios():
    """Test that failure scenarios are defined."""
    scenarios = EvaluationSuite.get_failure_scenarios()

    assert len(scenarios) > 0
    assert all("scenario" in s for s in scenarios)
    assert all("expected_behavior" in s for s in scenarios)
    assert all("should_hallucinate" in s for s in scenarios)

    # All scenarios should not hallucinate
    assert all(s["should_hallucinate"] is False for s in scenarios)

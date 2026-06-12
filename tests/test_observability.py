"""Tests for the observability tracker."""

import os
import unittest

from tools.observability.tracker import (
    Span,
    _estimate_cost,
    get_metrics,
    get_summary,
    trace,
)


class TestCostEstimation(unittest.TestCase):

    def test_known_model_cost(self):
        cost = _estimate_cost("gpt-5.4-mini", input_tokens=1_000_000, output_tokens=0)
        self.assertAlmostEqual(cost, 0.75, places=2)

    def test_output_token_cost(self):
        cost = _estimate_cost("gpt-5.4-mini", input_tokens=0, output_tokens=1_000_000)
        self.assertAlmostEqual(cost, 4.50, places=2)

    def test_unknown_model_falls_back(self):
        cost = _estimate_cost("unknown-model", input_tokens=1_000_000, output_tokens=0)
        self.assertGreater(cost, 0)

    def test_zero_tokens(self):
        cost = _estimate_cost("gpt-5.4-mini", input_tokens=0, output_tokens=0)
        self.assertEqual(cost, 0.0)


class TestTraceContextManager(unittest.TestCase):

    def test_trace_records_ok_status(self):
        with trace(module="test-module", model="gpt-5.4-mini") as span:
            span.input_tokens = 100
            span.output_tokens = 50
        self.assertEqual(span.status, "ok")
        self.assertGreaterEqual(span.latency_ms, 0)
        self.assertGreater(span.cost_usd, 0)

    def test_trace_records_error_status(self):
        with self.assertRaises(ValueError):
            with trace(module="test-module", model="gpt-5.4-mini") as span:
                raise ValueError("test error")
        self.assertEqual(span.status, "error")
        self.assertIn("ValueError", span.error)

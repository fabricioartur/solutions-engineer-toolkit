"""Tests for the evals module (offline — no API calls)."""

import unittest

from tools.evals.evaluator import _score_to_grade


class TestScoreToGrade(unittest.TestCase):

    def test_grade_a(self):
        self.assertEqual(_score_to_grade(9.5), "A")
        self.assertEqual(_score_to_grade(10.0), "A")

    def test_grade_b(self):
        self.assertEqual(_score_to_grade(7.0), "B")
        self.assertEqual(_score_to_grade(8.9), "B")

    def test_grade_c(self):
        self.assertEqual(_score_to_grade(5.0), "C")
        self.assertEqual(_score_to_grade(6.9), "C")

    def test_grade_d(self):
        self.assertEqual(_score_to_grade(3.0), "D")
        self.assertEqual(_score_to_grade(4.9), "D")

    def test_grade_f(self):
        self.assertEqual(_score_to_grade(0.0), "F")
        self.assertEqual(_score_to_grade(2.9), "F")

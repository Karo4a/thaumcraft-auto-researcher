import logging
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)

from utils import log_context
from utils.log_context import ContextFilter, currentContext


class LogContextTest(unittest.TestCase):
    def setUp(self) -> None:
        log_context.setResearch(0)
        log_context.setSolve(0)

    def test_default_context_is_dash(self):
        self.assertEqual(currentContext(), "-")

    def test_sets_research_and_solve(self):
        log_context.setResearch(2)
        log_context.setSolve(3)
        self.assertEqual(currentContext(), "R2 S3")

    def test_increment_and_reset_solve(self):
        log_context.setResearch(1)
        log_context.incrementSolve()
        log_context.incrementSolve()
        self.assertEqual(currentContext(), "R1 S2")
        log_context.resetSolve()
        self.assertEqual(currentContext(), "R1 S0")

    def test_increment_research(self):
        log_context.setResearch(1)
        log_context.incrementResearch()
        self.assertEqual(currentContext(), "R2 S0")

    def test_filter_stamps_record(self):
        log_context.setResearch(4)
        log_context.setSolve(5)
        record = logging.LogRecord("x", logging.INFO, __file__, 1, "m", (), None)
        ok = ContextFilter().filter(record)
        self.assertTrue(ok)
        self.assertEqual(record.solutionContext, "R4 S5")


if __name__ == "__main__":
    unittest.main()

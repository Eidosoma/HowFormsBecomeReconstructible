"""Lightweight harness tests; these do not test the biological equations."""

import io
import unittest

from run_pilot import THRESHOLDS, Tee, compare_thresholds


class ReportingTests(unittest.TestCase):
    def fixture(self, scale=1):
        return "\n".join(
            f"Result NR=0 center-{center}, surround={count}: final GJ_diff={value * scale:.4g}"
            for (center, count), value in THRESHOLDS.items())

    def test_reference_passes(self):
        rows, passed = compare_thresholds(self.fixture(), .02)
        self.assertTrue(passed)
        self.assertEqual(len(rows), 8)

    def test_large_discrepancy_fails(self):
        self.assertFalse(compare_thresholds(self.fixture(1.1), .02)[1])

    def test_missing_or_duplicate_result_fails(self):
        lines = self.fixture().splitlines()
        self.assertFalse(compare_thresholds("\n".join(lines[:-1]), .02)[1])
        self.assertFalse(compare_thresholds("\n".join(lines[:-1] + lines[:1]), .02)[1])

    def test_failed_search_fails(self):
        self.assertFalse(compare_thresholds(self.fixture() + "\nBAD_SEARCH", .02)[1])

    def test_tee_preserves_output(self):
        target = io.StringIO()
        tee = Tee(target)
        tee.write("hello\n")
        self.assertEqual(target.getvalue(), tee.getvalue())


if __name__ == "__main__":
    unittest.main()

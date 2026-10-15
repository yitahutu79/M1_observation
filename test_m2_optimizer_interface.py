import tempfile
import unittest
from pathlib import Path

from m2_optimizer_interface import OptimizationRequest, SUPPORTED_MODES, freeze_champion, optimize_schedule


class UnifiedOptimizerInterfaceTests(unittest.TestCase):
    def test_supported_modes_are_stable(self):
        self.assertEqual(SUPPORTED_MODES, ("fast_local", "milp_rebuild", "hybrid"))

    def test_rejects_unknown_mode_before_running(self):
        with tempfile.TemporaryDirectory() as directory:
            request = OptimizationRequest(Path("missing.csv"), "unknown", 300, 1, Path(directory))
            with self.assertRaisesRegex(ValueError, "unsupported mode"):
                optimize_schedule(request)

    def test_budget_must_leave_referee_reserve(self):
        with tempfile.TemporaryDirectory() as directory:
            request = OptimizationRequest(Path("missing.csv"), "fast_local", 8, 1, Path(directory))
            with self.assertRaisesRegex(ValueError, "Referee reserve"):
                optimize_schedule(request)


if __name__ == "__main__":
    unittest.main()

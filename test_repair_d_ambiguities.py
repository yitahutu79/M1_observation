import unittest
import numpy as np
from repair_d_ambiguities_aug2026 import positive_grid_runs

class PositiveGridRunsTests(unittest.TestCase):
    def test_empty_grid_has_no_intervals(self):
        self.assertEqual(positive_grid_runs([-2.0, -1.0, -0.1]), [])

    def test_separate_sunlit_runs_are_not_bridged(self):
        self.assertEqual(positive_grid_runs([-1.0, 0.0, 0.4, -0.2, 1.0, -1.0]), [(1, 2), (4, 4)])

    def test_entire_gap_sunlit_is_one_run(self):
        self.assertEqual(positive_grid_runs([0.1, 0.2, 0.3]), [(0, 2)])

if __name__ == '__main__':
    unittest.main()

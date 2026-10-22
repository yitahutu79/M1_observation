import math
import csv
import io
import unittest
from unittest.mock import patch

import numpy as np

import illumination_filter_aug2026 as illumination


class IlluminationFilterTests(unittest.TestCase):
    def test_single_time_xyz_is_not_mistaken_for_three_times(self):
        xyz = np.array([1.0, 2.0, 3.0])
        self.assertEqual(illumination._rows_xyz(xyz, 1).shape, (1, 3))

    def test_vectorized_xyz_layouts_agree(self):
        rows = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
        np.testing.assert_array_equal(illumination._rows_xyz(rows, 2), rows)
        np.testing.assert_array_equal(illumination._rows_xyz(rows.T, 2), rows)

    def test_adaptive_classifier_finds_internal_umbra_between_lit_endpoints(self):
        # A reproducible synthetic clearance curve with two roots in one 60 s
        # discovery interval: lit at both ends, eclipsed in the middle.
        clearance = lambda t: 10.0 * math.cos(2.0 * math.pi * t / 60.0)
        with patch.object(
            illumination, "scalar_clearance",
            side_effect=lambda _sat, _earth, _sun, _ts, t: clearance(t),
        ):
            ambiguous = [0]
            pieces = illumination.classify_interval(
                None, None, None, None, 0.0, clearance(0.0),
                60.0, clearance(60.0), ambiguous,
            )
        self.assertEqual(len(pieces), 2)
        self.assertLess(pieces[0][1], pieces[1][0])
        self.assertAlmostEqual(pieces[0][1], 15.0, delta=0.5)
        self.assertAlmostEqual(pieces[1][0], 45.0, delta=0.5)

    def test_clearance_bound_forces_detection_of_substep_umbra(self):
        # A narrow, piecewise-linear negative pocket with slope below the
        # configured 30 km/s bound. The initial endpoints and midpoint are lit.
        def clearance(t):
            distance = abs(t - 0.06)
            return -0.05 + 20.0 * distance if distance < 0.005 else 0.05
        with patch.object(
            illumination, "scalar_clearance",
            side_effect=lambda _sat, _earth, _sun, _ts, t: clearance(t),
        ):
            ambiguous = [0]
            pieces = illumination.classify_interval(
                None, None, None, None, 0.0, clearance(0.0),
                0.25, clearance(0.25), ambiguous,
            )
        self.assertGreaterEqual(len(pieces), 2)
        self.assertTrue(any(left < 0.06 < right for left, right in [(p[1], pieces[i + 1][0]) for i,p in enumerate(pieces[:-1])]))
        self.assertLessEqual(ambiguous[0], 2)

    def test_shape_mismatch_is_rejected(self):
        with self.assertRaises(ValueError):
            illumination._rows_xyz(np.zeros((4, 2)), 2)

    def test_d_output_preserves_source_c_row_and_boundaries(self):
        source = {
            "target_id": "12345", "target_index": 0, "station_id": 1,
            "start_s": 0.0, "end_s": 60.0, "duration_s": 60.0,
            "source_C_line": 2, "c_start_s": 0.0, "c_end_s": 60.0,
        }
        fields = list(source) + ["meets_120s", "illumination_status", "illumination_model", "illumination_boundary_method"]
        stream = io.StringIO()
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        counts = {"output_rows": 0, "source_windows_no_sunlit_segment": 0, "ambiguous_leaves": 0}
        with patch.object(illumination, "target_evaluator", return_value=np.array([10000.0, 10000.0])):
            illumination.process_target([source], None, None, None, None, writer, counts)
        row = next(csv.DictReader(io.StringIO(stream.getvalue())), None)
        self.assertIsNotNone(row)
        self.assertEqual(row["source_C_line"], "2")
        self.assertEqual(float(row["c_start_s"]), 0.0)
        self.assertEqual(float(row["c_end_s"]), 60.0)


if __name__ == "__main__":
    unittest.main()

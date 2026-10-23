import unittest
import json

from web_app import check_uploads, validate_stations, validate_tle


class UploadValidationTests(unittest.TestCase):
    def test_official_inputs_validate_and_match_pinned_cache(self):
        from pathlib import Path
        root = Path(__file__).resolve().parent
        tle = (root / "data/轨道.txt").read_bytes()
        stations = (root / "data/站址.txt").read_bytes()
        result = check_uploads(tle, stations)
        self.assertTrue(result["official_input_match"])
        self.assertEqual(result["tle"]["unique_satellites"], 10000)
        self.assertEqual(result["station"]["stations"], 10)

    def test_tle_must_be_complete_three_line_records(self):
        with self.assertRaisesRegex(ValueError, "三行|3行"):
            validate_tle(b"0 example\n1 00001\n")

    def test_station_file_requires_parseable_station(self):
        with self.assertRaisesRegex(ValueError, "未找到站点"):
            validate_stations("这里没有坐标".encode())

    def test_valid_but_changed_input_does_not_match_frozen_cache(self):
        from pathlib import Path
        root = Path(__file__).resolve().parent
        tle = (root / "data/轨道.txt").read_bytes()
        stations = (root / "data/站址.txt").read_bytes() + b"\n# local edit\n"
        result = check_uploads(tle, stations)
        self.assertTrue(result["valid"])
        self.assertFalse(result["official_input_match"])
        self.assertFalse(result["matches"]["stations"])

    def test_schedule_csv_counts_repeated_visits_by_target(self):
        from satellite_status import _load_schedule_counts
        counts, digest = _load_schedule_counts(
            b"target_id,station_id\n50574,1\n50574,2\n"
        )
        self.assertEqual(counts["50574"], 2)
        self.assertEqual(len(digest), 64)

    def test_analysis_summarizes_frozen_target_statuses(self):
        from pathlib import Path
        from satellite_status import build_satellite_status
        root = Path(__file__).resolve().parent
        result = build_satellite_status(
            root / "data/轨道.txt",
            root / "m1_validation/formal_20260801_candidate/A_orbit/target_status.csv",
            root / "m1_validation/formal_20260801_candidate/D_illumination_refined_v2",
            priority_path=root / "data/优先级.zip",
        )
        summary = result["summary"]
        self.assertEqual(summary["target_count"], 10000)
        self.assertEqual(summary["d_window_count"], 622882)
        self.assertEqual(summary["targets_with_propagation_anomaly"], 1)
        self.assertEqual(sum(summary["orbit_type_counts"].values()), 10000)
        self.assertFalse(summary["schedule_imported"])
        self.assertTrue(all(row["schedule_status"] == "未导入排程" for row in result["records"]))
        serialized = json.dumps(result, ensure_ascii=False)
        self.assertIn('"target_count": 10000', serialized)
        with_schedule = build_satellite_status(
            root / "data/轨道.txt",
            root / "m1_validation/formal_20260801_candidate/A_orbit/target_status.csv",
            root / "m1_validation/formal_20260801_candidate/D_illumination_refined_v2",
            schedule_csv=b"target_id,station_id\n50574,1\n50574,2\n",
            priority_path=root / "data/优先级.zip",
        )
        row = next(item for item in with_schedule["records"] if item["target_id"] == "50574")
        self.assertEqual(row["scheduled_visits"], 2)
        self.assertEqual(row["schedule_status"], "已排程（2次）")


if __name__ == "__main__":
    unittest.main()

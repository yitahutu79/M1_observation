import csv
import json
import tempfile
import unittest
import zipfile
from collections import defaultdict
from pathlib import Path

from m2_scheduler import (Rules, canonical_target_id, insert_observation, observation_score,
                          write_schedule)
from m2_referee import independent_score, referee


class M2ConfirmedRuleTests(unittest.TestCase):
    def setUp(self):
        self.rules = Rules(
            120.0, 240.0, 30.0, 172800.0,
            {"high": 5.0, "medium": 3.0, "low": 2.0},
            "linear_60_to_100", "cumulative_after_48h", 1e-6,
        )

    def test_linear_score_formula(self):
        self.assertAlmostEqual(observation_score("high", 120, self.rules), 3.0)
        self.assertAlmostEqual(observation_score("high", 180, self.rules), 4.0)
        self.assertAlmostEqual(observation_score("high", 240, self.rules), 5.0)

    def test_identifier_normalization(self):
        self.assertEqual(canonical_target_id("08882"), "8882")
        self.assertEqual(canonical_target_id("A0157"), "100157")

    def test_scheduler_generates_48h_repeat_across_stations(self):
        windows = [
            {"source_line": 2, "target_id": "00001", "canonical_target_id": "1", "target_index": 0,
             "station_id": 1, "window_start_s": 0.0, "window_end_s": 500.0, "priority": "high"},
            {"source_line": 3, "target_id": "00001", "canonical_target_id": "1", "target_index": 0,
             "station_id": 2, "window_start_s": 173040.0, "window_end_s": 173500.0, "priority": "high"},
        ]
        calendars = {station: [] for station in range(1, 11)}
        targets = defaultdict(list)
        first = insert_observation(windows, calendars, targets, self.rules, "test", "earliest")
        second = insert_observation(windows, calendars, targets, self.rules, "test", "earliest")
        self.assertEqual(first["station_id"], 1)
        self.assertEqual(second["station_id"], 2)
        self.assertGreaterEqual(second["start_s"] - first["end_s"], 172800.0)

    def fixture(self, root: Path):
        cache = root / "formal_20261001_v2"
        (cache / "C_optical").mkdir(parents=True)
        (cache / "A_orbit").mkdir()
        (cache / "C_optical/manifest.json").write_text(json.dumps({
            "layer": "C_optical", "window_count": 1655169,
            "windows_sha256": "f05e35c97e4ef37321418efd8c51fd7796f03a316f9dbeb9c80ee0c93332f2df",
        }), encoding="utf-8")
        c_fields = ["target_id", "target_index", "station_id", "start_s", "end_s", "duration_s", "priority"]
        with (cache / "C_optical/windows.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=c_fields); writer.writeheader(); writer.writerows([
                {"target_id":"00001","target_index":0,"station_id":1,"start_s":0,"end_s":500,"duration_s":500,"priority":"high"},
                {"target_id":"00001","target_index":0,"station_id":2,"start_s":172900,"end_s":173500,"duration_s":600,"priority":"high"},
                {"target_id":"00002","target_index":1,"station_id":1,"start_s":100,"end_s":700,"duration_s":600,"priority":"medium"},
            ])
        with (cache / "A_orbit/target_status.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["target_id", "target_index", "status"])
            writer.writeheader(); writer.writerows([
                {"target_id":"00001","target_index":0,"status":"has_windows"},
                {"target_id":"00002","target_index":1,"status":"has_windows"},
            ])
        priority = root / "priority.zip"
        with zipfile.ZipFile(priority, "w") as archive:
            archive.writestr("高优先级.txt", "1")
            archive.writestr("中优先级.txt", "2")
            archive.writestr("低优先级.txt", "3")
        config = root / "config.json"
        config.write_text(json.dumps({
            "minimum_observation_s":120,"maximum_observation_s":240,
            "different_target_switch_s":30,"target_revisit_cooldown_s":172800,
            "priority_weights":{"high":5,"medium":3,"low":2},
            "duration_score_rule":"linear_60_to_100",
            "repeat_observation_rule":"cumulative_after_48h","numeric_tolerance_s":1e-6,
        }), encoding="utf-8")
        return cache, priority, config

    def row(self, **overrides):
        row = {
            "task_id":"a", "algorithm":"test", "target_id":"00001", "canonical_target_id":"1",
            "target_index":0, "station_id":1, "start_s":0, "end_s":120, "duration_s":120,
            "priority":"high", "score":3.0, "visit_number":1, "source_c_line":2,
            "source_window_start_s":0, "source_window_end_s":500,
        }
        row.update(overrides)
        return row

    def test_referee_accepts_exact_48h_boundary_and_accumulates_repeat_score(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); cache, priority, config = self.fixture(root)
            rows = [self.row(), self.row(task_id="b", station_id=2, start_s=172920, end_s=173040,
                    visit_number=2, source_c_line=3, source_window_start_s=172900, source_window_end_s=173500)]
            path = root / "schedule.csv"; write_schedule(path, rows)
            result = referee(path, cache, priority, config, 2, root / "violations.csv")
            self.assertTrue(result["legal"])
            self.assertEqual(result["unique_covered_targets"], 1)
            self.assertEqual(result["repeated_observation_count"], 1)
            self.assertAlmostEqual(result["total_score"], 6.0)
            self.assertAlmostEqual(result["minimum_revisit_gap_s"], 172800.0)

    def test_referee_rejects_cross_station_repeat_before_48h(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); cache, priority, config = self.fixture(root)
            rows = [self.row(), self.row(task_id="b", station_id=2, start_s=172919, end_s=173039,
                    visit_number=2, source_c_line=3, source_window_start_s=172900, source_window_end_s=173500)]
            path = root / "schedule.csv"; write_schedule(path, rows)
            result = referee(path, cache, priority, config, 2)
            self.assertIn("target_cooldown", result["violation_categories"])

    def test_referee_keeps_window_duration_station_and_switch_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); cache, priority, config = self.fixture(root)
            cases = {
                "duration_bounds": [self.row(end_s=100, duration_s=100, score=0)],
                "window_containment": [self.row(start_s=450, end_s=570)],
                "station_overlap": [self.row(), self.row(task_id="b", target_id="00002", canonical_target_id="2",
                    target_index=1, priority="medium", score=1.8, start_s=100, end_s=220,
                    station_id=1, source_c_line=4, source_window_start_s=100, source_window_end_s=700)],
                "switch_gap": [self.row(), self.row(task_id="b", target_id="00002", canonical_target_id="2",
                    target_index=1, priority="medium", score=1.8, start_s=130, end_s=250,
                    station_id=1, source_c_line=4, source_window_start_s=100, source_window_end_s=700)],
            }
            path = root / "schedule.csv"
            for category, rows in cases.items():
                write_schedule(path, rows)
                result = referee(path, cache, priority, config, 2)
                self.assertIn(category, result["violation_categories"])

    def test_referee_scoring_is_independent(self):
        config = {"minimum_observation_s":120,"maximum_observation_s":240,"numeric_tolerance_s":1e-6,
                  "priority_weights":{"high":5}}
        self.assertAlmostEqual(independent_score("high", 180, config), 4.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

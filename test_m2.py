import csv
import json
import tempfile
import unittest
import zipfile
import hashlib
from collections import defaultdict
from pathlib import Path
from unittest.mock import patch

from m2_scheduler import (Rules, canonical_target_id, insert_observation, observation_score,
                          validate_cache_identity, write_schedule)
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
        base = root / "formal_20260801_candidate"
        cache = base / "D_illumination_refined_v2"
        (base / "C_optical").mkdir(parents=True)
        (base / "A_orbit").mkdir()
        cache.mkdir(parents=True)
        priority = root / "priority.zip"
        with zipfile.ZipFile(priority, "w") as archive:
            archive.writestr("高优先级.txt", "1")
            archive.writestr("中优先级.txt", "2")
            archive.writestr("低优先级.txt", "3")
        c_fields = ["target_id", "target_index", "station_id", "start_s", "end_s", "duration_s", "priority"]
        c_path = base / "C_optical/windows.csv"
        with c_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=c_fields); writer.writeheader(); writer.writerows([
                {"target_id":"00001","target_index":0,"station_id":1,"start_s":0,"end_s":500,"duration_s":500,"priority":"high"},
                {"target_id":"00001","target_index":0,"station_id":2,"start_s":172900,"end_s":173500,"duration_s":600,"priority":"high"},
                {"target_id":"00002","target_index":1,"station_id":1,"start_s":100,"end_s":700,"duration_s":600,"priority":"medium"},
            ])
        c_hash = hashlib.sha256(c_path.read_bytes()).hexdigest()
        (base / "C_optical/manifest.json").write_text(json.dumps({
            "layer":"C_optical","window_count":3,"windows_sha256":c_hash,
            "priority_file_sha256":hashlib.sha256(priority.read_bytes()).hexdigest()
        }), encoding="utf-8")
        d_fields = c_fields + ["source_C_line", "illumination_status"]
        d_path = cache / "windows.csv"
        with d_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=d_fields); writer.writeheader(); writer.writerows([
                {"target_id":"00001","target_index":0,"station_id":1,"start_s":0,"end_s":500,"duration_s":500,"priority":"high","source_C_line":2,"illumination_status":"sunlit"},
                {"target_id":"00001","target_index":0,"station_id":2,"start_s":172900,"end_s":173500,"duration_s":600,"priority":"high","source_C_line":3,"illumination_status":"sunlit"},
                {"target_id":"00002","target_index":1,"station_id":1,"start_s":100,"end_s":700,"duration_s":600,"priority":"medium","source_C_line":4,"illumination_status":"sunlit"},
            ])
        with (base / "A_orbit/target_status.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["target_id", "target_index", "status"])
            writer.writeheader(); writer.writerows([
                {"target_id":"00001","target_index":0,"status":"has_windows"},
                {"target_id":"00002","target_index":1,"status":"has_windows"},
            ])
        a_status = base / "A_orbit/target_status.csv"
        a_manifest_path = base / "A_orbit/manifest.json"
        a_manifest_path.write_text(json.dumps({"target_status_sha256":hashlib.sha256(a_status.read_bytes()).hexdigest()}), encoding="utf-8")
        c_manifest_path = base / "C_optical/manifest.json"
        c_manifest = json.loads(c_manifest_path.read_text(encoding="utf-8"))
        c_manifest["dependencies"] = {"A_manifest_sha256":hashlib.sha256(a_manifest_path.read_bytes()).hexdigest()}
        c_manifest_path.write_text(json.dumps(c_manifest), encoding="utf-8")
        project = Path(__file__).resolve().parent
        tle_path, ephemeris_path = project / "data/轨道.txt", project / "data/ephemeris/de421.bsp"
        d_manifest = {
            "schema_version":"m1-illumination-gap-refinement-aug2026-2.0",
            "layer":"D_illumination_refined",
            "planning":{"start_utc":"2026-08-01T00:00:00+00:00","end_utc":"2026-08-07T00:00:00+00:00","time_scale":"UTC"},
            "source_C_sha256":c_hash,"tle_sha256":hashlib.sha256(tle_path.read_bytes()).hexdigest(),
            "ephemeris_sha256":hashlib.sha256(ephemeris_path.read_bytes()).hexdigest(),
            "windows_sha256":hashlib.sha256(d_path.read_bytes()).hexdigest(),"rows":3
        }
        (cache / "manifest.json").write_text(json.dumps(d_manifest), encoding="utf-8")
        d_manifest_hash = hashlib.sha256((cache / "manifest.json").read_bytes()).hexdigest()
        config = root / "config.json"
        config.write_text(json.dumps({
            "minimum_observation_s":120,"maximum_observation_s":240,
            "different_target_switch_s":30,"target_revisit_cooldown_s":172800,
            "priority_weights":{"high":5,"medium":3,"low":2},
            "duration_score_rule":"linear_60_to_100",
            "repeat_observation_rule":"cumulative_after_48h","numeric_tolerance_s":1e-6,
            "candidate_data_directory":str(cache),"candidate_windows_sha256":d_manifest["windows_sha256"],
            "candidate_manifest_sha256":d_manifest_hash,"planning_start_utc":"2026-08-01T00:00:00+00:00",
            "planning_end_utc":"2026-08-07T00:00:00+00:00","time_scale":"UTC",
            "tle_path":str(tle_path),"ephemeris_path":str(ephemeris_path),
            "priority_file":str(priority),"referee_sunlight_sample_step_s":1.0
        }), encoding="utf-8")
        return cache, priority, config

    def referee_mocked(self, *args):
        with patch("m2_referee.load_tle_table", return_value={"1":object(), "2":object()}), \
             patch("m2_referee.load") as skyfield_load, \
             patch("m2_referee.check_task_sunlight", return_value=(True, 1.0)):
            skyfield_load.timescale.return_value = object()
            skyfield_load.return_value = {"earth":object(), "sun":object()}
            return referee(*args)

    def row(self, **overrides):
        row = {
            "task_id":"a", "algorithm":"test", "target_id":"00001", "canonical_target_id":"1",
            "target_index":0, "station_id":1, "start_s":0, "end_s":120, "duration_s":120,
            "priority":"high", "score":3.0, "visit_number":1, "source_d_line":2,
            "source_window_start_s":0, "source_window_end_s":500,
        }
        row.update(overrides)
        return row

    def test_referee_accepts_exact_48h_boundary_and_accumulates_repeat_score(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); cache, priority, config = self.fixture(root)
            rows = [self.row(), self.row(task_id="b", station_id=2, start_s=172920, end_s=173040,
                    visit_number=2, source_d_line=3, source_window_start_s=172900, source_window_end_s=173500)]
            path = root / "schedule.csv"; write_schedule(path, rows)
            result = self.referee_mocked(path, cache, priority, config, 2, root / "violations.csv")
            self.assertTrue(result["legal"])
            self.assertEqual(result["unique_covered_targets"], 1)
            self.assertEqual(result["repeated_observation_count"], 1)
            self.assertAlmostEqual(result["total_score"], 6.0)
            self.assertAlmostEqual(result["minimum_revisit_gap_s"], 172800.0)

    def test_referee_rejects_cross_station_repeat_before_48h(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); cache, priority, config = self.fixture(root)
            rows = [self.row(), self.row(task_id="b", station_id=2, start_s=172919, end_s=173039,
                    visit_number=2, source_d_line=3, source_window_start_s=172900, source_window_end_s=173500)]
            path = root / "schedule.csv"; write_schedule(path, rows)
            result = self.referee_mocked(path, cache, priority, config, 2)
            self.assertIn("target_cooldown", result["violation_categories"])

    def test_referee_keeps_window_duration_station_and_switch_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); cache, priority, config = self.fixture(root)
            cases = {
                "duration_bounds": [self.row(end_s=100, duration_s=100, score=0)],
                "window_containment": [self.row(start_s=450, end_s=570)],
                "station_overlap": [self.row(), self.row(task_id="b", target_id="00002", canonical_target_id="2",
                    target_index=1, priority="medium", score=1.8, start_s=100, end_s=220,
                    station_id=1, source_d_line=4, source_window_start_s=100, source_window_end_s=700)],
                "switch_gap": [self.row(), self.row(task_id="b", target_id="00002", canonical_target_id="2",
                    target_index=1, priority="medium", score=1.8, start_s=130, end_s=250,
                    station_id=1, source_d_line=4, source_window_start_s=100, source_window_end_s=700)],
            }
            path = root / "schedule.csv"
            for category, rows in cases.items():
                write_schedule(path, rows)
                result = self.referee_mocked(path, cache, priority, config, 2)
                self.assertIn(category, result["violation_categories"])

    def test_referee_scoring_is_independent(self):
        config = {"minimum_observation_s":120,"maximum_observation_s":240,"numeric_tolerance_s":1e-6,
                  "priority_weights":{"high":5}}
        self.assertAlmostEqual(independent_score("high", 180, config), 4.0)

    def test_current_scheduler_cache_identity_is_exact_refined_d(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache, _, config = self.fixture(Path(tmp))
            manifest = validate_cache_identity(cache, config)
            self.assertEqual(manifest["layer"], "D_illumination_refined")
            with self.assertRaisesRegex(ValueError, "configured D directory"):
                validate_cache_identity(cache.parent, config)

    def test_referee_reports_independent_umbra_violation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); cache, priority, config = self.fixture(root)
            path = root / "schedule.csv"; write_schedule(path, [self.row()])
            with patch("m2_referee.load_tle_table", return_value={"1":object(), "2":object()}), \
                 patch("m2_referee.load") as skyfield_load, \
                 patch("m2_referee.check_task_sunlight", return_value=(False, -0.01)):
                skyfield_load.timescale.return_value = object()
                skyfield_load.return_value = {"earth":object(), "sun":object()}
                result = referee(path, cache, priority, config, 2)
            self.assertIn("satellite_umbra", result["violation_categories"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

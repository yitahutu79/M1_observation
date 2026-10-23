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


    def test_schedule_parser_exposes_utc_times_and_observation_durations(self):
        from satellite_status import _load_schedule_observations
        data = (
            b"task_id,target_id,station_id,start_s,end_s,duration_s,priority,score\n"
            b"t1,50574,1,120,240,120,high,3\n"
            b"t2,50574,4,172920,173160,240,high,5\n"
        )
        counts, observations, digest, stats = _load_schedule_observations(data)
        self.assertEqual(counts["50574"], 2)
        self.assertEqual(observations["50574"][0]["start_utc"], "2026-08-01T00:02:00.000Z")
        self.assertEqual(observations["50574"][0]["end_utc"], "2026-08-01T00:04:00.000Z")
        self.assertEqual(observations["50574"][0]["duration_s"], 120)
        self.assertTrue(all(item["duration_in_120_240_s_range"] for item in observations["50574"]))
        self.assertEqual(observations["50574"][1]["station_id"], "4")
        self.assertEqual(stats, {"timed_task_count": 2, "untimed_task_count": 0})
        self.assertEqual(len(digest), 64)

    def test_schedule_parser_rejects_duration_mismatch(self):
        from satellite_status import _load_schedule_observations
        with self.assertRaisesRegex(ValueError, "disagrees"):
            _load_schedule_observations(
                b"target_id,start_s,end_s,duration_s\n50574,0,120,121\n"
            )

    def test_schedule_csv_without_times_remains_count_only(self):
        from satellite_status import _load_schedule_observations
        counts, observations, _digest, stats = _load_schedule_observations(
            b"target_id,station_id\n50574,1\n"
        )
        self.assertEqual(counts["50574"], 1)
        self.assertEqual(observations, {})
        self.assertEqual(stats, {"timed_task_count": 0, "untimed_task_count": 1})


    def test_analysis_endpoint_accepts_request_without_tle_or_station_payload(self):
        import threading
        from http.server import ThreadingHTTPServer
        from unittest.mock import patch
        from urllib.request import Request, urlopen
        from web_app import Handler
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with patch("web_app.satellite_analysis", return_value={"summary": {"target_count": 1}}) as analyze:
                request = Request(
                    f"http://127.0.0.1:{server.server_port}/api/analysis",
                    data=b"{}", headers={"Content-Type": "application/json"}, method="POST",
                )
                with urlopen(request, timeout=3) as response:
                    result = json.loads(response.read())
                self.assertEqual(result["summary"]["target_count"], 1)
                analyze.assert_called_once_with(None)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)

    def test_run_job_records_stage_and_end_to_end_elapsed_time(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from web_app import run_job
        decision = {
            "legal": True, "unique_covered_targets": 0, "coverage_rate": 0.0,
            "total_score": 0.0, "task_count": 0, "repeated_observation_count": 0,
            "overall_station_utilization": 0.0, "violation_count": 0, "priority_metrics": {},
        }
        with tempfile.TemporaryDirectory() as temp:
            with patch("web_app.RUNS", Path(temp)), \
                 patch("web_app.schedule_baseline", return_value=([], {"scheduling_elapsed_s": 0.01})), \
                 patch("web_app.referee", return_value=decision):
                jobs = __import__("web_app").JOBS
                jobs["progress-test"] = {}
                run_job("progress-test", 1000, "coverage_score_hybrid")
                job = jobs.pop("progress-test")
        self.assertEqual(job["state"], "complete")
        self.assertEqual(job["stage"], "complete")
        self.assertGreaterEqual(job["elapsed_s"], 0.0)
        self.assertGreaterEqual(job["result"]["total_elapsed_s"], 0.0)
        self.assertIn("referee_elapsed_s", job["result"])

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
        self.assertEqual(row["scheduled_timed_visits"], 0)
        self.assertEqual(row["scheduled_observations"], [])
        self.assertNotIn("tle_age_days", row)
        self.assertNotIn("reentry_status", row)
        self.assertEqual(row["schedule_status"], "已排程（2次）")


if __name__ == "__main__":
    unittest.main()

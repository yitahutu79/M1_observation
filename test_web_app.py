import unittest

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


if __name__ == "__main__":
    unittest.main()

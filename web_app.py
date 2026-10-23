"""Local, upload-first interface for the verified August M2 baseline.

The server binds to localhost only. Uploaded inputs are accepted for scheduling
only when their bytes match the inputs pinned by the released D-layer cache.
"""
from __future__ import annotations

import base64
import csv
import hashlib
import json
import threading
import time
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from m2_referee import referee
from m2_scheduler import schedule_baseline, write_schedule
from satellite_status import build_satellite_status

ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "m2_config.json"
PRIORITY = ROOT / "data/优先级.zip"
CACHE = ROOT / "m1_validation/formal_20260801_candidate/D_illumination_refined_v2"
RUNS = ROOT / "output/ui_runs"
UI = ROOT / "web/index.html"
MAX_TLE_BYTES = 10 * 1024 * 1024
MAX_STATION_BYTES = 64 * 1024
MAX_SCHEDULE_BYTES = 20 * 1024 * 1024
ALGORITHMS = {
    "coverage_score_hybrid": "覆盖与得分平衡（推荐）",
    "first_observation_first": "优先覆盖更多目标",
    "total_score_first": "优先提高总得分",
}
JOBS: dict[str, dict] = {}
LOCK = threading.Lock()
ANALYSIS_LOCK = threading.Lock()
ANALYSIS_CACHE: dict[str, dict] = {}
LATEST_ANALYSIS: dict | None = None


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def official_input_paths() -> dict[str, Path]:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    return {"tle": ROOT / config["tle_path"], "stations": ROOT / "data/站址.txt"}


def validate_tle(data: bytes) -> dict:
    try:
        lines = data.decode("utf-8-sig").splitlines()
    except UnicodeDecodeError as exc:
        raise ValueError("TLE文件不是可读的UTF-8文本") from exc
    if not lines or len(lines) % 3:
        raise ValueError("TLE必须按每颗卫星3行排列：名称、轨道行1、轨道行2")
    ids = []
    for offset in range(0, len(lines), 3):
        name, line1, line2 = lines[offset:offset + 3]
        if not name.startswith("0 ") or not line1.startswith("1 ") or not line2.startswith("2 "):
            raise ValueError(f"第 {offset // 3 + 1} 组不是标准的三行TLE")
        if len(line1) < 7 or len(line2) < 7 or line1[2:7] != line2[2:7]:
            raise ValueError(f"第 {offset // 3 + 1} 组TLE的卫星编号不一致")
        ids.append(line1[2:7])
    if len(set(ids)) != len(ids):
        raise ValueError("TLE中存在重复卫星编号，请先整理输入文件")
    return {"records": len(ids), "unique_satellites": len(set(ids))}


def validate_stations(data: bytes) -> dict:
    try:
        lines = data.decode("utf-8-sig").splitlines()
    except UnicodeDecodeError as exc:
        raise ValueError("站点文件不是可读的UTF-8文本") from exc
    import re
    pattern = re.compile(r"^\s*(\d+)\s*[：:]\s*([+-]?[\d.]+)\s*,\s*([+-]?[\d.]+)\s*,\s*([+-]?[\d.]+)")
    stations = []
    for line in lines:
        match = pattern.match(line)
        if not match:
            continue
        ident, lon, lat, elev = match.groups()
        lon, lat, elev = float(lon), float(lat), float(elev)
        if not -90 <= lat <= 90 or not -1000 <= elev <= 10000:
            raise ValueError(f"站点 {ident} 的纬度或海拔超出合理范围")
        stations.append((int(ident), lon, lat, elev))
    if not stations:
        raise ValueError("未找到站点。每行格式应为：站点编号：经度, 纬度, 海拔(m)")
    if len({row[0] for row in stations}) != len(stations):
        raise ValueError("站点编号重复")
    return {"stations": len(stations), "station_ids": [row[0] for row in stations]}


def check_uploads(tle: bytes, stations: bytes) -> dict:
    tle_info = validate_tle(tle)
    station_info = validate_stations(stations)
    expected_paths = official_input_paths()
    expected = {key: sha256_bytes(path.read_bytes()) for key, path in expected_paths.items()}
    actual = {"tle": sha256_bytes(tle), "stations": sha256_bytes(stations)}
    matches = {key: actual[key] == expected[key] for key in actual}
    return {"valid": True, "official_input_match": all(matches.values()), "matches": matches,
            "sha256": actual, "expected_sha256": expected, "tle": tle_info, "station": station_info,
            "planning_start_utc": "2026-08-01 00:00", "planning_end_utc": "2026-08-07 00:00",
            "time_scale": "UTC"}


def satellite_analysis(schedule_csv: bytes | None) -> dict:
    global LATEST_ANALYSIS
    if schedule_csv is not None and len(schedule_csv) > MAX_SCHEDULE_BYTES:
        raise ValueError("排程CSV最大20 MB")
    schedule_sha = hashlib.sha256(schedule_csv).hexdigest() if schedule_csv is not None else "no-schedule"
    with ANALYSIS_LOCK:
        if schedule_sha not in ANALYSIS_CACHE:
            from m2_scheduler import validate_cache_identity
            validate_cache_identity(CACHE, CONFIG)
            report = build_satellite_status(
                official_input_paths()["tle"], CACHE.parent / "A_orbit/target_status.csv",
                CACHE, schedule_csv=schedule_csv, priority_path=PRIORITY,
            )
            ANALYSIS_CACHE[schedule_sha] = report
        LATEST_ANALYSIS = ANALYSIS_CACHE[schedule_sha]
        return LATEST_ANALYSIS


def analysis_csv_bytes(report: dict) -> bytes:
    records = report["records"]
    if not records:
        return b""
    fields = list(records[0])
    import io
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for row in records:
        encoded = {
            key: json.dumps(value, ensure_ascii=False, separators=(",", ":"))
            if isinstance(value, (dict, list)) else value
            for key, value in row.items()
        }
        writer.writerow(encoded)
    return output.getvalue().encode("utf-8-sig")


def run_job(job_id: str, target_limit: int, algorithm: str) -> None:
    job = JOBS[job_id]
    out = RUNS / job_id
    out.mkdir(parents=True, exist_ok=False)
    schedule_path = out / "schedule.csv"
    violation_path = out / "violations.csv"
    try:
        job.update(state="running", message="正在生成排程…")
        rows, scheduler_metrics = schedule_baseline(CACHE, PRIORITY, CONFIG, target_limit, algorithm)
        write_schedule(schedule_path, rows)
        job.update(message="排程已生成，独立裁判正在逐项验收…")
        referee_started = time.perf_counter()
        decision = referee(schedule_path, CACHE, PRIORITY, CONFIG, target_limit, violation_path)
        result = {
            "legal": decision["legal"], "unique_covered_targets": decision["unique_covered_targets"],
            "coverage_rate": decision["coverage_rate"], "total_score": decision["total_score"],
            "task_count": decision["task_count"],
            "repeated_observation_count": decision["repeated_observation_count"],
            "overall_station_utilization": decision["overall_station_utilization"],
            "violation_count": decision["violation_count"], "priority_metrics": decision["priority_metrics"],
            "scheduling_elapsed_s": scheduler_metrics["scheduling_elapsed_s"],
            "referee_elapsed_s": time.perf_counter() - referee_started, "algorithm": algorithm,
            "target_limit": target_limit,
            "planning": "2026-08-01 00:00 至 2026-08-07 00:00 UTC",
        }
        (out / "summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        job.update(state="complete", message="独立裁判验收完成", result=result,
                   schedule=f"/api/jobs/{job_id}/schedule", violations=f"/api/jobs/{job_id}/violations")
    except Exception as exc:  # surfaced in the UI; job never reports unverified success
        job.update(state="failed", message=f"运行失败：{type(exc).__name__}: {exc}")


class Handler(BaseHTTPRequestHandler):
    server_version = "M1M2LocalUI/1.0"

    def log_message(self, fmt, *args):
        print(f"[ui] {self.address_string()} {fmt % args}")

    def send_json(self, status: int, value: dict):
        body = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length > MAX_SCHEDULE_BYTES * 4 // 3 + 1024 * 1024:
            raise ValueError("上传内容过大")
        return json.loads(self.rfile.read(length))

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            if not UI.is_file():
                self.send_error(404, "UI assets missing")
                return
            body = UI.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path == "/api/analysis.csv":
            if LATEST_ANALYSIS is None:
                self.send_json(404, {"error": "请先运行卫星状态分析"})
                return
            body = analysis_csv_bytes(LATEST_ANALYSIS)
            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", 'attachment; filename="satellite_status_analysis.csv"')
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        pieces = path.strip("/").split("/")
        if len(pieces) == 4 and pieces[:2] == ["api", "jobs"]:
            job_id, kind = pieces[2], pieces[3]
            if job_id not in JOBS:
                self.send_error(404)
                return
            file_path = RUNS / job_id / ("schedule.csv" if kind == "schedule" else "violations.csv" if kind == "violations" else "")
            if not file_path.is_file():
                self.send_error(404)
                return
            body = file_path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", f'attachment; filename="{kind}.csv"')
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if len(pieces) == 3 and pieces[:2] == ["api", "jobs"]:
            job = JOBS.get(pieces[2])
            if not job:
                self.send_json(404, {"error": "任务不存在"})
            else:
                self.send_json(200, job)
            return
        self.send_error(404)

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            payload = self.read_json()
            if path == "/api/analysis":
                encoded_schedule = payload.get("schedule_base64")
                schedule_data = base64.b64decode(encoded_schedule, validate=True) if encoded_schedule else None
                self.send_json(200, satellite_analysis(schedule_data))
                return
            tle = base64.b64decode(payload.get("tle_base64", ""), validate=True)
            stations = base64.b64decode(payload.get("stations_base64", ""), validate=True)
            if not tle or len(tle) > MAX_TLE_BYTES or not stations or len(stations) > MAX_STATION_BYTES:
                raise ValueError("TLE最大10 MB，站点文件最大64 KB，且都不能为空")
            checked = check_uploads(tle, stations)
            if path == "/api/validate":
                self.send_json(200, checked)
                return
            if path != "/api/run":
                self.send_error(404)
                return
            if not checked["official_input_match"]:
                self.send_json(409, {"error": "上传文件与当前正式D窗口绑定的输入不一致。为避免误用旧窗口，已停止运行。需要先为这组输入生成并验收新的D窗口。", "validation": checked})
                return
            target_limit = int(payload.get("target_limit", 1000))
            algorithm = payload.get("algorithm", "coverage_score_hybrid")
            if target_limit not in (1000, 10000) or algorithm not in ALGORITHMS:
                raise ValueError("请选择1000或10000目标，以及有效的调度基线")
            job_id = uuid.uuid4().hex[:12]
            with LOCK:
                JOBS[job_id] = {"id": job_id, "state": "queued", "message": "任务已排队",
                                "created_utc": datetime.now(timezone.utc).isoformat()}
            threading.Thread(target=run_job, args=(job_id, target_limit, algorithm), daemon=True).start()
            self.send_json(202, {"job_id": job_id, "state": "queued"})
        except (ValueError, KeyError, json.JSONDecodeError) as exc:
            self.send_json(400, {"error": str(exc)})


def main():
    missing = [str(path) for path in [CONFIG, PRIORITY, CACHE / "windows.csv", CACHE / "manifest.json",
                                      CACHE.parent / "A_orbit/target_status.csv"] if not path.is_file()]
    if missing:
        raise SystemExit("本地正式输入/缓存不完整，不能启动调度界面：\n" + "\n".join(missing))
    RUNS.mkdir(parents=True, exist_ok=True)
    host = "127.0.0.1"
    server = None
    for port in range(8765, 8781):
        try:
            server = ThreadingHTTPServer((host, port), Handler)
            break
        except OSError:
            continue
    if server is None:
        raise SystemExit("本地端口8765–8780均不可用，请关闭占用进程后重试")
    print(f"打开浏览器访问 http://{host}:{server.server_port} （仅本机可访问；Ctrl+C 停止）")
    server.serve_forever()


if __name__ == "__main__":
    main()

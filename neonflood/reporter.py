"""
neonflood/reporter.py
=====================
Session analytics, JSON/CSV report export, and real-time file logging.

Classes
-------
SessionReport  — Collects stats during a session; exports to JSON or CSV.
SessionLogger  — Writes timestamped log lines to ~/.neonflood/logs/ in real-time.

Output directories
------------------
Logs    : ~/.neonflood/logs/session_YYYY-MM-DD_HH-MM-SS.log
Reports : ~/.neonflood/reports/neonflood_YYYY-MM-DD_HH-MM-SS.{json,csv}
          (or a user-specified path via export_json / export_csv)
"""

import json
import csv
import time
from datetime import datetime
from pathlib import Path


# ── Directory setup ───────────────────────────────────────────────────────────

LOG_DIR    = Path.home() / ".neonflood" / "logs"
REPORT_DIR = Path.home() / ".neonflood" / "reports"

LOG_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
#  SessionReport
# ─────────────────────────────────────────────────────────────────────────────

class SessionReport:
    """
    Accumulates statistics for one test session and provides export methods.

    Usage
    -----
    report = SessionReport()
    report.start(target="http://example.com", mode="get", workers=5, sockets=50)
    # ... during session ...
    report.record_rps(rps_value)          # call once per second
    # ... on session end ...
    report.finish(hits=1000, fails=50)
    report.export_json("/path/to/report.json")
    report.export_csv("/path/to/report.csv")
    """

    def __init__(self):
        self._data = {}
        self.reset()

    def reset(self):
        """Reset all accumulated data for a new session."""
        self.target      = ""
        self.mode        = ""
        self.workers     = 0
        self.sockets     = 0
        self.proxy       = None
        self.rate_limit  = 0
        self.start_time  = None   # float (epoch)
        self.end_time    = None   # float (epoch)
        self.rps_history = []     # list of (epoch_float, rps_int)
        self.total_hits  = 0
        self.total_fails = 0

    def start(self, target, mode, workers, sockets, proxy=None, rate_limit=0):
        """
        Begin a new session.  Resets all previous data.

        Parameters
        ----------
        target     : str       — full target URL
        mode       : str       — attack mode name
        workers    : int       — number of worker processes
        sockets    : int       — sockets per worker
        proxy      : str|None  — proxy string (display only)
        rate_limit : int       — max rps cap (0 = unlimited)
        """
        self.reset()
        self.target     = target
        self.mode       = mode
        self.workers    = workers
        self.sockets    = sockets
        self.proxy      = proxy
        self.rate_limit = rate_limit
        self.start_time = time.time()

    def record_rps(self, rps):
        """
        Append a RPS sample to the history.

        Parameters
        ----------
        rps : int|float — requests per second at this moment
        """
        self.rps_history.append((time.time(), int(rps)))

    def finish(self, hits, fails):
        """
        Mark the session as complete.

        Parameters
        ----------
        hits  : int — total successful responses
        fails : int — total failed/blocked responses
        """
        self.end_time    = time.time()
        self.total_hits  = hits
        self.total_fails = fails

    # ── Computed properties ───────────────────────────────────────────────

    @property
    def duration(self):
        """Session duration in seconds (float).  0.0 if not yet finished."""
        if self.start_time and self.end_time:
            return round(self.end_time - self.start_time, 2)
        return 0.0

    @property
    def avg_rps(self):
        """Average requests per second across the recorded history."""
        if not self.rps_history:
            return 0.0
        return round(sum(r for _, r in self.rps_history) / len(self.rps_history), 1)

    @property
    def peak_rps(self):
        """Peak (maximum) requests per second recorded."""
        if not self.rps_history:
            return 0
        return max(r for _, r in self.rps_history)

    # ── Serialisation ─────────────────────────────────────────────────────

    def to_dict(self):
        """
        Return a JSON-serialisable dictionary of all session data.

        Returns
        -------
        dict
        """
        return {
            "tool":               "NeonFlood v2.0.0",
            "author":             "NH Prince",
            "website":            "https://nhprince.dpdns.org",
            "disclaimer":         "For authorized and educational use only.",
            "target":             self.target,
            "mode":               self.mode,
            "workers":            self.workers,
            "sockets_per_worker": self.sockets,
            "proxy":              str(self.proxy) if self.proxy else None,
            "rate_limit_rps":     self.rate_limit,
            "start_time":         datetime.fromtimestamp(self.start_time).isoformat()
                                  if self.start_time else None,
            "end_time":           datetime.fromtimestamp(self.end_time).isoformat()
                                  if self.end_time else None,
            "duration_seconds":   self.duration,
            "total_requests":     self.total_hits + self.total_fails,
            "successful_hits":    self.total_hits,
            "failed_requests":    self.total_fails,
            "avg_rps":            self.avg_rps,
            "peak_rps":           self.peak_rps,
            "rps_history":        [
                {"timestamp": datetime.fromtimestamp(t).isoformat(), "rps": r}
                for t, r in self.rps_history
            ],
        }

    # ── Export methods ────────────────────────────────────────────────────

    def export_json(self, path=None):
        """
        Write session data to a JSON file.

        Parameters
        ----------
        path : str | Path | None
            Destination file path.  If None an auto-generated path under
            ~/.neonflood/reports/ is used.

        Returns
        -------
        str — absolute path to the written file.
        """
        if path is None:
            ts   = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            path = REPORT_DIR / f"neonflood_{ts}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)
        return str(path)

    def export_csv(self, path=None):
        """
        Write session summary and RPS history to a CSV file.

        Parameters
        ----------
        path : str | Path | None
            Destination file path.  If None an auto-generated path under
            ~/.neonflood/reports/ is used.

        Returns
        -------
        str — absolute path to the written file.
        """
        if path is None:
            ts   = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            path = REPORT_DIR / f"neonflood_{ts}.csv"

        d = self.to_dict()
        summary_rows = [
            ["Field",            "Value"],
            ["Tool",              d["tool"]],
            ["Target",            d["target"]],
            ["Mode",              d["mode"]],
            ["Workers",           d["workers"]],
            ["Sockets/Worker",    d["sockets_per_worker"]],
            ["Proxy",             d["proxy"] or "None"],
            ["Rate Limit (rps)",  d["rate_limit_rps"]],
            ["Start Time",        d["start_time"] or ""],
            ["End Time",          d["end_time"] or ""],
            ["Duration (s)",      d["duration_seconds"]],
            ["Total Requests",    d["total_requests"]],
            ["Successful Hits",   d["successful_hits"]],
            ["Failed Requests",   d["failed_requests"]],
            ["Avg RPS",           d["avg_rps"]],
            ["Peak RPS",          d["peak_rps"]],
        ]

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(summary_rows)
            writer.writerow([])
            writer.writerow(["Timestamp", "RPS"])
            for entry in d["rps_history"]:
                writer.writerow([entry["timestamp"], entry["rps"]])

        return str(path)


# ─────────────────────────────────────────────────────────────────────────────
#  SessionLogger
# ─────────────────────────────────────────────────────────────────────────────

class SessionLogger:
    """
    Writes real-time log lines to a session log file in ~/.neonflood/logs/.

    The file is opened with line buffering (buffering=1) so that entries are
    flushed immediately even on crash.

    Usage
    -----
    logger = SessionLogger()
    logger.write("HIT", "GET 200 — example.com")
    logger.close()
    """

    def __init__(self):
        ts        = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.path = LOG_DIR / f"session_{ts}.log"
        self._fh  = open(self.path, "w", buffering=1, encoding="utf-8")
        self._fh.write(
            f"NeonFlood v2.0.0 — Session Log\n"
            f"Started : {datetime.now().isoformat()}\n"
            f"{'=' * 60}\n"
        )

    def write(self, level, msg):
        """
        Append one log line.

        Parameters
        ----------
        level : str — log level tag (HIT / FAIL / WARN / LOAD / SYS)
        msg   : str — message text
        """
        if self._fh:
            ts = datetime.now().strftime("%H:%M:%S")
            self._fh.write(f"[{ts}] {level}: {msg}\n")

    def close(self):
        """Flush and close the log file."""
        if self._fh:
            self._fh.write(
                f"{'=' * 60}\n"
                f"Ended   : {datetime.now().isoformat()}\n"
            )
            self._fh.close()
            self._fh = None

    def __del__(self):
        self.close()

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import sqlite3
import json
import statistics


@dataclass
class DriftMetric:
    """Drift detection metric."""

    metric_name: str
    baseline_value: float
    current_value: float
    deviation: float
    alert_flag: bool
    timestamp: str


@dataclass
class DriftConfig:
    """Configuration for drift detection."""

    sigma_threshold: float = 2.0  # 2 standard deviations
    min_samples: int = 10  # Minimum samples for baseline
    check_interval_hours: int = 24


class DriftDetector:
    """
    Detect drift in system metrics over time.

    Monitors:
    - Category distribution
    - Budget recommendation shifts
    - Anomaly frequency
    """

    def __init__(self, config: DriftConfig = None, db_path: str = "event_log.db"):
        self.config = config or DriftConfig()
        self.db_path = db_path
        self._init_table()

    def _init_table(self):
        """Initialize drift tracking tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS drift_baselines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_name TEXT NOT NULL UNIQUE,
                baseline_mean REAL NOT NULL,
                baseline_std REAL NOT NULL,
                sample_count INTEGER NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS drift_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_name TEXT NOT NULL,
                value REAL NOT NULL,
                timestamp TEXT NOT NULL,
                session_id TEXT,
                UNIQUE(metric_name, timestamp)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS drift_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_name TEXT NOT NULL,
                baseline_value REAL NOT NULL,
                current_value REAL NOT NULL,
                deviation REAL NOT NULL,
                threshold REAL NOT NULL,
                timestamp TEXT NOT NULL,
                UNIQUE(metric_name, timestamp)
            )
        """)

        conn.commit()
        conn.close()

    def record_metric(self, metric_name: str, value: float, session_id: str = ""):
        """Record a metric value."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO drift_metrics (metric_name, value, timestamp, session_id)
                VALUES (?, ?, ?, ?)
            """,
                (metric_name, value, datetime.utcnow().isoformat(), session_id),
            )
            conn.commit()
        finally:
            conn.close()

    def update_baseline(self, metric_name: str, window_hours: int = 168):
        """Update baseline statistics for a metric."""
        cutoff = (datetime.utcnow() - timedelta(hours=window_hours)).isoformat()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT value FROM drift_metrics
            WHERE metric_name = ? AND timestamp >= ?
        """,
            (metric_name, cutoff),
        )

        values = [row[0] for row in cursor.fetchall()]
        conn.close()

        if len(values) < self.config.min_samples:
            return None

        mean = statistics.mean(values)
        std = statistics.stdev(values) if len(values) > 1 else 0.0

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT OR REPLACE INTO drift_baselines (metric_name, baseline_mean, baseline_std, sample_count, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """,
                (metric_name, mean, std, len(values), datetime.utcnow().isoformat()),
            )
            conn.commit()
        finally:
            conn.close()

        return {"mean": mean, "std": std, "count": len(values)}

    def check_drift(self, metric_name: str, current_value: float) -> DriftMetric:
        """Check if current value deviates from baseline."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT baseline_mean, baseline_std FROM drift_baselines
            WHERE metric_name = ?
        """,
            (metric_name,),
        )

        row = cursor.fetchone()
        conn.close()

        if not row:
            baseline_mean = current_value
            baseline_std = 0.0
        else:
            baseline_mean, baseline_std = row

        if baseline_std > 0:
            z_score = abs(current_value - baseline_mean) / baseline_std
            deviation = z_score * 100  # Convert to percentage
            alert_flag = z_score > self.config.sigma_threshold
        else:
            deviation = abs(current_value - baseline_mean) if baseline_mean > 0 else 0
            alert_flag = deviation > 0.2  # 20% deviation if no std

        metric = DriftMetric(
            metric_name=metric_name,
            baseline_value=baseline_mean,
            current_value=current_value,
            deviation=deviation,
            alert_flag=alert_flag,
            timestamp=datetime.utcnow().isoformat(),
        )

        if alert_flag:
            self._create_alert(metric)

        return metric

    def _create_alert(self, metric: DriftMetric):
        """Create drift alert."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO drift_alerts 
                (metric_name, baseline_value, current_value, deviation, threshold, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    metric.metric_name,
                    metric.baseline_value,
                    metric.current_value,
                    metric.deviation,
                    self.config.sigma_threshold * 100,
                    metric.timestamp,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def get_drift_report(self, metric_names: List[str]) -> List[Dict]:
        """Get drift report for multiple metrics."""
        report = []

        for name in metric_names:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT value FROM drift_metrics
                WHERE metric_name = ?
                ORDER BY timestamp DESC
                LIMIT 10
            """,
                (name,),
            )

            values = [row[0] for row in cursor.fetchall()]
            conn.close()

            if values:
                current = values[0]
                drift = self.check_drift(name, current)
                report.append(
                    {
                        "metric": name,
                        "baseline": drift.baseline_value,
                        "current": drift.current_value,
                        "deviation": drift.deviation,
                        "alert": drift.alert_flag,
                    }
                )

        return report

    def get_alerts(self, metric_name: Optional[str] = None) -> List[Dict]:
        """Get drift alerts."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if metric_name:
            cursor.execute(
                """
                SELECT metric_name, baseline_value, current_value, deviation, timestamp
                FROM drift_alerts
                WHERE metric_name = ?
                ORDER BY timestamp DESC
            """,
                (metric_name,),
            )
        else:
            cursor.execute("""
                SELECT metric_name, baseline_value, current_value, deviation, timestamp
                FROM drift_alerts
                ORDER BY timestamp DESC
                LIMIT 20
            """)

        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "metric": r[0],
                "baseline": r[1],
                "current": r[2],
                "deviation": r[3],
                "timestamp": r[4],
            }
            for r in rows
        ]


_global_drift_detector: Optional[DriftDetector] = None


def get_drift_detector(config: DriftConfig = None) -> DriftDetector:
    """Get global drift detector instance."""
    global _global_drift_detector
    if _global_drift_detector is None:
        _global_drift_detector = DriftDetector(config)
    return _global_drift_detector

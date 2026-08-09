"""Baggage risk scoring.

Rule-driven baseline that flags bags likely to be delayed from: short transfer time,
missing expected scan, and high transfer workload. The score is explicitly labeled as a
prototype in the UI itself (base.BaggageRiskResult.model_label).
"""
from datetime import datetime, timedelta

from .base import BaggageRiskResult


def score_baggage(bag, latest_scan_at, scans, transfer_workload: int = 0) -> BaggageRiskResult:
    reasons: list[str] = []
    score = 0.0

    expected_scans = {"Checked", "Screening", "Sorting", "Loaded"}
    seen = {s.scan_event for s in scans}
    missing = expected_scans - seen
    if missing:
        score += 0.35
        reasons.append(f"Missing expected scan event: {', '.join(sorted(missing))}")

    if bag.transfer_time_minutes is not None:
        if bag.transfer_time_minutes < 45:
            score += 0.4
            reasons.append(f"Short transfer time ({bag.transfer_time_minutes:.0f} min < 45)")
        elif bag.transfer_time_minutes < 90:
            score += 0.15
            reasons.append(f"Tight transfer window ({bag.transfer_time_minutes:.0f} min)")

    if transfer_workload >= 6:
        score += 0.15
        reasons.append(f"High transfer workload ({transfer_workload} concurrent transfers)")

    if bag.status in ("Missing", "Delayed", "Damaged"):
        score += 0.5
        reasons.append(f"Already in exception status '{bag.status}'")

    # Stale scan: no scan within the last 90 minutes while still processing.
    if latest_scan_at is not None:
        stale = datetime.now() - latest_scan_at
        if stale > timedelta(minutes=90):
            score += 0.2
            reasons.append(f"No scan for {int(stale.total_seconds() // 60)} minutes")

    score = min(1.0, round(score, 2))
    return BaggageRiskResult(risk_score=score, reasons=reasons)

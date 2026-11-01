"""Reconstruct daily energy from Recorder's reset-adjusted hourly sums."""
from __future__ import annotations

from math import isfinite

from .ledger import Ledger


def reconstruct(timezone, direction, rows, begin, now, current):
    """Build a replacement off to the side; never mix raw states and sums.

    A statistics row holds the cumulative sum/state at the END of its hour.
    The hour before begin supplies the baseline. The final raw meter state
    bridges the last statistics hour to the live observation without counting
    the statistics sum's arbitrary offset as consumption.
    """
    points = []
    for row in sorted(rows, key=lambda r: r["start"]):
        end = row.get("end", row["start"] + 3600)
        value = row.get("sum")
        if end <= now and isinstance(value, (int, float)) and isfinite(value):
            points.append((end, value, row.get("state")))
    if len(points) < 2 or current is None:
        return None
    baseline = [i for i, point in enumerate(points) if point[0] <= begin]
    first = baseline[-1] if baseline else 0
    points = points[first:]
    if len(points) < 2 or points[-1][0] <= begin:
        return None
    ledger = Ledger(timezone)
    started = max(begin, points[0][0])
    reasons = []
    if points[0][0] > begin:
        reasons.append("missing_start_baseline")
    elif points[0][0] < begin:
        # The cumulative amount across the gap is known, but the share before
        # the billing boundary is not. Never present that estimate as exact.
        reasons.append("estimated_start_boundary")
    gaps = 0
    longest_gap = 0.0

    def book(left, right, amount):
        if right == left and amount == 0:
            return
        if amount < 0:
            if "decreasing_sum_or_counter_reset" not in reasons:
                reasons.append("decreasing_sum_or_counter_reset")
            return
        if right <= left:
            if "invalid_interval" not in reasons:
                reasons.append("invalid_interval")
            return
        for day, a, b in ledger.segments(max(left, begin), right):
            bucket = ledger.energy.setdefault(day.isoformat(), {"import": 0.0, "export": 0.0})
            bucket[direction] += amount * (b - a) / (right - left)

    for previous, point in zip(points, points[1:]):
        gap = point[0] - previous[0]
        if gap > 3600.01:
            gaps += 1
            longest_gap = max(longest_gap, gap)
        book(previous[0], point[0], point[1] - previous[1])
    end, _, raw = points[-1]
    if not isinstance(raw, (int, float)) or not isfinite(raw) or raw < 0:
        return None
    tail_seconds = now - end
    book(end, now, current - raw)
    ledger.last[direction] = [current, now]
    ledger.history[direction] = {"tracking_since": started, "complete": not reasons,
                                 "incomplete_reasons": reasons,
                                 "distribution_estimated": gaps > 0 or tail_seconds > 7200 or "estimated_start_boundary" in reasons,
                                 "statistics_gaps": gaps, "longest_gap_seconds": longest_gap,
                                 "live_tail_seconds": tail_seconds, "version": 2,
                                 "status": "imported", "requested_start": begin,
                                 "statistics_until": end}
    return ledger

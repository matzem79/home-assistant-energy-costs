"""Calendar-based import, export and standing-charge accounting."""
from __future__ import annotations

import calendar
from datetime import date, datetime, time, timedelta
from math import isfinite
from zoneinfo import ZoneInfo


def energy_value(state):
    """Normalize positive cumulative Wh/kWh sensor states to kWh."""
    if state is None:
        return None
    try:
        number = float(state.state)
    except (TypeError, ValueError):
        return None
    factor = {"Wh": 0.001, "kWh": 1}.get(state.attributes.get("unit_of_measurement"))
    return number * factor if factor and isfinite(number) and number >= 0 else None


def with_tariff(history, tariff):
    """Insert/replace a dated tariff without removing other validity periods."""
    effective = date.fromisoformat(tariff["valid_from"]).isoformat()
    result = [dict(t) for t in history if t["valid_from"] != effective]
    result.append(dict(tariff, valid_from=effective))
    return sorted(result, key=lambda t: t["valid_from"])


class Ledger:
    """Keep observed daily energy so backdated prices can be recalculated."""

    def __init__(self, timezone):
        self.zone = ZoneInfo(timezone)
        self.started = None
        self.last = {"import": None, "export": None}
        self.energy = {}
        self.resets = {"import": 0, "export": 0}

    def dump(self):
        return {"started": self.started, "last": self.last, "energy": self.energy, "resets": self.resets}

    def restore(self, data):
        if isinstance(data, dict):
            self.started = data.get("started")
            self.last.update(data.get("last", {}))
            self.energy = data.get("energy", {})
            self.resets.update(data.get("resets", {}))

    def midnight(self, day):
        return datetime.combine(day, time.min, self.zone).timestamp()

    def segments(self, begin, end):
        """Yield local-day portions, respecting different month lengths and DST."""
        while begin < end:
            day = datetime.fromtimestamp(begin, self.zone).date()
            limit = min(end, self.midnight(day + timedelta(days=1)))
            yield day, begin, limit
            begin = limit

    def observe(self, direction, value, now):
        """Book only new cumulative energy; a counter reset starts a new baseline."""
        if self.started is None:
            self.started = now
        if value is None or not isfinite(value) or value < 0:
            return
        previous = self.last[direction]
        if previous is None or value < previous[0]:
            if previous is not None:
                self.resets[direction] += 1
            self.last[direction] = [value, now]
            return
        if value == previous[0]:
            return
        begin, delta = previous[1], value - previous[0]
        if now < begin:
            self.last[direction] = [value, now]
            return
        parts = list(self.segments(begin, now))
        if not parts:
            parts = [(datetime.fromtimestamp(now, self.zone).date(), now, now)]
        for day, left, right in parts:
            amount = delta * (right - left) / (now - begin) if now > begin else delta
            bucket = self.energy.setdefault(day.isoformat(), {"import": 0.0, "export": 0.0})
            bucket[direction] += amount
        self.last[direction] = [value, now]

    @staticmethod
    def tariff_on(history, day):
        current = None
        for tariff in sorted(history, key=lambda t: t["valid_from"]):
            if tariff["valid_from"] <= day:
                current = tariff
            else:
                break
        return current

    def result(self, category, period, now, history, since=None):
        """Return an independent energy/cost/revenue/fee and missing-price amount."""
        today = datetime.fromtimestamp(now, self.zone).date().isoformat()
        matches = lambda day: (since is None or day >= since) and (period in ("total", "year") or (day == today if period == "day" else day[:7] == today[:7]))
        total, missing = 0.0, 0.0
        if category == "standing_charge":
            if self.started is None:
                return total, missing
            for day, left, right in self.segments(max(self.started, self.midnight(date.fromisoformat(since))) if since else self.started, now):
                key = day.isoformat()
                if not matches(key):
                    continue
                tariff = self.tariff_on(history, key)
                if tariff is not None:
                    seconds = self.midnight(day + timedelta(days=1)) - self.midnight(day)
                    total += tariff["monthly_fee"] / calendar.monthrange(day.year, day.month)[1] * (right - left) / seconds
                else:
                    seconds = self.midnight(day + timedelta(days=1)) - self.midnight(day)
                    missing += (right - left) / seconds
            return total, missing
        direction = "import" if category.startswith("import") else "export"
        for day, amounts in self.energy.items():
            if not matches(day):
                continue
            quantity = amounts[direction]
            if category.endswith("energy"):
                total += quantity
            else:
                tariff = self.tariff_on(history, day)
                if tariff is None:
                    missing += quantity
                else:
                    total += quantity * tariff[f"{direction}_price"]
        return total, missing


    @staticmethod
    def cycle_start(anchor, today):
        """Return the current yearly anniversary, clamping leap-day anchors."""
        initial = date.fromisoformat(anchor)
        if today < initial:
            return initial
        anniversary = date(today.year, initial.month, min(initial.day, calendar.monthrange(today.year, initial.month)[1]))
        if anniversary > today:
            year = today.year - 1
            anniversary = date(year, initial.month, min(initial.day, calendar.monthrange(year, initial.month)[1]))
        return anniversary

    def settlement(self, direction, now, settings):
        """Compare scheduled monthly advances with the corresponding earned cost."""
        today = datetime.fromtimestamp(now, self.zone).date()
        start = self.cycle_start(settings[f"{direction}_billing_start"], today)
        history = settings["tariffs"]
        category = "import_cost" if direction == "import" else "export_revenue"
        actual, missing = self.result(category, "year", now, history, since=start.isoformat())
        if direction == "import":
            fee, fee_missing = self.result("standing_charge", "year", now, history, since=start.isoformat())
            actual += fee
            missing += fee_missing
        payments, missing_payments = 0.0, 0
        # Only scheduled instalments observed since tracking began are included;
        # earlier costs/payments belong in an optional opening balance.
        if self.started is not None:
            index = 0
            while True:
                month_index = start.year * 12 + start.month - 1 + index
                year, month0 = divmod(month_index, 12)
                month = month0 + 1
                pay_day = date(year, month, min(start.day, calendar.monthrange(year, month)[1]))
                if pay_day > today or index >= 12:
                    break
                if self.midnight(pay_day) >= self.started:
                    tariff = self.tariff_on(history, pay_day.isoformat())
                    if tariff is None:
                        missing_payments += 1
                    else:
                        key = "monthly_import_payment" if direction == "import" else "monthly_export_credit"
                        payments += tariff.get(key, 0.0)
                index += 1
        opening_key = f"{direction}_opening_balance"
        partial = self.started is None or self.started > self.midnight(start)
        opening = (settings.get(opening_key) or 0.0) if partial else 0.0
        complete = (not partial or settings.get(opening_key) is not None) and missing < 1e-9 and missing_payments == 0
        balance = opening + (payments - actual if direction == "import" else actual - payments)
        status = "incomplete" if not complete else "credit" if balance > 0.005 else (
            "additional_payment" if direction == "import" else "repayment") if balance < -0.005 else "balanced"
        return {"balance": balance, "status": status, "advances": payments, "actual": actual,
                "cycle_start": start.isoformat(), "complete": complete,
                "opening_balance": opening, "scheduled_payments": True, "tracking_since": self.started}

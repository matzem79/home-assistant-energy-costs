"""Calendar, tariff and independent meter regressions without an HA runtime."""
from __future__ import annotations

from datetime import datetime
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1] / "custom_components/energy_costs"
spec = importlib.util.spec_from_file_location("ledger", ROOT / "ledger.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
Ledger, with_tariff = module.Ledger, module.with_tariff


def at(value):
    return datetime.fromisoformat(value).timestamp()


def tariff(day="2026-01-01", import_price=0.3, export_price=0.08, monthly_fee=31):
    return dict(valid_from=day, import_price=import_price, export_price=export_price, monthly_fee=monthly_fee)


class MeterTests(unittest.TestCase):
    def test_units(self):
        for value, unit, expected in ((1000, "Wh", 1), (123, "kWh", 123)):
            self.assertEqual(module.energy_value(SimpleNamespace(state=str(value), attributes={"unit_of_measurement": unit})), expected)

    def test_invalid_meter(self):
        for value, unit in (("unknown", "kWh"), ("unavailable", "Wh"), (-1, "Wh"), ("nan", "Wh"), ("inf", "kWh"), (1, "W")):
            self.assertIsNone(module.energy_value(SimpleNamespace(state=str(value), attributes={"unit_of_measurement": unit})))
        self.assertIsNone(module.energy_value(None))


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.ledger = Ledger("Europe/Berlin")
        self.begin = at("2026-11-01T00:00:00+01:00")
        self.history = [tariff()]

    def result(self, category, period="total", now=None):
        return self.ledger.result(category, period, now or self.begin + 3600, self.history)

    def test_no_charge_for_lifetime_initial_meter(self):
        self.ledger.observe("import", 50000, self.begin)
        self.assertEqual(self.result("import_cost")[0], 0)

    def test_import_export_separate(self):
        for direction in ("import", "export"):
            self.ledger.observe(direction, 100, self.begin)
        self.ledger.observe("import", 110, self.begin + 60)
        self.ledger.observe("export", 104, self.begin + 60)
        self.assertAlmostEqual(self.result("import_cost")[0], 3)
        self.assertAlmostEqual(self.result("export_revenue")[0], 0.32)
        self.assertEqual(self.result("import_energy")[0], 10)
        self.assertEqual(self.result("export_energy")[0], 4)

    def test_repeat_poll_does_not_add_twice(self):
        self.ledger.observe("import", 100, self.begin)
        self.ledger.observe("import", 110, self.begin + 60)
        self.ledger.observe("import", 110, self.begin + 120)
        self.assertEqual(self.result("import_energy")[0], 10)

    def test_tariff_boundary_and_day_month_split(self):
        begin = at("2026-10-31T23:00:00+01:00")
        end = at("2026-11-01T01:00:00+01:00")
        self.history = with_tariff(self.history, tariff("2026-11-01", import_price=0.5))
        self.ledger.observe("import", 100, begin)
        self.ledger.observe("import", 110, end)
        self.assertAlmostEqual(self.result("import_cost", now=end)[0], 4)
        self.assertAlmostEqual(self.result("import_cost", "day", end)[0], 2.5)
        self.assertAlmostEqual(self.result("import_cost", "month", end)[0], 2.5)

    def test_backdated_price_recalculates_only_affected_days(self):
        self.ledger.energy = {"2026-10-31": {"import": 10, "export": 1}, "2026-11-01": {"import": 10, "export": 1}}
        self.assertAlmostEqual(self.result("import_cost")[0], 6)
        self.history = with_tariff(self.history, tariff("2026-11-01", import_price=0.5))
        self.assertAlmostEqual(self.result("import_cost")[0], 8)
        self.assertAlmostEqual(self.result("export_revenue")[0], 0.16)

    def test_future_tariff_does_not_change_today(self):
        self.history = with_tariff(self.history, tariff("2026-12-01", import_price=0.8))
        self.ledger.energy = {"2026-11-01": {"import": 10, "export": 0}}
        self.assertAlmostEqual(self.result("import_cost")[0], 3)

    def test_negative_energy_tariff(self):
        self.history = [tariff(import_price=-0.1, export_price=-0.02)]
        self.ledger.energy = {"2026-11-01": {"import": 10, "export": 2}}
        self.assertAlmostEqual(self.result("import_cost")[0], -1)
        self.assertAlmostEqual(self.result("export_revenue")[0], -0.04)

    def test_reset_and_recovery(self):
        for now, value in ((0, 100), (60, 110), (120, None), (180, 112), (240, 0), (300, 2)):
            self.ledger.observe("import", value, self.begin + now)
        self.assertEqual(self.result("import_energy")[0], 14)
        self.assertEqual(self.ledger.resets["import"], 1)

    def test_restore_no_double_count(self):
        self.ledger.observe("import", 100, self.begin)
        self.ledger.observe("import", 110, self.begin + 60)
        restored = Ledger("Europe/Berlin")
        restored.restore(json.loads(json.dumps(self.ledger.dump())))
        restored.observe("import", 110, self.begin + 120)
        restored.observe("import", 111, self.begin + 180)
        self.assertAlmostEqual(restored.result("import_cost", "total", self.begin + 180, self.history)[0], 3.3)

    def test_full_month_standing_charge(self):
        self.ledger.started = at("2026-11-01T00:00:00+01:00")
        end = at("2026-12-01T00:00:00+01:00")
        self.assertAlmostEqual(self.result("standing_charge", now=end)[0], 31)
        self.assertEqual(self.result("standing_charge", "month", end)[0], 0)

    def test_partial_day_fee(self):
        self.ledger.started = self.begin
        self.assertAlmostEqual(self.result("standing_charge", now=self.begin + 43200)[0], 31 / 30 / 2)

    def test_fee_change_mid_month(self):
        self.ledger.started = self.begin
        self.history = with_tariff(self.history, tariff("2026-11-16", monthly_fee=62))
        self.assertAlmostEqual(self.result("standing_charge", now=at("2026-12-01T00:00:00+01:00"))[0], 46.5)

    def test_leap_month_fee(self):
        self.ledger.started = at("2028-02-01T00:00:00+01:00")
        end = at("2028-03-01T00:00:00+01:00")
        self.assertAlmostEqual(self.result("standing_charge", now=end)[0], 31)

    def test_dst_day_has_one_daily_fee(self):
        self.ledger.started = at("2026-10-25T00:00:00+02:00")
        end = at("2026-10-26T00:00:00+01:00")
        self.assertAlmostEqual(self.result("standing_charge", now=end)[0], 1)

    def test_missing_tariff_is_reported(self):
        self.ledger.started = self.begin
        self.ledger.energy = {"2026-11-01": {"import": 10, "export": 0}}
        self.history = []
        self.assertEqual(self.result("import_cost"), (0, 10))
        self.assertAlmostEqual(self.result("standing_charge", now=self.begin + 43200)[1], 0.5)

    def test_same_timestamp_energy(self):
        self.ledger.observe("import", 100, self.begin)
        self.ledger.observe("import", 101, self.begin)
        self.assertEqual(self.result("import_energy")[0], 1)


class TariffTests(unittest.TestCase):
    def test_insert_replace_and_sort(self):
        original = [tariff("2026-01-01"), tariff("2026-12-01")]
        changed = with_tariff(original, tariff("2026-06-01", import_price=0.4))
        self.assertEqual(len(original), 2)
        self.assertEqual([t["valid_from"] for t in changed], ["2026-01-01", "2026-06-01", "2026-12-01"])
        changed = with_tariff(changed, tariff("2026-06-01", import_price=0.5))
        self.assertEqual(len(changed), 3)
        self.assertEqual(changed[1]["import_price"], 0.5)

    def test_invalid_date_rejected(self):
        with self.assertRaises(ValueError):
            with_tariff([], tariff("2026-02-30"))


if __name__ == "__main__":
    unittest.main()

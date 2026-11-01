"""Independent annual balances and scheduled monthly advances."""
from __future__ import annotations

from datetime import date
import unittest

from test_ledger import Ledger, at, tariff


class SettlementTests(unittest.TestCase):
    def setUp(self):
        self.ledger = Ledger("Europe/Berlin")
        self.ledger.started = at("2026-11-01T00:00:00+01:00")
        rate = tariff("2026-01-01", monthly_fee=30)
        rate.update(monthly_import_payment=100, monthly_export_credit=50)
        self.settings = {"tariffs": [rate], "import_billing_start": "2026-11-01", "export_billing_start": "2026-11-01"}
        self.now = at("2026-11-16T00:00:00+01:00")

    def test_import_credit_includes_fee(self):
        self.ledger.energy = {"2026-11-01": {"import": 100, "export": 0}}
        result = self.ledger.settlement("import", self.now, self.settings)
        self.assertAlmostEqual(result["actual"], 45)
        self.assertEqual(result["advances"], 100)
        self.assertAlmostEqual(result["balance"], 55)
        self.assertEqual(result["status"], "credit")

    def test_import_additional_payment(self):
        self.ledger.energy = {"2026-11-01": {"import": 500, "export": 0}}
        result = self.ledger.settlement("import", self.now, self.settings)
        self.assertAlmostEqual(result["balance"], -65)
        self.assertEqual(result["status"], "additional_payment")

    def test_export_credit_and_repayment_independent_of_import(self):
        self.ledger.energy = {"2026-11-01": {"import": 10000, "export": 1000}}
        result = self.ledger.settlement("export", self.now, self.settings)
        self.assertAlmostEqual(result["balance"], 30)
        self.assertEqual(result["status"], "credit")
        self.ledger.energy["2026-11-01"]["export"] = 100
        result = self.ledger.settlement("export", self.now, self.settings)
        self.assertAlmostEqual(result["balance"], -42)
        self.assertEqual(result["status"], "repayment")

    def test_separate_billing_years(self):
        self.settings["import_billing_start"] = "2026-04-01"
        self.settings["export_billing_start"] = "2026-07-15"
        self.assertEqual(self.ledger.settlement("import", self.now, self.settings)["cycle_start"], "2026-04-01")
        self.assertEqual(self.ledger.settlement("export", self.now, self.settings)["cycle_start"], "2026-07-15")

    def test_partial_period_not_presented_as_complete(self):
        self.settings["import_billing_start"] = "2026-01-01"
        self.assertEqual(self.ledger.settlement("import", self.now, self.settings)["status"], "incomplete")
        self.settings["import_opening_balance"] = -20
        result = self.ledger.settlement("import", self.now, self.settings)
        self.assertTrue(result["complete"])
        self.assertAlmostEqual(result["balance"], 65)

    def test_cleared_opening_balance_is_not_a_known_zero(self):
        self.settings["import_billing_start"] = "2026-01-01"
        self.settings["import_opening_balance"] = None
        self.assertEqual(self.ledger.settlement("import", self.now, self.settings)["status"], "incomplete")

    def test_monthly_payments_booked_in_full_not_daily_prorated(self):
        self.assertEqual(self.ledger.settlement("import", self.now, self.settings)["advances"], 100)
        later = at("2026-12-01T00:00:00+01:00")
        self.assertEqual(self.ledger.settlement("import", later, self.settings)["advances"], 200)

    def test_payment_change_uses_rate_at_payment_date(self):
        rate = tariff("2026-12-01")
        rate.update(monthly_import_payment=120, monthly_export_credit=60)
        self.settings["tariffs"].append(rate)
        later = at("2026-12-01T00:00:00+01:00")
        self.assertEqual(self.ledger.settlement("import", later, self.settings)["advances"], 220)
        self.assertEqual(self.ledger.settlement("export", later, self.settings)["advances"], 110)

    def test_annual_rollover_does_not_carry_settled_opening_balance(self):
        self.settings["import_opening_balance"] = 100
        result = self.ledger.settlement("import", at("2027-11-01T00:00:00+01:00"), self.settings)
        self.assertEqual(result["cycle_start"], "2027-11-01")
        self.assertEqual(result["opening_balance"], 0)
        self.assertEqual(result["advances"], 100)
        self.assertAlmostEqual(result["actual"], 0)

    def test_end_of_month_payment_day_clamped(self):
        self.settings["import_billing_start"] = "2026-01-31"
        self.ledger.started = at("2026-01-31T00:00:00+01:00")
        self.assertEqual(self.ledger.settlement("import", at("2026-02-28T12:00:00+01:00"), self.settings)["advances"], 200)

    def test_export_credits_january_cycle_april_payments_110_to_80(self):
        self.ledger.started = at("2026-01-01T00:00:00+01:00")
        self.settings["export_billing_start"] = "2026-01-01"
        self.settings["tariffs"][0]["monthly_export_credit"] = 10
        self.ledger.energy = {"2026-02-01": {"import": 0, "export": 100},
                              "2026-04-01": {"import": 0, "export": 200}}
        self.assertEqual(self.ledger.settlement("export", self.now, self.settings)["advances"], 110)
        self.settings["export_payment_start"] = "2026-04-01"
        result = self.ledger.settlement("export", self.now, self.settings)
        self.assertEqual(result["advances"], 80)
        self.assertEqual(result["cycle_start"], "2026-01-01")
        self.assertEqual(result["actual"], 24)
        self.assertEqual(result["balance"], -56)
        self.assertEqual(len(result["payment_schedule"]), 8)
        self.assertEqual(result["payment_schedule"][0]["date"], "2026-04-01")
        self.assertEqual(result["payment_schedule"][-1]["date"], "2026-11-01")
        self.assertEqual(result["tariff_count"], 1)
        self.assertEqual(result["tariffs"], self.settings["tariffs"])
        self.assertEqual(self.ledger.settlement("import", self.now, self.settings)["advances"], 100)

    def test_export_payment_start_future_and_next_cycle(self):
        self.ledger.started = at("2026-01-01T00:00:00+01:00")
        self.settings["export_billing_start"] = "2026-01-01"
        self.settings["export_payment_start"] = "2026-12-01"
        self.assertEqual(self.ledger.settlement("export", self.now, self.settings)["advances"], 0)
        self.settings["export_payment_start"] = "2026-04-01"
        result = self.ledger.settlement("export", at("2027-02-01T00:00:00+01:00"), self.settings)
        self.assertEqual(result["advances"], 100)

    def test_two_tariffs_without_payment_start_count_80(self):
        self.ledger.started = at("2026-01-01T00:00:00+01:00")
        self.settings["export_billing_start"] = "2026-01-01"
        self.settings["tariffs"][0]["monthly_export_credit"] = 0
        april = dict(self.settings["tariffs"][0], valid_from="2026-04-01", monthly_export_credit=10)
        self.settings["tariffs"].append(april)
        self.assertEqual(self.ledger.settlement("export", self.now, self.settings)["advances"], 80)

    def test_leap_year_anniversary(self):
        self.assertEqual(Ledger.cycle_start("2024-02-29", date(2027, 3, 1)), date(2027, 2, 28))


if __name__ == "__main__":
    unittest.main()

"""Validate actual sensor setup, values, balances and reset metadata."""
from __future__ import annotations

import ast
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
import unittest

from test_ledger import Ledger, at, tariff


class FakeSensor:
    hass = None


moment = datetime.fromisoformat("2026-11-16T12:00:00+01:00")
ROOT = Path(__file__).resolve().parents[1] / "custom_components/energy_costs"
nodes = [n for n in ast.parse((ROOT / "sensor.py").read_text()).body if isinstance(n, (ast.ClassDef, ast.AsyncFunctionDef))]
namespace = {"SensorEntity": FakeSensor, "CATEGORIES": ("import_energy", "export_energy", "import_cost", "export_revenue", "standing_charge"),
             "PERIODS": ("day", "month", "year", "total"), "DOMAIN": "energy_costs",
             "SensorDeviceClass": SimpleNamespace(ENERGY="energy", MONETARY="monetary", ENUM="enum"),
             "SensorStateClass": SimpleNamespace(TOTAL="total"), "UnitOfEnergy": SimpleNamespace(KILO_WATT_HOUR="kWh"),
             "DeviceInfo": lambda **kwargs: kwargs, "DeviceEntryType": SimpleNamespace(SERVICE="service"),
             "dt_util": SimpleNamespace(now=lambda: moment, utcnow=lambda: moment,
                                        utc_from_timestamp=lambda stamp: datetime.fromtimestamp(stamp, timezone.utc))}
exec(compile(ast.Module(body=nodes, type_ignores=[]), "sensor.py", "exec"), namespace)


class SensorTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        ledger = Ledger("Europe/Berlin")
        ledger.started = at("2026-11-01T00:00:00+01:00")
        ledger.energy = {"2026-11-16": {"import": 10, "export": 5}}
        rate = tariff("2026-01-01")
        rate.update(monthly_import_payment=100, monthly_export_credit=50)
        self.runtime = SimpleNamespace(entry=SimpleNamespace(entry_id="one", title="Energy Costs"), ledger=ledger,
            source_available={"import": True, "export": True},
            settings={"currency": "EUR", "tariffs": [rate], "import_billing_start": "2026-11-01", "export_billing_start": "2026-11-01"})

    async def test_setup_produces_26_unique_entities(self):
        entities = []
        await namespace["async_setup_entry"](None, SimpleNamespace(runtime_data=self.runtime), entities.extend)
        self.assertEqual(len(entities), 26)
        self.assertEqual(len({e._attr_unique_id for e in entities}), 26)
        for entity in entities:
            self.assertIsNotNone(entity.native_value)
            self.assertIsInstance(entity.extra_state_attributes, dict)

    async def test_money_energy_and_status_units(self):
        sensor = namespace["EnergyCostSensor"]
        self.assertEqual(sensor(self.runtime, "import_cost", "total").native_value, 3)
        self.assertEqual(sensor(self.runtime, "export_revenue", "total").native_value, 0.4)
        self.assertEqual(sensor(self.runtime, "import_energy", "total")._attr_native_unit_of_measurement, "kWh")
        status = namespace["SettlementSensor"](self.runtime, "import", "status")
        self.assertIsNone(status._attr_native_unit_of_measurement)
        self.assertIsNone(status.last_reset)
        self.assertEqual(status.native_value, "credit")

    async def test_annual_calendar_and_partial_period_attributes(self):
        sensor = namespace["EnergyCostSensor"](self.runtime, "import_cost", "year")
        self.assertTrue(sensor.extra_state_attributes["period_complete"])
        self.assertEqual(sensor.last_reset.timestamp(), self.runtime.ledger.started)
        self.runtime.ledger.started += 3600
        self.assertFalse(sensor.extra_state_attributes["period_complete"])

    async def test_unknown_price_has_incomplete_cost_attribute(self):
        self.runtime.settings["tariffs"] = []
        sensor = namespace["EnergyCostSensor"](self.runtime, "import_cost", "total")
        self.assertFalse(sensor.extra_state_attributes["cost_complete"])
        self.assertEqual(sensor.extra_state_attributes["unpriced_energy_kwh"], 10)


if __name__ == "__main__":
    unittest.main()

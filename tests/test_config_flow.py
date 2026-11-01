"""Exercise the real UI flow using isolated HA boundary doubles."""
from __future__ import annotations

import ast
from datetime import date, datetime
from math import isfinite
from pathlib import Path
from types import SimpleNamespace
import unittest

from test_ledger import Ledger, with_tariff


class Marker:
    def __init__(self, key, **kwargs):
        self.key, self.kwargs = key, kwargs


class Selector:
    def __init__(self, config=None):
        self.config = config or {}
        step = self.config.get("step", 1)
        if step != "any" and float(step) < 0.001:
            raise ValueError("HA number selector requires step >= 0.001 or any")


class FakeFlow:
    def __init_subclass__(cls, **kwargs):
        pass

    def async_show_form(self, **kwargs):
        return dict(type="form", **kwargs)

    def async_create_entry(self, **kwargs):
        return dict(type="create_entry", **kwargs)

    async def async_set_unique_id(self, value):
        self.unique_id = value

    def _abort_if_unique_id_configured(self):
        pass


ROOT = Path(__file__).resolve().parents[1] / "custom_components/energy_costs"
nodes = [n for n in ast.parse((ROOT / "config_flow.py").read_text()).body if isinstance(n, (ast.ClassDef, ast.FunctionDef, ast.Assign))]
namespace = {"date": date, "isfinite": isfinite, "Ledger": Ledger, "with_tariff": with_tariff,
             "DOMAIN": "energy_costs", "callback": lambda f: f,
             "dt_util": SimpleNamespace(now=lambda: datetime(2026, 11, 1, 12)),
             "vol": SimpleNamespace(Required=Marker, Optional=Marker, Schema=lambda s: s),
             "selector": SimpleNamespace(EntitySelector=Selector, EntitySelectorConfig=dict,
                                         NumberSelector=Selector, NumberSelectorConfig=dict, DateSelector=Selector),
             "er": SimpleNamespace(async_get=lambda hass: SimpleNamespace(async_get=lambda entity_id: None)),
             "config_entries": SimpleNamespace(ConfigFlow=FakeFlow, OptionsFlow=FakeFlow)}
exec(compile(ast.Module(body=nodes, type_ignores=[]), "config_flow.py", "exec"), namespace)


class FlowTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.hass = SimpleNamespace(config=SimpleNamespace(currency="EUR"),
            states=SimpleNamespace(get=lambda key: SimpleNamespace(attributes={"unit_of_measurement": "kWh"}) if key in ("sensor.import", "sensor.export") else None))
        self.input = {"import_entity": "sensor.import", "export_entity": "sensor.export", "import_price": 0.30123,
                      "export_price": 0.08, "monthly_fee": 12, "monthly_import_payment": 100, "monthly_export_credit": 20,
                      "import_billing_start": "2026-01-01", "export_billing_start": "2026-06-01"}

    async def test_setup_form_includes_all_inputs(self):
        flow = namespace["EnergyCostsConfigFlow"]()
        flow.hass = self.hass
        result = await flow.async_step_user()
        fields = {m.key: value for m, value in result["data_schema"].items()}
        self.assertIn("monthly_import_payment", fields)
        self.assertIn("monthly_export_credit", fields)
        self.assertEqual(fields["import_price"].config["step"], "any")
        self.assertIn("import_opening_balance", fields)
        self.assertIn("valid_from", fields)

    async def test_setup_uses_today_if_date_omitted(self):
        flow = namespace["EnergyCostsConfigFlow"]()
        flow.hass = self.hass
        result = await flow.async_step_user(self.input)
        self.assertEqual(result["type"], "create_entry")
        self.assertEqual(result["data"]["tariffs"][0]["valid_from"], "2026-11-01")
        self.assertEqual(result["data"]["tariffs"][0]["import_price"], 0.30123)

    async def test_options_append_future_tariff_and_keep_previous(self):
        initial = namespace["updated_settings"]({}, self.input, "EUR")
        flow = namespace["EnergyCostsOptionsFlow"]()
        flow.hass = self.hass
        flow.config_entry = SimpleNamespace(data=initial, options={})
        result = await flow.async_step_init(dict(self.input, valid_from="2027-01-01", import_price=0.4))
        self.assertEqual(len(result["data"]["tariffs"]), 2)
        self.assertEqual(result["data"]["tariffs"][0]["import_price"], 0.30123)

    async def test_options_form_reopens_with_saved_values(self):
        initial = namespace["updated_settings"]({}, self.input, "EUR")
        flow = namespace["EnergyCostsOptionsFlow"]()
        flow.hass = self.hass
        flow.config_entry = SimpleNamespace(data=initial, options={})
        result = await flow.async_step_init()
        marker = next(m for m in result["data_schema"] if m.key == "import_price")
        self.assertEqual(marker.kwargs["default"], 0.30123)

    async def test_separate_sources_required(self):
        errors = namespace["validate_input"](self.hass, dict(self.input, export_entity="sensor.import"))
        self.assertEqual(errors["export_entity"], "same_source")

    async def test_negative_fee_rejected_but_negative_tariff_allowed(self):
        errors = namespace["validate_input"](self.hass, dict(self.input, monthly_fee=-1, import_price=-0.2))
        self.assertIn("monthly_fee", errors)
        self.assertNotIn("import_price", errors)

    async def test_bad_date_returns_field_error(self):
        errors = namespace["validate_input"](self.hass, dict(self.input, valid_from="2026-02-30"))
        self.assertEqual(errors["valid_from"], "invalid_date")

    async def test_opening_balance_can_be_cleared_on_reconfigure(self):
        initial = namespace["updated_settings"]({}, dict(self.input, import_opening_balance=50), "EUR")
        changed = namespace["updated_settings"](initial, self.input, "EUR")
        merged = {**initial, **changed}
        self.assertIsNone(merged["import_opening_balance"])

    async def test_payment_start_saved_shown_validated_and_clearable(self):
        values = dict(self.input, export_payment_start="2026-04-01")
        saved = namespace["updated_settings"]({}, values, "EUR")
        self.assertEqual(saved["export_payment_start"], "2026-04-01")
        fields = namespace["make_schema"](saved, "EUR")
        marker = next(m for m in fields if m.key == "export_payment_start")
        self.assertEqual(marker.kwargs["description"]["suggested_value"], "2026-04-01")
        self.assertIn("export_payment_start", namespace["validate_input"](self.hass, dict(values, export_payment_start="2026-02-30")))
        cleared = namespace["updated_settings"](saved, self.input, "EUR")
        self.assertIsNone(cleared["export_payment_start"])

    async def test_options_display_all_tariffs_and_count(self):
        initial = namespace["updated_settings"]({}, dict(self.input, valid_from="2026-01-01", monthly_export_credit=0), "EUR")
        current = namespace["updated_settings"](initial, dict(self.input, valid_from="2026-04-01", monthly_export_credit=10), "EUR")
        flow = namespace["EnergyCostsOptionsFlow"]()
        flow.hass = self.hass
        flow.config_entry = SimpleNamespace(data=initial, options=current)
        result = await flow.async_step_init()
        overview = result["description_placeholders"]
        self.assertEqual(overview["tariff_count"], "2")
        self.assertEqual(overview["currency"], "EUR")
        self.assertIn("2026-01-01", overview["tariff_rows"])
        self.assertIn("2026-04-01", overview["tariff_rows"])
        self.assertTrue(overview["tariff_rows"].splitlines()[0].endswith("| 0 |"))
        self.assertTrue(overview["tariff_rows"].splitlines()[1].endswith("| 10 |"))

    async def test_export_optional(self):
        values = dict(self.input)
        values.pop("export_entity")
        self.assertEqual(namespace["validate_input"](self.hass, values), {})


if __name__ == "__main__":
    unittest.main()

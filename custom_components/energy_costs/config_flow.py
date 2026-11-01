"""UI setup, meter selection and dated tariff updates."""
from __future__ import annotations

from datetime import date
from math import isfinite

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er, selector
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .ledger import Ledger, with_tariff


PRICE_KEYS = ("import_price", "export_price", "monthly_fee", "monthly_import_payment", "monthly_export_credit")


def make_schema(settings, currency):
    today = dt_util.now().date().isoformat()
    tariff = Ledger.tariff_on(settings.get("tariffs", []), today) or {}
    schema = {}
    for key in ("import_entity", "export_entity"):
        marker = vol.Required if key == "import_entity" else vol.Optional
        suggestion = {"suggested_value": settings[key]} if settings.get(key) else {}
        schema[marker(key, description=suggestion)] = selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor"))
    for key in PRICE_KEYS:
        schema[vol.Required(key, default=tariff.get(key, 0.0))] = selector.NumberSelector(selector.NumberSelectorConfig(
            min=0 if key not in ("import_price", "export_price") else -1000, max=10000, step="any", mode="box",
            unit_of_measurement=f"{currency}/month" if key not in ("import_price", "export_price") else f"{currency}/kWh"))
    schema[vol.Optional("valid_from", description={"suggested_value": today})] = selector.DateSelector()
    for direction in ("import", "export"):
        key = f"{direction}_billing_start"
        schema[vol.Required(key, default=settings.get(key, f"{dt_util.now().year}-01-01"))] = selector.DateSelector()
        key = f"{direction}_opening_balance"
        schema[vol.Optional(key, description={"suggested_value": settings[key]} if settings.get(key) is not None else {})] = selector.NumberSelector(
            selector.NumberSelectorConfig(min=-1000000, max=1000000, step="any", mode="box", unit_of_measurement=currency))
    schema[vol.Optional("export_payment_start", description={"suggested_value": settings["export_payment_start"]}
                        if settings.get("export_payment_start") else {})] = selector.DateSelector()
    schema[vol.Optional("import_history", default=settings.get("import_history", False))] = bool
    return vol.Schema(schema)


def validate_input(hass, user_input):
    errors = {}
    registry = er.async_get(hass)
    for key in ("import_entity", "export_entity"):
        entity_id = user_input.get(key)
        if not entity_id:
            if key == "import_entity":
                errors[key] = "invalid_source"
            continue
        state = hass.states.get(entity_id)
        record = registry.async_get(entity_id)
        if state is None or state.attributes.get("unit_of_measurement") not in ("Wh", "kWh") or (record and record.platform == DOMAIN):
            errors[key] = "invalid_source"
    if user_input.get("export_entity") == user_input.get("import_entity"):
        errors["export_entity"] = "same_source"
    for key in PRICE_KEYS:
        value = user_input.get(key)
        if not isinstance(value, (float, int)) or not isfinite(value) or (key not in ("import_price", "export_price") and value < 0):
            errors[key] = "invalid_price"
    for key in ("valid_from", "import_billing_start", "export_billing_start", "export_payment_start"):
        if user_input.get(key):
            try:
                date.fromisoformat(user_input[key])
            except (TypeError, ValueError):
                errors[key] = "invalid_date"
    for direction in ("import", "export"):
        key = f"{direction}_opening_balance"
        if user_input.get(key) is not None and (not isinstance(user_input[key], (float, int)) or not isfinite(user_input[key])):
            errors[key] = "invalid_price"
    return errors


def updated_settings(previous, user_input, currency):
    effective = user_input.get("valid_from") or dt_util.now().date().isoformat()
    tariff = {key: float(user_input[key]) for key in PRICE_KEYS}
    tariff["valid_from"] = effective
    result = {"import_entity": user_input["import_entity"], "export_entity": user_input.get("export_entity"),
              "currency": previous.get("currency", currency),
              "import_history": user_input.get("import_history", previous.get("import_history", False)),
              "export_payment_start": user_input.get("export_payment_start") or None,
              "tariffs": with_tariff(previous.get("tariffs", []), tariff)}
    for direction in ("import", "export"):
        key = f"{direction}_billing_start"
        result[key] = user_input.get(key, previous.get(key, f"{dt_util.now().year}-01-01"))
        key = f"{direction}_opening_balance"
        result[key] = float(user_input[key]) if user_input.get(key) is not None else None
    return result


def tariff_overview(settings):
    """Expose every saved tariff in the options form, in a fixed column order."""
    history = sorted(settings.get("tariffs", []), key=lambda t: t["valid_from"])
    rows = [" | ".join([t["valid_from"], *(f"{t.get(k, 0):g}" for k in PRICE_KEYS)]) for t in history]
    return {"tariff_count": str(len(history)), "currency": settings["currency"],
            "tariff_rows": "\n".join("| " + row + " |" for row in rows) or "| — | — | — | — | — | — |"}


class EnergyCostsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return EnergyCostsOptionsFlow()

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            errors = validate_input(self.hass, user_input)
            if not errors:
                await self.async_set_unique_id(f"{user_input['import_entity']}|{user_input.get('export_entity') or ''}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title="Energy Costs", data=updated_settings({}, user_input, self.hass.config.currency))
        return self.async_show_form(step_id="user", data_schema=make_schema({}, self.hass.config.currency), errors=errors)


class EnergyCostsOptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        current = {**self.config_entry.data, **self.config_entry.options}
        errors = {}
        if user_input is not None:
            errors = validate_input(self.hass, user_input)
            if not errors:
                return self.async_create_entry(title="", data=updated_settings(current, user_input, current["currency"]))
        return self.async_show_form(step_id="init", data_schema=make_schema(current, current["currency"]), errors=errors,
                                    description_placeholders=tariff_overview(current))

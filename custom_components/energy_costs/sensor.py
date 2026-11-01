"""Separate import cost, export revenue, energy and standing-charge sensors."""
from __future__ import annotations

from datetime import date

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import UnitOfEnergy
from homeassistant.helpers.device_registry import DeviceInfo, DeviceEntryType
from homeassistant.util import dt as dt_util

from .const import CATEGORIES, DOMAIN, PERIODS


async def async_setup_entry(hass, entry, async_add_entities):
    runtime = entry.runtime_data
    runtime.entities = [EnergyCostSensor(runtime, category, period) for category in CATEGORIES for period in PERIODS]
    runtime.entities.extend(SettlementSensor(runtime, direction, kind)
                            for direction in ("import", "export")
                            for kind in ("advances", "balance", "status"))
    async_add_entities(runtime.entities)


class EnergyCostSensor(SensorEntity):
    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.TOTAL

    def __init__(self, runtime, category, period):
        self.runtime, self.category, self.period = runtime, category, period
        self._attr_unique_id = f"{runtime.entry.entry_id}_{category}_{period}"
        self._attr_translation_key = f"{category}_{period}"
        energy = category.endswith("energy")
        self._attr_device_class = SensorDeviceClass.ENERGY if energy else SensorDeviceClass.MONETARY
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR if energy else runtime.settings["currency"]
        self._attr_suggested_display_precision = 3 if energy else 2
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, runtime.entry.entry_id)},
            name=runtime.entry.title, manufacturer="Energy Costs", entry_type=DeviceEntryType.SERVICE)

    @property
    def cycle_start(self):
        direction = "export" if self.category.startswith("export") else "import"
        return self.runtime.ledger.cycle_start(self.runtime.settings[f"{direction}_billing_start"], dt_util.now().date())

    @property
    def native_value(self):
        value, _ = self.runtime.ledger.result(self.category, self.period, dt_util.utcnow().timestamp(), self.runtime.settings["tariffs"], since=self.cycle_start.isoformat() if self.period == "year" else None)
        return round(value, 6)

    @property
    def last_reset(self):
        now = dt_util.now()
        if self.period == "day":
            return now.replace(hour=0, minute=0, second=0, microsecond=0)
        if self.period == "month":
            return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if self.period == "year":
            return dt_util.utc_from_timestamp(self.runtime.ledger.midnight(self.cycle_start))
        return None

    @property
    def extra_state_attributes(self):
        _, missing = self.runtime.ledger.result(self.category, self.period, dt_util.utcnow().timestamp(), self.runtime.settings["tariffs"], since=self.cycle_start.isoformat() if self.period == "year" else None)
        direction = "import" if self.category.startswith("import") else "export"
        now = dt_util.now()
        boundary = self.cycle_start if self.period == "year" else now.date().replace(day=1) if self.period == "month" else now.date()
        direction = "import" if self.category == "standing_charge" else direction
        started = self.runtime.ledger.tracking_since(direction)
        complete = self.runtime.ledger.history_complete(direction) and started is not None and (
            self.period == "total" or started <= self.runtime.ledger.midnight(boundary))
        return {"period_complete": complete, ("unpriced_days" if self.category == "standing_charge" else "unpriced_energy_kwh"): round(missing, 6), "cost_complete": missing < 1e-9,
                "source_available": self.runtime.source_available.get(direction) if self.category != "standing_charge" else None,
                "counter_resets": self.runtime.ledger.resets.get(direction) if self.category != "standing_charge" else None,
                "tracking_since": dt_util.utc_from_timestamp(started).isoformat() if started is not None else None,
                "history_import": self.runtime.ledger.history.get(direction)}


class SettlementSensor(EnergyCostSensor):
    """Separate advances, balance and status for each annual settlement."""

    def __init__(self, runtime, direction, kind):
        super().__init__(runtime, f"{direction}_{kind}", "year")
        self.direction, self.kind = direction, kind
        if kind == "status":
            self._attr_device_class = SensorDeviceClass.ENUM
            self._attr_state_class = None
            self._attr_native_unit_of_measurement = None
            self._attr_suggested_display_precision = None
            self._attr_options = ["credit", "additional_payment", "repayment", "balanced", "incomplete"]

    @property
    def native_value(self):
        info = self.runtime.ledger.settlement(self.direction, dt_util.utcnow().timestamp(), self.runtime.settings)
        return info["status"] if self.kind == "status" else round(info[self.kind], 6)

    @property
    def last_reset(self):
        return None if self.kind == "status" else super().last_reset

    @property
    def extra_state_attributes(self):
        return self.runtime.ledger.settlement(self.direction, dt_util.utcnow().timestamp(), self.runtime.settings)

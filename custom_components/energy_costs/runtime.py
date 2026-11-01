"""Observe selected meters and persist independent cost accounting."""
from __future__ import annotations

from datetime import timedelta

from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import callback
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .ledger import Ledger, energy_value


class Runtime:
    def __init__(self, hass, entry):
        self.hass, self.entry = hass, entry
        self.settings = {**entry.data, **entry.options}
        self.ledger = Ledger(hass.config.time_zone)
        self.store = Store(hass, 1, f"{DOMAIN}_{entry.entry_id}")
        self.entities = []
        self.listeners = []
        self.source_available = {"import": False, "export": False}

    async def load(self):
        saved = await self.store.async_load()
        if saved:
            self.ledger.restore(saved.get("ledger"))
            for direction in ("import", "export"):
                if saved.get("sources", {}).get(direction) != self.settings.get(f"{direction}_entity"):
                    self.ledger.last[direction] = None

    def snapshot(self):
        return {"ledger": self.ledger.dump(),
                "sources": {d: self.settings.get(f"{d}_entity") for d in ("import", "export")}}

    async def save(self, event=None):
        await self.store.async_save(self.snapshot())

    def start(self):
        ids = [self.settings[k] for k in ("import_entity", "export_entity") if self.settings.get(k)]
        self.listeners.append(async_track_state_change_event(self.hass, ids, self.changed))
        self.listeners.append(async_track_time_interval(self.hass, self.changed, timedelta(minutes=1)))
        self.listeners.append(self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, self.save))
        self.entry.async_on_unload(self.stop)
        self.changed()

    @callback
    def stop(self):
        for remove in self.listeners:
            remove()
        self.listeners.clear()

    @callback
    def changed(self, event=None):
        now = dt_util.utcnow().timestamp()
        for direction in ("import", "export"):
            entity_id = self.settings.get(f"{direction}_entity")
            state = self.hass.states.get(entity_id) if entity_id else None
            value = energy_value(state)
            self.source_available[direction] = value is not None
            self.ledger.observe(direction, value, now)
        self.store.async_delay_save(self.snapshot, 5)
        for entity in self.entities:
            if entity.hass is not None:
                entity.async_write_ha_state()

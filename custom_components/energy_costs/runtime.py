"""Observe selected meters and persist independent cost accounting."""
from __future__ import annotations

from datetime import date, timedelta
import logging

from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import callback
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .ledger import Ledger, energy_value
from .history import reconstruct

_LOGGER = logging.getLogger(__name__)


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
                    self.ledger.history.pop(direction, None)

        if self.settings.get("import_history"):
            await self.import_history()

    async def import_history(self):
        # Recorder owns the database executor. Never query it on the event loop.
        try:
            from homeassistant.components.recorder import get_instance
            from homeassistant.components.recorder.statistics import statistics_during_period
            recorder = get_instance(self.hass)
            if not await recorder.async_db_ready:
                raise KeyError("Recorder database unavailable")
        except Exception:
            _LOGGER.warning("Historical energy import requires an available Recorder database")
            for direction in ("import", "export"):
                if self.settings.get(f"{direction}_entity"):
                    previous = self.ledger.history.get(direction, {})
                    self.ledger.history[direction] = dict(previous, status="unavailable", complete=False)
            return
        for direction in ("import", "export"):
            entity_id = self.settings.get(f"{direction}_entity")
            if not entity_id:
                continue
            begin = self.ledger.midnight(date.fromisoformat(self.settings[f"{direction}_billing_start"]))
            signature = [entity_id, begin]
            previous = self.ledger.history.get(direction, {})
            if previous.get("signature") == signature and previous.get("complete") and previous.get("version") == 2:
                continue
            now = dt_util.utcnow()
            if begin >= now.timestamp():
                continue
            try:
                rows = await recorder.async_add_executor_job(
                    statistics_during_period, self.hass,
                    dt_util.utc_from_timestamp(begin - timedelta(days=31).total_seconds()), now,
                    {entity_id}, "hour", {"energy": "kWh"}, {"sum", "state"})
                # Sample after the query so the live meter is never older than its statistics.
                now = dt_util.utcnow()
                current = energy_value(self.hass.states.get(entity_id))
                imported = reconstruct(self.hass.config.time_zone, direction,
                                       rows.get(entity_id, []), begin, now.timestamp(), current)
            except Exception:  # A history failure must not disable live accounting.
                self.ledger.history[direction] = dict(previous, status="error", complete=False)
                _LOGGER.exception("Unable to import energy history for %s", entity_id)
                continue
            if imported is None:
                self.ledger.history[direction] = dict(previous, status="unavailable", complete=False)
                _LOGGER.warning("No usable long-term energy statistics for %s", entity_id)
                continue
            # Replace this direction atomically, including today's live tail.
            for bucket in self.ledger.energy.values():
                bucket[direction] = 0.0
            for day, bucket in imported.energy.items():
                self.ledger.energy.setdefault(day, {"import": 0.0, "export": 0.0})[direction] = bucket[direction]
            self.ledger.last[direction] = imported.last[direction]
            self.ledger.history[direction] = dict(imported.history[direction], signature=signature)
        await self.save()

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

"""Independent household import/export energy costs."""
from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN
from .runtime import Runtime

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(hass, entry):
    runtime = Runtime(hass, entry)
    await runtime.load()
    entry.runtime_data = runtime
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    runtime.start()
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_reload_entry(hass, entry):
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass, entry):
    entry.runtime_data.stop()
    await entry.runtime_data.save()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

"""Diematic to MQTT custom integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .bridge import DiematicMqttBridge
from .const import DOMAIN


type BridgeStore = dict[str, DiematicMqttBridge]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    bridges: BridgeStore = hass.data.setdefault(DOMAIN, {})
    bridge = DiematicMqttBridge(entry.data)
    await hass.async_add_executor_job(bridge.start)
    bridges[entry.entry_id] = bridge
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    bridges: BridgeStore = hass.data[DOMAIN]
    bridge = bridges.pop(entry.entry_id)
    await hass.async_add_executor_job(bridge.stop)
    return True

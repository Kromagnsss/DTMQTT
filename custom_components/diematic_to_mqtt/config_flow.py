"""Config flow for Diematic to MQTT integration."""

from __future__ import annotations

import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME

from .const import (
    CONF_DISCOVERY_ENABLED,
    CONF_DISCOVERY_PREFIX,
    CONF_ENABLE_CIRCUIT_A,
    CONF_ENABLE_CIRCUIT_B,
    CONF_INTERFACE_ADDRESS,
    CONF_MODBUS_HOST,
    CONF_MODBUS_PORT,
    CONF_MQTT_CLIENT_ID,
    CONF_MQTT_HOST,
    CONF_MQTT_PASSWORD,
    CONF_MQTT_PORT,
    CONF_MQTT_TOPIC_PREFIX,
    CONF_MQTT_USERNAME,
    CONF_PERIOD,
    CONF_REGULATOR_ADDRESS,
    CONF_REGULATOR_TYPE,
    CONF_TIME_SYNC,
    CONF_TIMEZONE,
    DEFAULT_DISCOVERY_ENABLED,
    DEFAULT_DISCOVERY_PREFIX,
    DEFAULT_ENABLE_CIRCUIT_A,
    DEFAULT_ENABLE_CIRCUIT_B,
    DEFAULT_INTERFACE_ADDRESS,
    DEFAULT_MQTT_CLIENT_ID,
    DEFAULT_MQTT_HOST,
    DEFAULT_MQTT_PORT,
    DEFAULT_MQTT_TOPIC_PREFIX,
    DEFAULT_MODBUS_PORT,
    DEFAULT_NAME,
    DEFAULT_PERIOD,
    DEFAULT_REGULATOR_ADDRESS,
    DEFAULT_REGULATOR_TYPE,
    DEFAULT_TIME_SYNC,
    DOMAIN,
    REGULATOR_TYPES,
)

_LOGGER = logging.getLogger(__name__)


class DiematicFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    def _parse_address(value: str | int) -> int:
        if isinstance(value, int):
            return value
        return int(value.strip(), 0)

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            try:
                data = dict(user_input)
                data[CONF_REGULATOR_ADDRESS] = self._parse_address(data[CONF_REGULATOR_ADDRESS])
                data[CONF_INTERFACE_ADDRESS] = self._parse_address(data[CONF_INTERFACE_ADDRESS])
            except (TypeError, ValueError, KeyError):
                errors["base"] = "invalid_address"
            except Exception:  # defensive guard to avoid frontend 500
                _LOGGER.exception("Unexpected error while validating config flow input")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(data[CONF_MQTT_CLIENT_ID])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=data[CONF_NAME], data=data)


        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
                vol.Required(CONF_MODBUS_HOST): str,
                vol.Required(CONF_MODBUS_PORT, default=DEFAULT_MODBUS_PORT): int,
                vol.Required(CONF_REGULATOR_TYPE, default=DEFAULT_REGULATOR_TYPE): vol.In(REGULATOR_TYPES),
                vol.Required(CONF_REGULATOR_ADDRESS, default=hex(DEFAULT_REGULATOR_ADDRESS)): str,
                vol.Required(CONF_INTERFACE_ADDRESS, default=hex(DEFAULT_INTERFACE_ADDRESS)): str,
                vol.Required(CONF_PERIOD, default=DEFAULT_PERIOD): int,
                vol.Optional(CONF_TIMEZONE, default=""): str,
                vol.Required(CONF_TIME_SYNC, default=DEFAULT_TIME_SYNC): bool,
                vol.Required(CONF_ENABLE_CIRCUIT_A, default=DEFAULT_ENABLE_CIRCUIT_A): bool,
                vol.Required(CONF_ENABLE_CIRCUIT_B, default=DEFAULT_ENABLE_CIRCUIT_B): bool,
                vol.Required(CONF_MQTT_HOST, default=DEFAULT_MQTT_HOST): str,
                vol.Required(CONF_MQTT_PORT, default=DEFAULT_MQTT_PORT): int,
                vol.Optional(CONF_MQTT_USERNAME, default=""): str,
                vol.Optional(CONF_MQTT_PASSWORD, default=""): str,
                vol.Required(CONF_MQTT_CLIENT_ID, default=DEFAULT_MQTT_CLIENT_ID): str,
                vol.Required(CONF_MQTT_TOPIC_PREFIX, default=DEFAULT_MQTT_TOPIC_PREFIX): str,
                vol.Required(CONF_DISCOVERY_ENABLED, default=DEFAULT_DISCOVERY_ENABLED): bool,
                vol.Required(CONF_DISCOVERY_PREFIX, default=DEFAULT_DISCOVERY_PREFIX): str,
            }
        )
        try:
            return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
        except Exception:  # defensive guard to avoid frontend 500
            _LOGGER.exception("Unexpected error while building config flow form")
            return self.async_show_form(step_id="user", data_schema=schema, errors={"base": "unknown"})

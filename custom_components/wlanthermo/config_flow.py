"""Config flow for WLANThermo integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_DEVICE_NAME,
    CONF_TOPIC_PREFIX,
    DEFAULT_NAME,
    DEFAULT_TOPIC_PREFIX,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_DEVICE_NAME, default=DEFAULT_NAME): cv.string,
        vol.Required(CONF_TOPIC_PREFIX, default=DEFAULT_TOPIC_PREFIX): cv.string,
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for WLANThermo."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                # Set unique ID based on topic prefix
                await self.async_set_unique_id(user_input[CONF_TOPIC_PREFIX])
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=user_input[CONF_DEVICE_NAME],
                    data=user_input,
                )
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception in config flow")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> OptionsFlow:
        """Get the options flow for this handler."""
        return OptionsFlow(config_entry)


class OptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for WLANThermo."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        try:
            # Use options if set, otherwise fallback to data, then defaults
            current_name = self.config_entry.options.get(
                CONF_DEVICE_NAME,
                self.config_entry.data.get(CONF_DEVICE_NAME, DEFAULT_NAME)
            )
            current_topic = self.config_entry.options.get(
                CONF_TOPIC_PREFIX,
                self.config_entry.data.get(CONF_TOPIC_PREFIX, DEFAULT_TOPIC_PREFIX)
            )

            schema = vol.Schema(
                {
                    vol.Optional(CONF_DEVICE_NAME, default=current_name): cv.string,
                    vol.Optional(CONF_TOPIC_PREFIX, default=current_topic): cv.string,
                }
            )

            return self.async_show_form(step_id="init", data_schema=schema)
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception in options flow")
            return self.async_abort(reason="unknown")

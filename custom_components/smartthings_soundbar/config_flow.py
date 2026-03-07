"""Config flow for SmartThings Soundbar integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY, CONF_DEVICE_ID, CONF_NAME
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv

from .const import (
    CONF_MAX_VOLUME,
    CONF_SOURCE_MAP,
    DEFAULT_MAX_VOLUME,
    DEFAULT_NAME,
    DEFAULT_SOURCE_MAP,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Required(CONF_API_KEY): cv.string,
        vol.Required(CONF_DEVICE_ID): cv.string,
        vol.Optional(CONF_MAX_VOLUME, default=DEFAULT_MAX_VOLUME): cv.positive_int,
    }
)


class SmartThingsSoundbarConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SmartThings Soundbar."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate the API key and device ID
            try:
                # Here we could add validation by making a test API call
                # For now, we'll just accept the input
                pass
            except Exception as ex:
                _LOGGER.error("Validation error: %s", ex)
                errors["base"] = "cannot_connect"
            else:
                # Create a unique ID for the config entry
                await self.async_set_unique_id(
                    f"{DOMAIN}_{user_input[CONF_DEVICE_ID]}"
                )
                self._abort_if_unique_id_configured()

                # Add default source map to config
                user_input[CONF_SOURCE_MAP] = DEFAULT_SOURCE_MAP.copy()

                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_import(self, import_config: dict[str, Any]) -> FlowResult:
        """Handle import from configuration.yaml."""
        # Generate a unique ID for the imported config
        await self.async_set_unique_id(f"{DOMAIN}_{import_config[CONF_DEVICE_ID]}")
        self._abort_if_unique_id_configured()

        # Add default source map if not present
        if CONF_SOURCE_MAP not in import_config:
            import_config[CONF_SOURCE_MAP] = DEFAULT_SOURCE_MAP.copy()

        return self.async_create_entry(
            title=import_config.get(CONF_NAME, DEFAULT_NAME),
            data=import_config,
        )
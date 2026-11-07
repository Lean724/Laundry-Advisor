"""Config flow for Laundry Advisor."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import Platform
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_FORECAST_HOURS,
    CONF_HUMIDITY_SENSOR,
    CONF_LOAD_TYPE,
    CONF_TEMP_SENSOR,
    CONF_UPDATE_INTERVAL,
    CONF_WEATHER_ENTITY,
    CONF_WIND_SENSOR,
    DEFAULT_FORECAST_HOURS,
    DEFAULT_LOAD_TYPE,
    DEFAULT_UPDATE_INTERVAL_MINUTES,
    DOMAIN,
    LOAD_TYPES,
    MAX_FORECAST_HOURS,
    MAX_UPDATE_INTERVAL_MINUTES,
    MIN_FORECAST_HOURS,
    MIN_UPDATE_INTERVAL_MINUTES,
)


def _optional_entity_field(
    key: str,
    defaults: Mapping[str, Any],
) -> vol.Optional:
    """Create an optional Voluptuous key with suggested_value when present."""
    current = defaults.get(key)
    if current:
        return vol.Optional(key, description={"suggested_value": current})
    return vol.Optional(key)


def _schema(defaults: Mapping[str, Any] | None = None) -> vol.Schema:
    """Build the config/options schema."""
    defaults = defaults or {}
    weather_default = defaults.get(CONF_WEATHER_ENTITY)
    return vol.Schema(
        {
            vol.Required(
                CONF_WEATHER_ENTITY,
                default=(
                    weather_default if weather_default is not None else vol.UNDEFINED
                ),
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=Platform.WEATHER)
            ),
            vol.Required(
                CONF_FORECAST_HOURS,
                default=defaults.get(CONF_FORECAST_HOURS, DEFAULT_FORECAST_HOURS),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=MIN_FORECAST_HOURS,
                    max=MAX_FORECAST_HOURS,
                    step=1,
                    mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement="h",
                )
            ),
            vol.Required(
                CONF_UPDATE_INTERVAL,
                default=defaults.get(
                    CONF_UPDATE_INTERVAL,
                    DEFAULT_UPDATE_INTERVAL_MINUTES,
                ),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=MIN_UPDATE_INTERVAL_MINUTES,
                    max=MAX_UPDATE_INTERVAL_MINUTES,
                    step=5,
                    mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement="min",
                )
            ),
            vol.Required(
                CONF_LOAD_TYPE,
                default=defaults.get(CONF_LOAD_TYPE, DEFAULT_LOAD_TYPE),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=list(LOAD_TYPES),
                    translation_key=CONF_LOAD_TYPE,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            _optional_entity_field(
                CONF_TEMP_SENSOR,
                defaults,
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain=Platform.SENSOR,
                    device_class=SensorDeviceClass.TEMPERATURE,
                )
            ),
            _optional_entity_field(
                CONF_HUMIDITY_SENSOR,
                defaults,
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain=Platform.SENSOR,
                    device_class=SensorDeviceClass.HUMIDITY,
                )
            ),
            _optional_entity_field(
                CONF_WIND_SENSOR,
                defaults,
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain=Platform.SENSOR,
                )
            ),
        }
    )


class LaundryAdvisorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):  # type: ignore[call-arg]
    """Handle a config flow for Laundry Advisor."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            weather_entity = user_input[CONF_WEATHER_ENTITY]
            state = self.hass.states.get(weather_entity)
            if state is None or not weather_entity.startswith(f"{Platform.WEATHER}."):
                errors["base"] = "invalid_weather_entity"
            else:
                await self.async_set_unique_id(weather_entity)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=state.name or weather_entity,
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_schema(user_input),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> LaundryAdvisorOptionsFlow:
        """Create the options flow."""
        return LaundryAdvisorOptionsFlow(config_entry)


class LaundryAdvisorOptionsFlow(config_entries.OptionsFlow):
    """Handle Laundry Advisor options."""

    def __init__(
        self,
        config_entry: config_entries.ConfigEntry | None = None,
    ) -> None:
        """Initialize the options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Manage integration options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            weather_entity = user_input[CONF_WEATHER_ENTITY]
            state = self.hass.states.get(weather_entity)
            if state is None or not weather_entity.startswith(f"{Platform.WEATHER}."):
                errors["base"] = "invalid_weather_entity"
            else:
                return self.async_create_entry(title="", data=user_input)

        entry = self._config_entry or self.config_entry
        defaults = {**entry.data, **entry.options}
        return self.async_show_form(
            step_id="init",
            data_schema=_schema(user_input or defaults),
            errors=errors,
        )

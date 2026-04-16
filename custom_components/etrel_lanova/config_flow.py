"""Config flow for the Etrel Lanova integration."""

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import callback

from .const import CONF_PORT_WRITE, DEFAULT_HOST, DEFAULT_PORT, DEFAULT_PORT_WRITE, DOMAIN
from .modbus_client import EtrelModbusClient

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Required(CONF_PORT_WRITE, default=DEFAULT_PORT_WRITE): int,
    }
)


class EtrelLanovaConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the setup flow via the UI."""

    VERSION = 1

    async def async_step_user(self, user_input=None) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input[CONF_PORT]

            # Prevent duplicate entries for the same host
            await self.async_set_unique_id(f"{host}:{port}")
            self._abort_if_unique_id_configured()

            # Test the connection
            can_connect = await self.hass.async_add_executor_job(
                self._test_connection, host, port
            )
            if can_connect:
                return self.async_create_entry(
                    title=f"Etrel Lanova ({host})",
                    data=user_input,
                )
            errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_SCHEMA,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return EtrelLanovaOptionsFlow(config_entry)

    @staticmethod
    def _test_connection(host: str, port: int) -> bool:
        """Try to establish a Modbus connection (blocking, runs in executor)."""
        client = EtrelModbusClient(host=host, port=port)
        try:
            return client.connect()
        finally:
            client.disconnect()


class EtrelLanovaOptionsFlow(OptionsFlow):
    """Allow changing host and ports after initial setup."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input[CONF_PORT]

            can_connect = await self.hass.async_add_executor_job(
                EtrelLanovaConfigFlow._test_connection, host, port
            )
            if can_connect:
                self.hass.config_entries.async_update_entry(
                    self._config_entry, data=user_input
                )
                return self.async_create_entry(title="", data={})
            errors["base"] = "cannot_connect"

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=self._config_entry.data.get(CONF_HOST, DEFAULT_HOST)): str,
                vol.Required(CONF_PORT, default=self._config_entry.data.get(CONF_PORT, DEFAULT_PORT)): int,
                vol.Required(CONF_PORT_WRITE, default=self._config_entry.data.get(CONF_PORT_WRITE, DEFAULT_PORT_WRITE)): int,
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            errors=errors,
        )

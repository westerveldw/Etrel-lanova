"""Config flow for the Etrel Lanova integration."""

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST

from .const import DEFAULT_HOST, DEFAULT_PORT, DOMAIN
from .modbus_client import EtrelModbusClient

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
    }
)


class EtrelLanovaConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the setup flow via the UI."""

    VERSION = 1

    async def async_step_user(self, user_input=None) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]

            await self.async_set_unique_id(host)
            self._abort_if_unique_id_configured()

            can_connect = await self._test_connection(host, DEFAULT_PORT)
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
    async def _test_connection(host: str, port: int) -> bool:
        client = EtrelModbusClient(host=host, port=port)
        try:
            return await client.connect()
        finally:
            client.disconnect()


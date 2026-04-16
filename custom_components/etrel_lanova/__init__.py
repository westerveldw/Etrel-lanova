"""Etrel Lanova Home Assistant integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant

from .const import DEFAULT_PORT, DEFAULT_PORT_WRITE, DOMAIN
from .coordinator import EtrelCoordinator
from .modbus_client import EtrelModbusClient

PLATFORMS = [Platform.SENSOR, Platform.NUMBER]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the integration from a config entry."""
    host = entry.data[CONF_HOST]

    read_client = EtrelModbusClient(host=host, port=DEFAULT_PORT)
    write_client = EtrelModbusClient(host=host, port=DEFAULT_PORT_WRITE)

    coordinator = EtrelCoordinator(hass, entry, read_client, write_client)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload the config entry and close connections."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: EtrelCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await hass.async_add_executor_job(coordinator.read_client.disconnect)
        await hass.async_add_executor_job(coordinator.write_client.disconnect)
    return unload_ok

"""Button entity for stopping charging."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import EtrelCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: EtrelCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([EtrelStopChargingButton(coordinator)])


class EtrelStopChargingButton(ButtonEntity):
    """Button that sets the cluster limit to 0 to stop charging."""

    _attr_has_entity_name = True
    _attr_translation_key = "stop_charging"
    _attr_icon = "mdi:pause"

    def __init__(self, coordinator: EtrelCoordinator) -> None:
        self._coordinator = coordinator
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_stop_charging"
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.config_entry.entry_id)},
            name="Etrel Lanova",
            manufacturer="Etrel",
            model="Lanova",
        )

    async def async_press(self) -> None:
        await self._coordinator.write_client.write_cluster_limit(0.0)
        await self._coordinator.async_request_refresh()

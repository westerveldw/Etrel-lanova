"""Switch entity for enabling/disabling charging."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import EtrelCoordinator

RESUME_CURRENT = 6.0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: EtrelCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([EtrelChargingSwitch(coordinator)])


class EtrelChargingSwitch(CoordinatorEntity[EtrelCoordinator], SwitchEntity):
    """Switch to enable or disable charging via the cluster limit."""

    _attr_has_entity_name = True
    _attr_translation_key = "charging_enabled"

    def __init__(self, coordinator: EtrelCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_charging_enabled"
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.config_entry.entry_id)},
            name="Etrel Lanova",
            manufacturer="Etrel",
            model="Lanova",
        )

    @property
    def is_on(self) -> bool | None:
        if self.coordinator.data is None:
            return None
        limit = self.coordinator.data.cluster_limit_l1
        return limit is not None and limit > 0

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.write_client.write_cluster_limit(RESUME_CURRENT)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.write_client.write_cluster_limit(0.0)
        await self.coordinator.async_request_refresh()

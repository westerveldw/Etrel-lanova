"""Number entity for setting the cluster limit."""

from __future__ import annotations

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfElectricCurrent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import EtrelCoordinator

MIN_CURRENT = 0.0   # A  (0 = stop charging)
MAX_CURRENT = 32.0  # A  (adjust to match your installation)
STEP = 1.0          # A


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: EtrelCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([EtrelClusterLimit(coordinator)])


class EtrelClusterLimit(CoordinatorEntity[EtrelCoordinator], NumberEntity):
    """Adjustable cluster limit (all phases simultaneously)."""

    _attr_has_entity_name = True
    _attr_translation_key = "cluster_limit"
    _attr_native_min_value = MIN_CURRENT
    _attr_native_max_value = MAX_CURRENT
    _attr_native_step = STEP
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
    _attr_device_class = NumberDeviceClass.CURRENT
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: EtrelCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_cluster_limit"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.config_entry.entry_id)},
            name="Etrel Lanova",
            manufacturer="Etrel",
            model="Lanova",
        )

    @property
    def native_value(self) -> float | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.cluster_limit_l1

    async def async_set_native_value(self, value: float) -> None:
        """Write the new limit to the charger and refresh the coordinator.

        Valid values: 0 (stop charging) or 6–32 A.
        Values between 0 and 6 are snapped up to 6.
        """
        if 0 < value < 6:
            value = 6.0

        await self.hass.async_add_executor_job(
            self.coordinator.write_client.write_cluster_limit, value
        )
        await self.coordinator.async_request_refresh()

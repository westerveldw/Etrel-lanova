"""DataUpdateCoordinator for the Etrel Lanova charger."""

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN
from .modbus_client import ChargerState, EtrelModbusClient

_LOGGER = logging.getLogger(__name__)


class EtrelCoordinator(DataUpdateCoordinator[ChargerState]):
    """Fetches all data every SCAN_INTERVAL seconds via Modbus.

    read_client  (port 502) — measurements: status, current, voltage, power
    write_client (port 503) — cluster limits: read and write
    """

    def __init__(
        self,
        hass: HomeAssistant,
        entry,
        read_client: EtrelModbusClient,
        write_client: EtrelModbusClient,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
            config_entry=entry,
        )
        self.read_client = read_client
        self.write_client = write_client

    async def _async_update_data(self) -> ChargerState:
        # Read measurements from port 502
        state = await self.hass.async_add_executor_job(self.read_client.read_all)
        if state is None:
            raise UpdateFailed("No Modbus connection to the charger (port 502)")

        # Read cluster limits from port 503 (overwrite the port 502 values)
        cl1 = await self.hass.async_add_executor_job(self.write_client.read_cluster_limit_l1)
        cl2 = await self.hass.async_add_executor_job(self.write_client.read_cluster_limit_l2)
        cl3 = await self.hass.async_add_executor_job(self.write_client.read_cluster_limit_l3)
        state.cluster_limit_l1 = cl1
        state.cluster_limit_l2 = cl2
        state.cluster_limit_l3 = cl3

        return state

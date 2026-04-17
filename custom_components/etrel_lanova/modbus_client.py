"""
Etrel Lanova charger - Modbus TCP client.

Register map (Etrel Lanova protocol):

  Input Registers (FC4, read-only):
    0        Status          uint16   See STATUS_MAP
    2-3      EV max current  float32  A
    6-7      Frequency       float32  Hz
    8-9      Voltage L1      float32  V
    10-11    Voltage L2      float32  V
    12-13    Voltage L3      float32  V
    14-15    Current L1      float32  A
    16-17    Current L2      float32  A
    18-19    Current L3      float32  A
    20-21    Power L1        float32  kW
    22-23    Power L2        float32  kW
    24-25    Power L3        float32  kW
    28-29    Power factor    float32  -
    30-31    Session energy  float32  kWh

  Holding Registers (FC3/FC16, read/write):
    4-5      Target current    float32  A   (direct per-charger limit)
    2000-01  Cluster limit L1  float32  A   (LoadGuard / group control)
    2002-03  Cluster limit L2  float32  A
    2004-05  Cluster limit L3  float32  A
"""

import struct
from dataclasses import dataclass
from typing import Optional

from pymodbus.client import AsyncModbusTcpClient

# ---------------------------------------------------------------------------
# Default connection settings
# ---------------------------------------------------------------------------

DEFAULT_HOST = "192.168.2.139"
DEFAULT_PORT = 502
DEFAULT_TIMEOUT = 3

# ---------------------------------------------------------------------------
# Register addresses
# ---------------------------------------------------------------------------

# Input registers (read-only, FC4)
REG_STATUS = 0
REG_EV_MAX_CURRENT = 2
REG_FREQUENCY = 6
REG_VOLTAGE_L1 = 8
REG_VOLTAGE_L2 = 10
REG_VOLTAGE_L3 = 12
REG_CURRENT_L1 = 14
REG_CURRENT_L2 = 16
REG_CURRENT_L3 = 18
REG_POWER_L1 = 20
REG_POWER_L2 = 22
REG_POWER_L3 = 24
REG_POWER_FACTOR = 28
REG_SESSION_ENERGY = 30
REG_DEPARTURE_TIME = 38
REG_EV_BATTERY_PCT = 46
REG_FW_MAJOR = 49
REG_FW_MINOR = 52
REG_FW_PATCH = 53

# Holding registers (read/write, FC3/FC16)
REG_TARGET_CURRENT = 4
REG_CLUSTER_LIMIT_L1 = 2000
REG_CLUSTER_LIMIT_L2 = 2002
REG_CLUSTER_LIMIT_L3 = 2004

# ---------------------------------------------------------------------------
# Status descriptions
# ---------------------------------------------------------------------------

STATUS_MAP: dict[int, str] = {
    # Based on OCPP 1.6 status values, but Etrel deviates on two points:
    #   4 (SuspendedEV) — per OCPP: EV paused, but this charger uses it
    #                     to mean "actively charging"
    #   6 (Faulted)     — per OCPP: fault, but this charger uses it
    #                     to mean "charging suspended" (cluster limit at 0A)
    0: "available",
    1: "preparing",
    2: "charging",
    3: "suspended_evse",
    4: "charging",
    5: "finishing",
    6: "suspended",
    7: "unavailable",
    8: "reserved",
}

# ---------------------------------------------------------------------------
# Dataclass for a full charger reading
# ---------------------------------------------------------------------------


@dataclass
class ChargerState:
    status: int
    status_text: str
    ev_max_current: Optional[float]
    frequency: Optional[float]
    voltage_l1: Optional[float]
    voltage_l2: Optional[float]
    voltage_l3: Optional[float]
    current_l1: Optional[float]
    current_l2: Optional[float]
    current_l3: Optional[float]
    power_l1: Optional[float]
    power_l2: Optional[float]
    power_l3: Optional[float]
    power_total: Optional[float]
    power_factor: Optional[float]
    session_energy: Optional[float]
    departure_time: Optional[int]
    ev_battery_pct: Optional[float]
    firmware_version: Optional[str]
    cluster_limit_l1: Optional[float]
    cluster_limit_l2: Optional[float]
    cluster_limit_l3: Optional[float]


# ---------------------------------------------------------------------------
# Client class
# ---------------------------------------------------------------------------


class EtrelModbusClient:
    """Async Modbus TCP client for the Etrel Lanova charger."""

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        self.host = host
        self.port = port
        self._client = AsyncModbusTcpClient(host, port=port, timeout=timeout)

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    async def connect(self) -> bool:
        return await self._client.connect()

    def disconnect(self) -> None:
        self._client.close()

    def is_connected(self) -> bool:
        return self._client.connected

    async def ensure_connected(self) -> bool:
        if not self.is_connected():
            return await self.connect()
        return True

    # ------------------------------------------------------------------
    # Register read helpers
    # ------------------------------------------------------------------

    async def _read_float_ir(self, address: int) -> Optional[float]:
        r = await self._client.read_input_registers(address=address, count=2)
        if r.isError():
            return None
        raw = struct.pack(">HH", r.registers[0], r.registers[1])
        return struct.unpack(">f", raw)[0]

    async def _read_uint16_ir(self, address: int) -> Optional[int]:
        r = await self._client.read_input_registers(address=address, count=1)
        if r.isError():
            return None
        return r.registers[0]

    async def _read_uint32_ir(self, address: int) -> Optional[int]:
        r = await self._client.read_input_registers(address=address, count=2)
        if r.isError():
            return None
        raw = struct.pack(">HH", r.registers[0], r.registers[1])
        return struct.unpack(">I", raw)[0]

    async def _read_float_hr(self, address: int) -> Optional[float]:
        r = await self._client.read_holding_registers(address=address, count=2)
        if r.isError():
            return None
        raw = struct.pack(">HH", r.registers[0], r.registers[1])
        return struct.unpack(">f", raw)[0]

    async def _write_float_hr(self, address: int, value: float) -> bool:
        raw = struct.pack(">f", float(value))
        hi, lo = struct.unpack(">HH", raw)
        r = await self._client.write_registers(address=address, values=[hi, lo])
        return not r.isError()

    # ------------------------------------------------------------------
    # Write methods
    # ------------------------------------------------------------------

    async def write_cluster_limit(self, ampere: float) -> bool:
        ok1 = await self._write_float_hr(REG_CLUSTER_LIMIT_L1, ampere)
        ok2 = await self._write_float_hr(REG_CLUSTER_LIMIT_L2, ampere)
        ok3 = await self._write_float_hr(REG_CLUSTER_LIMIT_L3, ampere)
        return ok1 and ok2 and ok3

    # ------------------------------------------------------------------
    # Full read in one call
    # ------------------------------------------------------------------

    async def read_all(self) -> Optional[ChargerState]:
        """Read all registers and return a ChargerState, or None on failure."""
        if not await self.ensure_connected():
            return None

        status = await self._read_uint16_ir(REG_STATUS) or 0
        p1 = await self._read_float_ir(REG_POWER_L1)
        p2 = await self._read_float_ir(REG_POWER_L2)
        p3 = await self._read_float_ir(REG_POWER_L3)
        power_total = round((p1 or 0.0) + (p2 or 0.0) + (p3 or 0.0), 3)

        major = await self._read_uint16_ir(REG_FW_MAJOR)
        minor = await self._read_uint16_ir(REG_FW_MINOR)
        patch = await self._read_uint16_ir(REG_FW_PATCH)
        if None not in (major, minor, patch):
            firmware = f"{major}.{minor}.{patch}"
        else:
            firmware = None

        return ChargerState(
            status=status,
            status_text=STATUS_MAP.get(status, "Unknown"),
            ev_max_current=await self._read_float_ir(REG_EV_MAX_CURRENT),
            frequency=await self._read_float_ir(REG_FREQUENCY),
            voltage_l1=await self._read_float_ir(REG_VOLTAGE_L1),
            voltage_l2=await self._read_float_ir(REG_VOLTAGE_L2),
            voltage_l3=await self._read_float_ir(REG_VOLTAGE_L3),
            current_l1=await self._read_float_ir(REG_CURRENT_L1),
            current_l2=await self._read_float_ir(REG_CURRENT_L2),
            current_l3=await self._read_float_ir(REG_CURRENT_L3),
            power_l1=p1,
            power_l2=p2,
            power_l3=p3,
            power_total=power_total,
            power_factor=await self._read_float_ir(REG_POWER_FACTOR),
            session_energy=await self._read_float_ir(REG_SESSION_ENERGY),
            departure_time=await self._read_uint32_ir(REG_DEPARTURE_TIME),
            ev_battery_pct=await self._read_float_ir(REG_EV_BATTERY_PCT),
            firmware_version=firmware,
            cluster_limit_l1=await self._read_float_hr(REG_CLUSTER_LIMIT_L1),
            cluster_limit_l2=await self._read_float_hr(REG_CLUSTER_LIMIT_L2),
            cluster_limit_l3=await self._read_float_hr(REG_CLUSTER_LIMIT_L3),
        )

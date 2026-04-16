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

from pymodbus.client import ModbusTcpClient

# ---------------------------------------------------------------------------
# Default connection settings
# ---------------------------------------------------------------------------

DEFAULT_HOST = "192.168.2.139"
DEFAULT_PORT = 502          # Etrel Lanova port
DEFAULT_TIMEOUT = 3         # seconds

# ---------------------------------------------------------------------------
# Register addresses
# ---------------------------------------------------------------------------

# Input registers (read-only, FC4)
REG_STATUS          = 0
REG_EV_MAX_CURRENT  = 2
REG_FREQUENCY       = 6
REG_VOLTAGE_L1      = 8
REG_VOLTAGE_L2      = 10
REG_VOLTAGE_L3      = 12
REG_CURRENT_L1      = 14
REG_CURRENT_L2      = 16
REG_CURRENT_L3      = 18
REG_POWER_L1        = 20
REG_POWER_L2        = 22
REG_POWER_L3        = 24
REG_POWER_FACTOR    = 28
REG_SESSION_ENERGY  = 30
REG_SESSION_DURATION = 32   # uint32, seconds
REG_DEPARTURE_TIME  = 38    # uint32, Unix timestamp
REG_EV_BATTERY_PCT  = 46    # float32, % (EV battery percentage)
REG_FW_MAJOR        = 49    # uint16
REG_FW_MINOR        = 52    # uint16
REG_FW_PATCH        = 53    # uint16

# Holding registers (read/write, FC3/FC16)
REG_TARGET_CURRENT      = 4       # direct target current
REG_CLUSTER_LIMIT_L1    = 2000    # group limit phase 1
REG_CLUSTER_LIMIT_L2    = 2002    # group limit phase 2
REG_CLUSTER_LIMIT_L3    = 2004    # group limit phase 3

# ---------------------------------------------------------------------------
# Status descriptions
# ---------------------------------------------------------------------------

STATUS_MAP: dict[int, str] = {
    # Based on OCPP 1.6 status values, but Etrel deviates on two points:
    #   4 (SuspendedEV) — per OCPP: EV paused, but this charger uses it
    #                     to mean "actively charging"
    #   6 (Faulted)     — per OCPP: fault, but this charger uses it
    #                     to mean "charging suspended" (cluster limit at 0A)
    0: "Available",
    1: "Preparing",
    2: "Charging",
    3: "SuspendedEVSE",
    4: "Charging",    # Etrel-specific: actively charging
    5: "Finishing",
    6: "Suspended",   # Etrel-specific: charging paused (limit at 0A)
    7: "Unavailable",
    8: "Reserved",
}

# ---------------------------------------------------------------------------
# Dataclass for a full charger reading
# ---------------------------------------------------------------------------

@dataclass
class ChargerState:
    status: int
    status_text: str
    ev_max_current: Optional[float]     # A
    frequency: Optional[float]          # Hz
    voltage_l1: Optional[float]         # V
    voltage_l2: Optional[float]         # V
    voltage_l3: Optional[float]         # V
    current_l1: Optional[float]         # A
    current_l2: Optional[float]         # A
    current_l3: Optional[float]         # A
    power_l1: Optional[float]           # kW
    power_l2: Optional[float]           # kW
    power_l3: Optional[float]           # kW
    power_total: Optional[float]        # kW
    power_factor: Optional[float]
    session_energy: Optional[float]     # kWh
    session_duration: Optional[int]     # seconds
    departure_time: Optional[int]       # Unix timestamp
    ev_battery_pct: Optional[float]     # %
    firmware_version: Optional[str]     # e.g. "2.3.1"
    cluster_limit_l1: Optional[float]   # A
    cluster_limit_l2: Optional[float]   # A
    cluster_limit_l3: Optional[float]   # A

# ---------------------------------------------------------------------------
# Client class
# ---------------------------------------------------------------------------

class EtrelModbusClient:
    """Modbus TCP client for the Etrel Lanova charger."""

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        self.host = host
        self.port = port
        self._client = ModbusTcpClient(host, port=port, timeout=timeout)

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def connect(self) -> bool:
        return self._client.connect()

    def disconnect(self) -> None:
        self._client.close()

    def is_connected(self) -> bool:
        return self._client.is_socket_open()

    def ensure_connected(self) -> bool:
        if not self.is_connected():
            return self.connect()
        return True

    # ------------------------------------------------------------------
    # Register read helpers
    # ------------------------------------------------------------------

    def _read_float_ir(self, address: int) -> Optional[float]:
        """Read two input registers and return a float32."""
        r = self._client.read_input_registers(address=address, count=2)
        if r.isError():
            return None
        raw = struct.pack(">HH", r.registers[0], r.registers[1])
        return struct.unpack(">f", raw)[0]

    def _read_uint16_ir(self, address: int) -> Optional[int]:
        """Read one input register and return a uint16."""
        r = self._client.read_input_registers(address=address, count=1)
        if r.isError():
            return None
        return r.registers[0]

    def _read_float_hr(self, address: int) -> Optional[float]:
        """Read two holding registers and return a float32."""
        r = self._client.read_holding_registers(address=address, count=2)
        if r.isError():
            return None
        raw = struct.pack(">HH", r.registers[0], r.registers[1])
        return struct.unpack(">f", raw)[0]

    def _write_float_hr(self, address: int, value: float) -> bool:
        """Write a float32 to two holding registers."""
        raw = struct.pack(">f", float(value))
        hi, lo = struct.unpack(">HH", raw)
        r = self._client.write_registers(address=address, values=[hi, lo])
        return not r.isError()

    # ------------------------------------------------------------------
    # Read methods
    # ------------------------------------------------------------------

    def read_status(self) -> Optional[int]:
        return self._read_uint16_ir(REG_STATUS)

    def read_status_text(self) -> str:
        s = self.read_status()
        return STATUS_MAP.get(s, "Unknown") if s is not None else "Unknown"

    def read_current_l1(self) -> Optional[float]:
        return self._read_float_ir(REG_CURRENT_L1)

    def read_current_l2(self) -> Optional[float]:
        return self._read_float_ir(REG_CURRENT_L2)

    def read_current_l3(self) -> Optional[float]:
        return self._read_float_ir(REG_CURRENT_L3)

    def read_voltage_l1(self) -> Optional[float]:
        return self._read_float_ir(REG_VOLTAGE_L1)

    def read_voltage_l2(self) -> Optional[float]:
        return self._read_float_ir(REG_VOLTAGE_L2)

    def read_voltage_l3(self) -> Optional[float]:
        return self._read_float_ir(REG_VOLTAGE_L3)

    def read_power_l1(self) -> Optional[float]:
        return self._read_float_ir(REG_POWER_L1)

    def read_power_l2(self) -> Optional[float]:
        return self._read_float_ir(REG_POWER_L2)

    def read_power_l3(self) -> Optional[float]:
        return self._read_float_ir(REG_POWER_L3)

    def read_power_total(self) -> Optional[float]:
        p1 = self.read_power_l1()
        p2 = self.read_power_l2()
        p3 = self.read_power_l3()
        if p1 is None and p2 is None and p3 is None:
            return None
        return round((p1 or 0.0) + (p2 or 0.0) + (p3 or 0.0), 3)

    def read_frequency(self) -> Optional[float]:
        return self._read_float_ir(REG_FREQUENCY)

    def read_power_factor(self) -> Optional[float]:
        return self._read_float_ir(REG_POWER_FACTOR)

    def read_session_energy(self) -> Optional[float]:
        return self._read_float_ir(REG_SESSION_ENERGY)

    def read_ev_max_current(self) -> Optional[float]:
        return self._read_float_ir(REG_EV_MAX_CURRENT)

    def read_target_current(self) -> Optional[float]:
        return self._read_float_hr(REG_TARGET_CURRENT)

    def _read_uint32_ir(self, address: int) -> Optional[int]:
        """Read two input registers and return a uint32."""
        r = self._client.read_input_registers(address=address, count=2)
        if r.isError():
            return None
        return struct.unpack(">I", struct.pack(">HH", r.registers[0], r.registers[1]))[0]

    def read_session_duration(self) -> Optional[int]:
        return self._read_uint32_ir(REG_SESSION_DURATION)

    def read_departure_time(self) -> Optional[int]:
        return self._read_uint32_ir(REG_DEPARTURE_TIME)

    def read_ev_battery_pct(self) -> Optional[float]:
        return self._read_float_ir(REG_EV_BATTERY_PCT)

    def read_firmware_version(self) -> Optional[str]:
        major = self._read_uint16_ir(REG_FW_MAJOR)
        minor = self._read_uint16_ir(REG_FW_MINOR)
        patch = self._read_uint16_ir(REG_FW_PATCH)
        if major is None or minor is None or patch is None:
            return None
        return f"{major}.{minor}.{patch}"

    def read_cluster_limit_l1(self) -> Optional[float]:
        return self._read_float_hr(REG_CLUSTER_LIMIT_L1)

    def read_cluster_limit_l2(self) -> Optional[float]:
        return self._read_float_hr(REG_CLUSTER_LIMIT_L2)

    def read_cluster_limit_l3(self) -> Optional[float]:
        return self._read_float_hr(REG_CLUSTER_LIMIT_L3)

    # ------------------------------------------------------------------
    # Write methods
    # ------------------------------------------------------------------

    def write_target_current(self, ampere: float) -> bool:
        """Write direct target current (HR 4)."""
        return self._write_float_hr(REG_TARGET_CURRENT, ampere)

    def write_cluster_limit(self, ampere: float) -> bool:
        """Write group limit to all three phases (HR 2000/2002/2004)."""
        ok1 = self._write_float_hr(REG_CLUSTER_LIMIT_L1, ampere)
        ok2 = self._write_float_hr(REG_CLUSTER_LIMIT_L2, ampere)
        ok3 = self._write_float_hr(REG_CLUSTER_LIMIT_L3, ampere)
        return ok1 and ok2 and ok3

    # ------------------------------------------------------------------
    # Full read in one call
    # ------------------------------------------------------------------

    def read_all(self) -> Optional[ChargerState]:
        """Read all registers and return a ChargerState, or None on connection failure."""
        if not self.ensure_connected():
            return None

        status = self.read_status() or 0
        p1 = self._read_float_ir(REG_POWER_L1)
        p2 = self._read_float_ir(REG_POWER_L2)
        p3 = self._read_float_ir(REG_POWER_L3)
        power_total = round((p1 or 0.0) + (p2 or 0.0) + (p3 or 0.0), 3)

        return ChargerState(
            status=status,
            status_text=STATUS_MAP.get(status, "Unknown"),
            ev_max_current=self._read_float_ir(REG_EV_MAX_CURRENT),
            frequency=self._read_float_ir(REG_FREQUENCY),
            voltage_l1=self._read_float_ir(REG_VOLTAGE_L1),
            voltage_l2=self._read_float_ir(REG_VOLTAGE_L2),
            voltage_l3=self._read_float_ir(REG_VOLTAGE_L3),
            current_l1=self._read_float_ir(REG_CURRENT_L1),
            current_l2=self._read_float_ir(REG_CURRENT_L2),
            current_l3=self._read_float_ir(REG_CURRENT_L3),
            power_l1=p1,
            power_l2=p2,
            power_l3=p3,
            power_total=power_total,
            power_factor=self._read_float_ir(REG_POWER_FACTOR),
            session_energy=self._read_float_ir(REG_SESSION_ENERGY),
            session_duration=self._read_uint32_ir(REG_SESSION_DURATION),
            departure_time=self._read_uint32_ir(REG_DEPARTURE_TIME),
            ev_battery_pct=self._read_float_ir(REG_EV_BATTERY_PCT),
            firmware_version=self.read_firmware_version(),
            cluster_limit_l1=self._read_float_hr(REG_CLUSTER_LIMIT_L1),
            cluster_limit_l2=self._read_float_hr(REG_CLUSTER_LIMIT_L2),
            cluster_limit_l3=self._read_float_hr(REG_CLUSTER_LIMIT_L3),
        )


# ---------------------------------------------------------------------------
# Quick test (python modbus_client.py)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    client = EtrelModbusClient()

    if not client.connect():
        print(f"No connection to {client.host}:{client.port}")
        exit(1)

    state = client.read_all()
    client.disconnect()

    if state is None:
        print("Read failed.")
        exit(1)

    print(f"Status         : {state.status_text} ({state.status})")
    print(f"Frequency      : {state.frequency:.2f} Hz" if state.frequency else "Frequency      : -")
    print(f"Voltage   L1   : {state.voltage_l1:.1f} V"  if state.voltage_l1 else "Voltage   L1   : -")
    print(f"Voltage   L2   : {state.voltage_l2:.1f} V"  if state.voltage_l2 else "Voltage   L2   : -")
    print(f"Voltage   L3   : {state.voltage_l3:.1f} V"  if state.voltage_l3 else "Voltage   L3   : -")
    print(f"Current   L1   : {state.current_l1:.2f} A"  if state.current_l1 else "Current   L1   : -")
    print(f"Current   L2   : {state.current_l2:.2f} A"  if state.current_l2 else "Current   L2   : -")
    print(f"Current   L3   : {state.current_l3:.2f} A"  if state.current_l3 else "Current   L3   : -")
    print(f"Power     L1   : {state.power_l1:.3f} kW"   if state.power_l1 else "Power     L1   : -")
    print(f"Power     L2   : {state.power_l2:.3f} kW"   if state.power_l2 else "Power     L2   : -")
    print(f"Power     L3   : {state.power_l3:.3f} kW"   if state.power_l3 else "Power     L3   : -")
    print(f"Power total    : {state.power_total:.3f} kW")
    print(f"Power factor   : {state.power_factor:.3f}"  if state.power_factor else "Power factor   : -")
    print(f"Session energy : {state.session_energy:.3f} kWh" if state.session_energy else "Session energy : -")
    print(f"EV max current : {state.ev_max_current:.1f} A" if state.ev_max_current else "EV max current : -")
    print(f"Cluster lim L1 : {state.cluster_limit_l1:.1f} A" if state.cluster_limit_l1 else "Cluster lim L1 : -")
    print(f"Cluster lim L2 : {state.cluster_limit_l2:.1f} A" if state.cluster_limit_l2 else "Cluster lim L2 : -")
    print(f"Cluster lim L3 : {state.cluster_limit_l3:.1f} A" if state.cluster_limit_l3 else "Cluster lim L3 : -")
    print(f"EV battery     : {state.ev_battery_pct:.0f}%" if state.ev_battery_pct is not None else "EV battery     : -")
    print(f"Session dur    : {state.session_duration}s" if state.session_duration else "Session dur    : -")
    print(f"Firmware       : {state.firmware_version}" if state.firmware_version else "Firmware       : -")

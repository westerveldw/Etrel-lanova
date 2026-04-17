"""Constants for the Etrel Lanova integration."""

DOMAIN = "etrel_lanova"

# Connection settings
DEFAULT_HOST = "192.168.2.139"
DEFAULT_PORT = 502        # read: measurements, status, current, voltage
DEFAULT_PORT_WRITE = 503  # write: cluster limits (LoadGuard)
DEFAULT_SCAN_INTERVAL = 10  # seconds

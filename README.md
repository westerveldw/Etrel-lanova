# Etrel Lanova - Home Assistant Integration

Custom integration for the Etrel Lanova EV charger in Home Assistant, using Modbus TCP.

## Features

- Sensors: status, current (L1/L2/L3), voltage, power, energy, frequency
- Set maximum charging current via the interface
- Polling via Modbus TCP (port 502 for reading, port 503 for writing)

## Installation via HACS

1. Go to **HACS → Integrations** in Home Assistant
2. Click the three dots in the top right and choose **Custom repositories**
3. Add: `https://github.com/westerveldw/Etrel-lanova` as type **Integration**
4. Search for **Etrel Lanova** and install
5. Restart Home Assistant

## Manual installation

1. Copy the `custom_components/etrel_lanova/` folder to the `custom_components/` directory of your Home Assistant installation
2. Restart Home Assistant

## Configuration

1. Go to **Settings → Devices & Services → Add integration**
2. Search for **Etrel Lanova**
3. Enter the IP address of your charger

## Requirements

- Home Assistant
- Etrel Lanova charger with Modbus TCP enabled
- `pymodbus >= 3.0.0`

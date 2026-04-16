# Etrel Lanova - Home Assistant Integration

Custom integration voor de Etrel Lanova laadpaal in Home Assistant, via Modbus TCP.

## Functies

- Uitlezen van sensoren: status, stroom (L1/L2/L3), spanning, vermogen, energie, frequentie
- Instellen van maximale laadstroom via de interface
- Polling via Modbus TCP (poort 502 voor lezen, 503 voor schrijven)

## Installatie via HACS

1. Ga in Home Assistant naar **HACS → Integraties**
2. Klik op de drie puntjes rechtsboven en kies **Aangepaste opslagplaatsen**
3. Voeg toe: `https://github.com/westerveldw/Etrel-lanova` als type **Integratie**
4. Zoek naar **Etrel Lanova** en installeer
5. Herstart Home Assistant

## Handmatige installatie

1. Kopieer de map `custom_components/etrel_lanova/` naar de `custom_components/` map van jouw Home Assistant installatie
2. Herstart Home Assistant

## Configuratie

1. Ga naar **Instellingen → Apparaten & Diensten → Integratie toevoegen**
2. Zoek op **Etrel Lanova**
3. Vul het IP-adres van de laadpaal in

## Vereisten

- Home Assistant
- Etrel Lanova laadpaal met Modbus TCP ingeschakeld
- `pymodbus >= 3.0.0`

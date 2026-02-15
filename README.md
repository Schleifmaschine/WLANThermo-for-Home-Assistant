# WLANThermo Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![GitHub release](https://img.shields.io/github/release/Schleifmaschine/WLANThermo-for-Home-Assistant.svg)](https://github.com/Schleifmaschine/WLANThermo-for-Home-Assistant/releases)
[![License](https://img.shields.io/github/license/Schleifmaschine/WLANThermo-for-Home-Assistant.svg)](LICENSE)

Eine vollständige Home Assistant Integration für WLANThermo-Geräte (Mini V3, Nano V3, etc.) mit MQTT-Unterstützung.

## Features

- 🌡️ **Temperatursensoren** für alle Kanäle
- 🔔 **Alarm-Temperaturen** konfigurierbar
- 🔌 **Kanal-Steuerung** (aktivieren/deaktivieren)
- 🔥 **Pitmaster-Steuerung** (Zieltemperatur, Modus, Lüfterwert)
- 📊 **System-Sensoren** (CPU, Batterie, WiFi, Online-Status)
- 🎨 **UI-Konfiguration** über Config Flow
- 🌍 **Mehrsprachig** (Deutsch & Englisch)
- 📱 **HACS-kompatibel** für einfache Installation

## Unterstützte Geräte

- WLANThermo Mini V3
- WLANThermo Nano V3
- WLANThermo Link V1
- Andere ESP32-basierte WLANThermo-Geräte

## Voraussetzungen

1. **Home Assistant** (Version 2023.1.0 oder neuer)
2. **MQTT Broker** (z.B. Mosquitto)
3. **WLANThermo-Gerät** mit MQTT-Unterstützung

## Installation

### HACS (empfohlen)

1. Öffne HACS in Home Assistant
2. Gehe zu "Integrationen"
3. Klicke auf die drei Punkte oben rechts und wähle "Benutzerdefinierte Repositories"
4. Füge die Repository-URL hinzu: `https://github.com/Schleifmaschine/WLANThermo-for-Home-Assistant`
5. Kategorie: "Integration"
6. Klicke auf "Hinzufügen"
7. Suche nach "WLANThermo" und installiere die Integration
8. Starte Home Assistant neu

### Manuell

1. Lade die neueste Version von [Releases](https://github.com/Schleifmaschine/WLANThermo-for-Home-Assistant/releases) herunter
2. Entpacke das Archiv
3. Kopiere den Ordner `custom_components/wlanthermo` in dein Home Assistant `config/custom_components/` Verzeichnis
4. Starte Home Assistant neu

## Konfiguration

### 1. MQTT-Broker einrichten

Stelle sicher, dass du einen MQTT-Broker in Home Assistant konfiguriert hast:

**Einstellungen** → **Geräte & Dienste** → **MQTT**

### 2. WLANThermo MQTT konfigurieren

Konfiguriere dein WLANThermo-Gerät, um Daten an deinen MQTT-Broker zu senden:

1. Öffne die WLANThermo-Weboberfläche
2. Gehe zu **Einstellungen** → **MQTT**
3. Aktiviere MQTT
4. Setze den **Host** auf die IP-Adresse deines Home Assistant
5. Setze **Port** auf `1883` (Standard)
6. Optional: Benutzername und Passwort eingeben
7. Speichern

### 3. Integration in Home Assistant hinzufügen

1. Gehe zu **Einstellungen** → **Geräte & Dienste**
2. Klicke auf **+ Integration hinzufügen**
3. Suche nach "WLANThermo"
4. Gib die folgenden Informationen ein:
   - **Gerätename**: Ein Name für dein WLANThermo (z.B. "Grill")
   - **MQTT Topic-Präfix**: Das Topic-Präfix deines Geräts (z.B. `WLanThermo/MINI-V3`)
5. Klicke auf **Absenden**

## Verwendung

Nach der Konfiguration werden automatisch folgende Entitäten erstellt:

### Sensoren

- **Temperatur-Sensoren** für jeden Kanal (z.B. `sensor.grill_kanal_1`)
- **Batterie** (`sensor.grill_battery`)
- **WiFi-Signal** (`sensor.grill_wifi_signal`)

### Number-Entitäten

- **Alarm Min** für jeden Kanal (z.B. `number.grill_kanal_1_alarm_min`)
- **Alarm Max** für jeden Kanal (z.B. `number.grill_kanal_1_alarm_max`)


## MQTT-Topics

Die Integration verwendet folgende MQTT-Topics:

| Topic | Beschreibung |
|-------|--------------|
| `{prefix}/status/data` | Status-Daten (Temperaturen, System) |
| `{prefix}/status/settings` | Einstellungen |
| `{prefix}/set/channels` | Kanal-Konfiguration setzen |

Wobei `{prefix}` dein konfiguriertes Topic-Präfix ist (z.B. `WLanThermo/MINI-V3`).

## Beispiel-Automatisierung

```yaml
automation:
  - alias: "Grill Temperatur Alarm"
    trigger:
      - platform: numeric_state
        entity_id: sensor.grill_kanal_1
        above: 200
    action:
      - service: notify.mobile_app
        data:
          title: "Grill Alarm"
          message: "Temperatur über 200°C!"
```

## Troubleshooting

### Keine Daten empfangen

1. Überprüfe, ob der MQTT-Broker läuft
2. Überprüfe die MQTT-Konfiguration im WLANThermo
3. Überprüfe das Topic-Präfix in der Integration
4. Schaue in die Home Assistant Logs: **Einstellungen** → **System** → **Protokolle**

### Entitäten werden nicht erstellt

1. Stelle sicher, dass das WLANThermo Daten sendet
2. Überprüfe die MQTT-Topics mit einem MQTT-Client (z.B. MQTT Explorer)
3. Starte Home Assistant neu

### MQTT-Topics finden

Verwende einen MQTT-Client wie [MQTT Explorer](http://mqtt-explorer.com/) um zu sehen, welche Topics dein WLANThermo verwendet.

## Entwicklung

### Lokales Testen

1. Clone das Repository
2. Kopiere `custom_components/wlanthermo` in dein Home Assistant `config/custom_components/` Verzeichnis
3. Starte Home Assistant neu
4. Aktiviere Debug-Logging in `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.wlanthermo: debug
```

## Beitragen

Contributions sind willkommen! Bitte erstelle einen Pull Request oder öffne ein Issue.

## Lizenz

MIT License - siehe [LICENSE](LICENSE) Datei

## Credits

- Entwickelt für die [WLANThermo](https://wlanthermo.de/) Community
- Basierend auf der [Home Assistant Integration Blueprint](https://github.com/home-assistant/example-custom-config)

## Support

Bei Problemen oder Fragen:
- Öffne ein [Issue auf GitHub](https://github.com/Schleifmaschine/WLANThermo-for-Home-Assistant/issues)
- Besuche das [WLANThermo Forum](https://forum.wlanthermo.de/)

---

**Hinweis**: Diese Integration ist nicht offiziell von WLANThermo unterstützt.

# WLANThermo Home Assistant Integration

![WLANThermo Logo](logo.png)

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![GitHub release](https://img.shields.io/github/release/Schleifmaschine/WLANThermo-for-Home-Assistant.svg)](https://github.com/Schleifmaschine/WLANThermo-for-Home-Assistant/releases)
[![License](https://img.shields.io/github/license/Schleifmaschine/WLANThermo-for-Home-Assistant.svg)](LICENSE)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2023.1.0+-blue.svg)](https://www.home-assistant.io/)

Eine leistungsstarke Integration für [WLANThermo](https://wlanthermo.de/) Geräte (Mini V3, Nano V3, Link V1, etc.) in Home Assistant via MQTT.

## 🌟 Features

- 🌡️ **Echtzeit-Temperaturen**: Monitoring aller verfügbaren Kanäle.
- 🔔 **Intelligente Alarme**: Konfiguration von Min/Max-Alarmen direkt aus HA.
- 🛠️ **Kanal-Anpassung**: Namen und Farben (Hex-Code) der Kanäle ändern.
- 🔥 **Pitmaster-Kontrolle**: Vollständige Steuerung von Modus, Zieltemperatur, Profilen und Kanälen.
- 📊 **System-Monitoring**: Batterie (Status & Laden), RSSI, CPU-Temperatur, UpTime.
- 🎨 **Modernes UI**: Einfache Einrichtung via Config Flow und automatische Entitätserstellung.
- 🌍 **Mehrsprachig**: Volle Unterstützung für Deutsch und Englisch.

## 📱 Unterstützte Geräte

- WLANThermo Mini V3
- WLANThermo Nano V3
- WLANThermo Link V1
- ESP32-basierte Eigenbau-Geräte mit aktueller Firmware

---

## 🚀 Installation

### HACS (Empfohlen)

1. Öffne **HACS** in Home Assistant.
2. Gehe zu **Integrationen**.
3. Klicke oben rechts auf die drei Punkte und wähle **Benutzerdefinierte Repositories**.
4. Füge hinzu: `https://github.com/Schleifmaschine/WLANThermo-for-Home-Assistant`
5. Kategorie: **Integration**.
6. Suche nach **WLANThermo** und installiere es.
7. Starte Home Assistant neu.

### Manuell

1. Lade das neueste [Release](https://github.com/Schleifmaschine/WLANThermo-for-Home-Assistant/releases) herunter.
2. Kopiere den Ordner `custom_components/wlanthermo` in dein `config/custom_components/` Verzeichnis.
3. Starte Home Assistant neu.

---

## ⚙️ Konfiguration

### 1. MQTT am WLANThermo einrichten
1. Weboberfläche deines WLANThermo öffnen.
2. **Einstellungen** → **MQTT** aufrufen.
3. MQTT aktivieren und die IP deines HA-Brokers eintragen.
4. Wir empfehlen das Topic-Präfix `WLanThermo/MINI-V3` (Standard).

### 2. Integration in HA hinzufügen
1. **Einstellungen** → **Geräte & Dienste** → **+ Integration hinzufügen**.
2. Nach **WLANThermo** suchen.
3. Wähle einen Namen (z.B. "Smoker") und gib das exakte MQTT Topic-Präfix an.

---

## 🏛️ Entitäten Übersicht

Die Integration erstellt pro Gerät folgende Entitäten:

### Sensoren & Binary Sensors
| Plattform | Name | Beschreibung |
| :--- | :--- | :--- |
| `sensor` | **Kanal X Temperatur** | Aktuelle Temperatur des Fühlers |
| `sensor` | **Pitmaster Wert** | Aktuelle Lüfter-/Servo-Leistung in % |
| `sensor` | **Batterie** | Ladezustand in % |
| `sensor` | **RSSI** | WiFi-Signalstärke |
| `binary_sensor` | **Online** | Verbindungsstatus zum Broker |
| `binary_sensor` | **Charging** | Zeigt an, ob das Gerät lädt |

### Steuerung (Select, Number, Text)
- **Selects**:
    - **Alarm Modus**: Aus, Push, Piepser, Beides.
    - **Fühlertypen**: Wechsel der Kennlinien (z.B. Maverick, iGrill).
    - **Pitmaster Modus**: Aus, Manuell, Auto.
    - **Pitmaster Profil**: Auswahl der hinterlegten Profile.
- **Numbers**:
    - **Alarm Min/Max**: Grenzwerte für die Temperatur-Warnung.
    - **Zieltemperatur**: Setpoint für den Pitmaster.
- **Text**:
    - **Kanal Name**: Ändert den Namen direkt am Gerät.
    - **Kanal Farbe**: Hex-Code (z.B. `#FF0000`) für das Display.

---

## 💡 Automatisierungs-Beispiel

Benachrichtigung, wenn das Fleisch fertig ist:

```yaml
alias: "BBQ: KT erreicht"
trigger:
  - platform: numeric_state
    entity_id: sensor.smoker_kanal_1_temperatur
    above: 92
action:
  - service: notify.mobile_app_iphone
    data:
      title: "WLANThermo"
      message: "KT von 92°C erreicht! Zeit zum Ruhen."
```

---

## 🛠️ Troubleshooting

- **Keine Daten?** Prüfe mit [MQTT Explorer](http://mqtt-explorer.com/), ob unter dem konfigurierten Präfix Daten ankommen.
- **Entitäten fehlen?** Die Integration benötigt eine aktive MQTT-Publikation vom Gerät, um die Kanäle initial zu erkennen.
- **Logs:** Aktiviere Debug-Logging, falls Probleme auftreten:
  ```yaml
  logger:
    logs:
      custom_components.wlanthermo: debug
  ```

---

## 🤝 Beitragen & Support

Hast du Verbesserungsvorschläge oder Fehler gefunden?
- Öffne ein [Issue](https://github.com/Schleifmaschine/WLANThermo-for-Home-Assistant/issues).
- Diskutiere im [WLANThermo Forum](https://forum.wlanthermo.de/).

*Dieses Projekt ist eine Community-Entwicklung und steht in keiner offiziellen Verbindung zur WLANThermo GmbH.*

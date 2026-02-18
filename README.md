# WLANThermo Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![GitHub release](https://img.shields.io/github/release/Schleifmaschine/WLANThermo-for-Home-Assistant.svg)](https://github.com/Schleifmaschine/WLANThermo-for-Home-Assistant/releases)
[![License](https://img.shields.io/github/license/Schleifmaschine/WLANThermo-for-Home-Assistant.svg)](LICENSE)

🌡️ WLANThermo für Home Assistant
Eine leistungsstarke und native Home Assistant Integration für WLANThermo-Geräte. Verbinde dein Grill-Thermometer nahtlos mit deinem Smart Home über MQTT und behalte deine Temperaturen, Pitmaster-Steuerung und Alarme direkt in Home Assistant im Blick.

✨ Funktionen
Diese Integration bietet weit mehr als nur das Anzeigen von Temperaturen:

🔥 Live-Temperaturen: Überwachung aller Fühler-Kanäle in Echtzeit.

⚙️ Pitmaster-Steuerung: Setze die Zieltemperatur, ändere den Modus und überwache den Lüfter-Status direkt aus HA.

🔔 Alarm-Management: Konfiguriere Min/Max-Alarmgrenzen für jeden Kanal individuell über Number-Entitäten.

🔋 System-Status: Behalte Akkustand, WLAN-Signalstärke und Online-Status im Auge.

🔌 Kanal-Verwaltung: Aktiviere oder deaktiviere einzelne Kanäle bei Bedarf.

🛠️ Einfache Einrichtung: Volle Unterstützung für den Home Assistant Config Flow (UI-Konfiguration).

📱 Unterstützte Geräte
Die Integration wurde primär für folgende Modelle entwickelt, sollte aber mit allen ESP32-basierten WLANThermo-Geräten funktionieren, die das aktuelle API unterstützen:

✅ WLANThermo Mini V3

✅ WLANThermo Nano V3

✅ WLANThermo Link V1

🛠 Voraussetzungen
Bevor du startest, stelle sicher, dass du folgendes bereit hast:

Home Assistant (Version 2023.1.0 oder neuer).

Einen installierten MQTT Broker (z.B. das offizielle Mosquitto Add-on in Home Assistant).

Ein WLANThermo-Gerät, das im selben Netzwerk verbunden ist.

💾 Installation
Via HACS (Empfohlen)
Der einfachste Weg, die Integration aktuell zu halten.

Öffne HACS in deinem Home Assistant.

Wähle Integrationen > Menü (drei Punkte oben rechts) > Benutzerdefinierte Repositories.

Füge folgende URL hinzu:
https://github.com/Schleifmaschine/WLANThermo-for-Home-Assistant

Wähle als Kategorie Integration.

Klicke auf Hinzufügen und suche dann in HACS nach "WLANThermo".

Klicke auf Herunterladen.

Wichtig: Starte Home Assistant neu!

Manuelle Installation
Lade die neueste Version von den Releases herunter.

Entpacke die Datei.

Kopiere den Ordner custom_components/wlanthermo in dein Home Assistant Verzeichnis: /config/custom_components/.

Starte Home Assistant neu.

⚙ Konfiguration
Schritt 1: MQTT Broker
Stelle sicher, dass die MQTT-Integration in Home Assistant korrekt eingerichtet ist (Einstellungen → Geräte & Dienste → MQTT).

Schritt 2: WLANThermo Einstellungen
Damit dein Thermo mit Home Assistant sprechen kann, muss MQTT auf dem Gerät aktiviert werden:

Öffne das Web-Interface deines WLANThermo.

Navigiere zu Einstellungen → MQTT.

Aktiviere den Haken bei MQTT.

Host: IP-Adresse deines Home Assistant (oder des MQTT Brokers).

Port: Standard ist 1883.

(Optional) Benutzername/Passwort, falls im Broker konfiguriert.

Speichere die Einstellungen.

Schritt 3: Integration hinzufügen
Gehe in Home Assistant zu Einstellungen → Geräte & Dienste.

Klicke unten rechts auf + Integration hinzufügen.

Suche nach WLANThermo.

Gib die erforderlichen Daten ein:

Name: Ein Anzeigename (z.B. "Mein Grill").

MQTT Topic-Präfix: Dies muss mit der Einstellung im WLANThermo übereinstimmen (Standard oft: WLanThermo/MINI-V3 oder ähnlich).

Bestätigen – fertig! 🎉

📊 Nutzung & Entitäten
Nach der Einrichtung erstellt die Integration automatisch ein Gerät mit diversen Entitäten.

Haupt-Sensoren
sensor.mein_grill_kanal_1 ... sensor.mein_grill_kanal_8: Aktuelle Temperaturen.

sensor.mein_grill_battery: Batteriestatus in %.

sensor.mein_grill_wifi_signal: RSSI-Wert des WLANs.

Steuerung (Number & Select)
number.mein_grill_kanal_1_alarm_min: Untergrenze für Alarm.

number.mein_grill_kanal_1_alarm_max: Obergrenze für Alarm.

number.mein_grill_pitmaster_set_temp: Zieltemperatur für den Pitmaster.

🤖 Automatisierungs-Beispiele
Benachrichtigung bei Zieltemperatur
Sende eine Push-Nachricht auf dein Handy, wenn das Fleisch fertig ist.

YAML
alias: "Grill: Fleisch ist fertig"
description: "Benachrichtigung wenn Kanal 1 über 93 Grad steigt"
trigger:
  - platform: numeric_state
    entity_id: sensor.mein_grill_kanal_1
    above: 93
action:
  - service: notify.mobile_app_dein_handy
    data:
      title: "🍖 Essen ist fertig!"
      message: "Das Pulled Pork hat 93°C erreicht. Guten Appetit!"
Pitmaster Automatik
Schalte den Pitmaster aus, wenn der Grillvorgang beendet ist (manuell oder via Logik).

YAML
alias: "Grill: Pitmaster aus"
trigger:
  - platform: state
    entity_id: input_boolean.grill_session
    to: "off"
action:
  - service: number.set_value
    target:
      entity_id: number.mein_grill_pitmaster_set_temp
    data:
      value: 0
❓ Troubleshooting
Problem: Keine Entitäten oder "Nicht verfügbar"

Prüfe mit einem Tool wie MQTT Explorer, ob Daten unter dem konfigurierten Topic ankommen.

Stimmt das Topic-Präfix in der Integration exakt mit dem im WLANThermo überein? (Groß-/Kleinschreibung beachten!).

Ist das WLANThermo im selben Netzwerk und online?

Problem: Änderungen in HA werden nicht am Thermo übernommen

Stelle sicher, dass das Topic .../set/... vom Broker empfangen und vom WLANThermo gelesen werden kann.

📜 Lizenz & Credits
Dieses Projekt steht unter der MIT Lizenz. Siehe LICENSE für Details.

Entwickelt von Schleifmaschine.

Ein großer Dank geht an die WLANThermo Community für die großartige Hardware und Software.

Hinweis: Dies ist ein Community-Projekt und keine offizielle Integration des WLANThermo-Herstellers.
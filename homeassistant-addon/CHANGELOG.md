# TalkAnchor-Add-on-Changelog

## 0.1.2

- Geführter Web-Setup-Wizard (`/wizard`, Button im Dashboard): führt
  Schritt für Schritt durch Cloudflare, SSH-Einrichtung (inkl.
  Host-Key-Abruf und Sofia-Config-Discovery) und Benachrichtigungen und
  schreibt die Konfiguration am Ende direkt in die Add-on-Optionen
  (Supervisor-API, `hassio_api: true`), inklusive automatischem Neustart.
  Ersetzt den bisherigen „Setup-Helfer" als primären Einrichtungsweg.
- Dashboard-Bereich „Diagnose" (vormals „Setup-Helfer") zum erneuten
  Prüfen der bereits gespeicherten Konfiguration.

## 0.1.1

- Setup-Helfer im Dashboard (SSH-Host-Key abrufen, Sofia-Config-Pfad
  suchen, Cloudflare-Verbindung testen) als Ersatz für die SSH-Schritte
  des CLI-Wizards, den das Add-on nicht ausführen kann.
- Options-Schema-Fix: Felder mit leerem Standardwert sind jetzt korrekt
  optional statt fälschlich verpflichtend.

## 0.1.0

- Erstes Release, umhüllt TalkAnchor 0.1.0.

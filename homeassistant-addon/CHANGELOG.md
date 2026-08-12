# TalkAnchor-Add-on-Changelog

## 0.1.1

- Geführter Web-Setup-Wizard (`/wizard`, Button im Dashboard): führt
  Schritt für Schritt durch Cloudflare, SSH-Einrichtung (inkl.
  Host-Key-Abruf und Sofia-Config-Discovery) und Benachrichtigungen und
  schreibt die Konfiguration am Ende direkt in die Add-on-Optionen
  (Supervisor-API, `hassio_api: true`), inklusive automatischem Neustart.
- Dashboard-Bereich „Diagnose" zum erneuten Prüfen der bereits
  gespeicherten Konfiguration.
- Options-Schema-Fix: Felder mit leerem Standardwert sind jetzt korrekt
  optional statt fälschlich verpflichtend.

## 0.1.0

- Erstes Release, umhüllt TalkAnchor 0.1.0.

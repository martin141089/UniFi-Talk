# TalkAnchor-Add-on-Changelog

## 0.1.8

- Neuer Knopf "Schlüssel automatisch erzeugen" im SSH-Schritt des
  Wizards: erzeugt den Schlüssel serverseitig (kein Terminal mehr nötig),
  zeigt nur die öffentliche Zeile zum Einfügen bei UniFi. Manuelles
  Einfügen eines eigenen Schlüssels bleibt als aufklappbare
  "fortgeschritten"-Option erhalten.

## 0.1.7

- Warnhinweis direkt am Cloudflare-Token-Feld im Wizard: der Tunnel-
  Connector-Token aus `cloudflared tunnel run --token …` (beginnt meist
  mit `eyJ…`) ist NICHT das gesuchte API-Token. Erklärt den Unterschied
  und verlinkt den richtigen Weg (My Profile → API Tokens → Create
  Token).

## 0.1.6

- "Anzeigen"-Knopf neben dem Cloudflare-Token-Feld im Wizard, um die
  Eingabe bei Bedarf im Klartext zu prüfen (das Feld war zuvor immer
  maskiert, obwohl `paste`-Fehler unsichtbar blieben). Zusätzlich zeigt
  die Fehlermeldung bei einer abgelehnten Verbindung jetzt sicher Länge,
  Anfang/Ende und eventuelle nicht-druckbare Zeichen des empfangenen
  Tokens.

## 0.1.5

- Cloudflare-Token-Feld im Wizard erkennt jetzt automatisch, wenn versehentlich
  mehr als der reine Token eingefügt wurde (z. B. Cloudflares eigenes
  curl-Beispiel drumherum) und extrahiert nur den Token daraus; verbleibender
  Leerraum/Zeilenumbrüche werden zusätzlich entfernt.

## 0.1.4

- Cloudflare-Verbindungstest im Setup-Wizard liefert jetzt eine genaue
  Diagnose statt der rohen Cloudflare-Fehlermeldung: unterscheidet
  "Token selbst ungültig" (inkl. Zeichenlänge zur Copy-Paste-Prüfung) von
  "Token gültig, aber kein Zugriff auf Account-/Tunnel-ID".

## 0.1.3

- Dashboard und Setup-Wizard waren unter Ingress komplett ungestylt und
  der Wizard-Button/API-Aufrufe liefen ins Leere (404), weil alle
  CSS-/JS-/API-Pfade absolut waren. Jetzt über `X-Ingress-Path` und
  relative Pfade korrekt behoben.

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

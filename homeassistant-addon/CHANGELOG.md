# TalkAnchor-Add-on-Changelog

## 0.1.14

- SSH schlug nach erneutem Speichern über das native HA-Konfigurations-
  formular fehl, weil dessen Einzeilen-Textfeld die Zeilenumbrüche des
  privaten Schlüssels verschluckte. Wird beim Add-on-Start jetzt
  automatisch repariert (Schlüssel korrekt neu umgebrochen); Doku
  ergänzt, dieses Feld nur über den Wizard zu bearbeiten.
- Sofia-Config-Suche übernahm bei mehreren Kandidaten blind den ersten
  statt den zum konfigurierten Profilnamen passenden — jetzt bevorzugt
  und mit Hinweis, die Auswahl zu prüfen.

## 0.1.13

- Live-Fehler behoben: Sofia-Config-Suche traf nur die FreeSWITCH-
  Loader-Config statt der eigentlichen Profildatei mit den IP-Parametern
  — Anwenden schlug deshalb fehl ("Parameter(s) ... not found"). Die
  Suche prüft jetzt zuerst den Dateiinhalt statt nur den Dateinamen.
  Bitte im Wizard "Sofia-Config-Pfad suchen" erneut ausführen.
- Fehlgeschlagenes Anwenden erzeugte unnötig ein Backup, bevor der
  eigentliche Fehler erkannt wurde — jetzt erst unmittelbar vor dem
  Schreibvorgang.
- Wiederkehrender Traceback beim Neustart behoben (Scheduler-Shutdown
  lief nach dem Schließen der Event-Loop statt davor).

## 0.1.12

- Neuer Schalter "Cloudflare-Tunnel-Connector-IP als Quelle verwenden" im
  Wizard und als Option (`cloudflare_enabled`). Lässt sich ausschalten,
  wenn der Tunnel (z. B. bei Multi-WAN) strukturell nie eine eindeutige
  IP liefern kann — TalkAnchor läuft dann bewusst nur mit der
  Fallback-Quelle, ohne die Cloudflare-Zugangsdaten löschen zu müssen.

## 0.1.11

- Wizard lädt beim Öffnen jetzt zusätzlich die bereits gespeicherte
  Konfiguration direkt vom Server, nicht mehr nur aus dem lokalen
  Browser-Entwurf — behebt fehlende Werte, wenn der Wizard aus einer
  anderen Sitzung/App heraus erneut geöffnet wird.

## 0.1.10

- Wizard-Eingaben gingen bei Neuladen/Navigation verloren, da sie erst
  beim finalen Speichern an den Server geschickt wurden. Alle Felder
  werden jetzt laufend im Browser zwischengespeichert und beim erneuten
  Öffnen automatisch wiederhergestellt.

## 0.1.9

- Klarere Fehlermeldung, wenn UniFi die SSH-Authentifizierung ablehnt:
  vorher zeigte Paramiko irreführend einen "falsches Schlüsselformat"-
  Fehler (z. B. "encountered RSA key, expected OPENSSH key"), obwohl der
  Schlüssel technisch in Ordnung war — das eigentliche Problem ist fast
  immer, dass der öffentliche Schlüssel nicht korrekt bei UniFi hinterlegt
  wurde. Wird jetzt erkannt und klar benannt.

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

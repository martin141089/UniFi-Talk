# TalkAnchor-Add-on-Changelog

## 0.2.3

- Dashboard-Verlauf zeigt nur noch die letzten 3 Einträge mit „Weitere
  Verläufe laden"-Button; Historie wird automatisch auf 90 Einträge
  begrenzt.
- Reihenfolge im Dashboard: „Verlauf" steht jetzt vor „Diagnose".

## 0.2.2

- Health-Check nutzte einen fs_cli-Befehl, der so nicht existiert.
  Gateway-Registrierungen werden jetzt korrekt über `sofia status
  gateway` abgefragt.
- Verlauf und Wizard-Zusammenfassung liefen auf schmalen Bildschirmen
  über den Rand — Verlauf wird auf dem Handy jetzt als Kartenliste
  dargestellt.

## 0.2.1

- Logo in der Dokumentation (Reiter „Dokumentation") wurde von Home
  Assistants Doku-Viewer nicht angezeigt.

## 0.2.0

- Logo/Icon repariert: korrekt zentriert, transparenter Hintergrund
  statt weißer Fläche.
- Alle vom Add-on erzeugten Meldungen (Anwenden/Health-Check/Rollback,
  Benachrichtigungen, Log-Zeilen) jetzt durchgängig auf Deutsch.
- Dokumentation ausführlicher und einsteigerfreundlicher.
- Dashboard und Wizard-Formulare für schmale Handy-Bildschirme
  verbessert.

## 0.1.19

- Ein Dry-Run-Speichervorgang nach einem zurückgerollten scharfen
  Zyklus wurde fälschlich als bereits übernommen gewertet und hätte den
  nötigen Korrekturversuch dauerhaft unterdrückt.

## 0.1.18

- „Jetzt Testlauf ausführen" bzw. „Jetzt prüfen" liefen im Hintergrund
  weiter statt die Verbindung offen zu halten — verhindert
  Verbindungsabbrüche bei hohem Health-Check-Timeout.

## 0.1.17

- Health-Check fragte Endpunkt- statt Gateway-Registrierungen ab und
  wurde bei reinen Trunk-Profilen nie gesund.

## 0.1.16

- Nach einem per Health-Check ausgelösten Rollback hielt TalkAnchor die
  verworfene IP fälschlich für bereits übernommen.

## 0.1.15

- Cloudflare-API-Token-Feld im Wizard ist kein maskiertes Passwortfeld
  mehr (iOS Safari ersetzte es trotz `autocomplete="off"` wiederholt
  durch ein gespeichertes Passwort).

## 0.1.14

- Privater SSH-Schlüssel verlor beim Speichern über das native
  HA-Konfigurationsformular seine Zeilenumbrüche; wird jetzt beim
  Add-on-Start automatisch repariert.
- Sofia-Config-Suche wählte bei mehreren Treffern blind den ersten
  statt des passenden.

## 0.1.13

- Sofia-Config-Suche fand nur die FreeSWITCH-Loader-Datei statt der
  eigentlichen Profildatei; sucht jetzt nach Dateiinhalt statt Namen.
- Fehlgeschlagenes Anwenden legte trotzdem ein Backup an.
- Wiederkehrender Traceback beim Neustart behoben.

## 0.1.12

- Schalter „Cloudflare-Tunnel-Connector-IP als Quelle verwenden"
  (`cloudflare_enabled`) für Tunnel ohne eindeutige IP (z. B. Multi-WAN).

## 0.1.11

- Wizard lädt beim Öffnen zusätzlich die bereits gespeicherte
  Konfiguration direkt vom Server.

## 0.1.10

- Wizard-Eingaben werden laufend im Browser zwischengespeichert und bei
  erneutem Öffnen automatisch wiederhergestellt.

## 0.1.9

- Klarere Fehlermeldung, wenn UniFi die SSH-Authentifizierung ablehnt
  (statt Paramikos irreführender „falsches Schlüsselformat"-Meldung).

## 0.1.8

- Knopf „Schlüssel automatisch erzeugen" im SSH-Schritt des Wizards —
  kein Terminal mehr nötig.

## 0.1.7

- Warnhinweis am Cloudflare-Token-Feld: der Tunnel-Connector-Token ist
  nicht dasselbe wie das benötigte API-Token.

## 0.1.6

- „Anzeigen"-Knopf am Cloudflare-Token-Feld sowie eine sichere Kurzform
  des empfangenen Tokens in der Fehlermeldung.

## 0.1.5

- Cloudflare-Token-Feld erkennt und entfernt automatisch ein
  versehentlich mitkopiertes `Bearer <token>`-Präfix.

## 0.1.4

- Cloudflare-Verbindungstest unterscheidet jetzt zwischen ungültigem
  Token und gültigem Token ohne Zugriff auf Account/Tunnel.

## 0.1.3

- Dashboard und Wizard waren unter Ingress ungestylt (absolute statt
  relative Asset-/API-Pfade).

## 0.1.2

- Geführter Web-Setup-Wizard (`/wizard`, Button im Dashboard), schreibt
  direkt in die Add-on-Optionen.
- Dashboard-Bereich „Diagnose" (vormals „Setup-Helfer").

## 0.1.1

- Setup-Helfer im Dashboard (SSH-Host-Key, Sofia-Config-Pfad,
  Cloudflare-Verbindungstest).
- Options-Schema-Fix: leere Standardwerte machten Felder fälschlich zu
  Pflichtfeldern.

## 0.1.0

- Erstes Release, umhüllt TalkAnchor 0.1.0.

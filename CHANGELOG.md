# Changelog

Alle nennenswerten Änderungen an diesem Projekt werden in dieser Datei
dokumentiert.

Das Format orientiert sich an [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
dieses Projekt folgt [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.16] - 2026-08-13

### Behoben

- **Live auf der Henschke-Instanz beobachtet:** Der Patch auf die neue IP
  gelang, der anschließende Health-Check sah aber innerhalb von 30s keine
  gesunde Registrierung und TalkAnchor rollte korrekt zurück (genau wie
  vorgesehen). Dabei zeigte sich aber ein Folgefehler: `get_last_known_ip()`
  zählte den Schreibvorgang trotz Rollback weiterhin als "zuletzt bekannte
  IP", weil es nur auf `apply_success` prüfte, nicht auf `rolled_back`.
  Der nächste Zyklus sah dieselbe erkannte IP und hielt sie fälschlich für
  bereits übernommen — TalkAnchor hätte den zurückgerollten Zustand (mit
  der alten, ggf. nicht mehr aktuellen IP) nie wieder von selbst korrigiert.
  Nach einem zurückgerollten Schreibvorgang zählt jetzt wieder die alte IP
  als aktuell, sodass der nächste Zyklus den Patch-Versuch erneut probiert.

## [0.1.15] - 2026-08-13

### Behoben

- **Live wiederholt beobachtet:** Das Cloudflare-API-Token-Feld im Wizard
  wurde trotz `autocomplete="off"` mehrfach durch ein unpassendes,
  gespeichertes Passwort ersetzt (iOS Safari ignoriert `autocomplete="off"`
  bei `type="password"`-Feldern gezielt und bietet dort eigene
  Passwort-Vorschläge an). Da das Feld für einen selbst gehosteten
  Admin-Bereich ohnehin nicht wirklich geheim gehalten werden muss, ist
  es jetzt ein normales Textfeld (kein `type="password"` mehr, kein
  „Anzeigen"-Umschalter mehr nötig) — damit greift Safaris
  Passwort-Vorschlag hier gar nicht erst.

## [0.1.14] - 2026-08-13

### Behoben

- **Live auf der Henschke-Instanz gefunden:** Nach dem Update auf 0.1.13
  schlug die SSH-Verbindung plötzlich komplett fehl ("not a valid OPENSSH
  private key file"), obwohl derselbe Schlüssel kurz zuvor noch
  funktionierte. Ursache: Der gespeicherte private Schlüssel hatte all
  seine Zeilenumbrüche verloren — vermutlich durch erneutes Speichern
  über Home Assistants generisches Supervisor-Konfigurationsformular,
  das `password`-Felder als einzeilige Box darstellt, auch wenn der Wert
  (ein mehrzeiliger PEM-Schlüssel) das nicht ist. Der Schlüssel wird
  jetzt beim Add-on-Start automatisch wieder ins korrekte 64-Zeichen-PEM-
  Format zurückgewrappt, unabhängig davon, wie er zuletzt gespeichert
  wurde; ergänzend ein deutlicher Hinweis in der Doku, dieses Feld nur
  über den Wizard und nicht über das native HA-Formular zu bearbeiten.
- Die Sofia-Config-Suche im Wizard übernahm bei mehreren gefundenen
  Kandidaten (z. B. "internal" und "external"-Profil) bisher blind den
  ersten — bei der Henschke-Instanz führte das zur falschen Datei
  (`internal.xml` statt der zum konfigurierten Profilnamen passenden
  Datei). Bevorzugt jetzt den Kandidaten, dessen Pfad den konfigurierten
  Profilnamen enthält, und weist bei mehreren Kandidaten ausdrücklich
  darauf hin, die Auswahl zu prüfen.

## [0.1.13] - 2026-08-13

### Behoben

- **Live-Fehler auf der Henschke-Instanz gefunden und behoben:** Nach
  einer echten IP-Änderung schlug das Anwenden fehl mit *"Parameter(s)
  ['ext-sip-ip', 'ext-rtp-ip'] not found in
  /etc/freeswitch/autoload_configs/sofia.conf.xml"*. Ursache: Die
  Sofia-Config-Suche im Wizard fand Kandidaten per Dateiname
  (`sofia*.xml`) und traf damit nur FreeSWITCH's generische
  Loader-Config, die selbst nie die IP-Parameter enthält — diese liegen
  in einer separaten, beliebig benannten Profildatei (z. B.
  `sip_profiles/external_talk.xml`), die die Loader-Config nur einbindet.
  Die Suche durchsucht Dateien jetzt zuerst nach **Inhalt** (welche XML-
  Datei enthält tatsächlich `ext-sip-ip`?) statt nur nach Namen; die alte
  Namenssuche bleibt als Fallback. **Wer betroffen war:** Bitte im Wizard
  bei "Sofia-Config-Pfad suchen" erneut suchen (jetzt korrekt) oder unter
  UniFi Talk (SSH) den Pfad manuell prüfen — die zuletzt erkannte
  IP-Änderung wurde nicht angewendet, UniFi Talk hatte also
  möglicherweise noch die alte IP eingetragen.
- Ein fehlgeschlagenes Anwenden legte trotzdem ein Remote-/Lokal-Backup
  an, bevor der eigentliche Fehler (fehlende Parameter) erkannt wurde —
  bei wiederholten Fehlversuchen (z. B. bei flatternder IP) sammelten
  sich so nutzlose Backup-Dateien auf dem begrenzten Flash-Speicher der
  UDM an. Backup wird jetzt erst unmittelbar vor dem tatsächlichen
  Schreibvorgang angelegt.
- Wiederkehrender `RuntimeError: Event loop is closed`-Traceback beim
  Neustart des `talkanchor run`-Dienstes (u. a. nach jedem
  Wizard-Speichern im Add-on) behoben — der Scheduler wurde nach dem
  Schließen der Event-Loop statt davor heruntergefahren.

## [0.1.12] - 2026-08-13

### Hinzugefügt

- Neuer Schalter **"Cloudflare-Tunnel-Connector-IP als Quelle verwenden"**
  im Setup-Wizard (Schritt 1) und als Konfigurationsoption
  (`cloudflare_enabled`, Standard: an). Manche Cloudflare-Tunnel können
  strukturell nie eine eindeutige IP liefern — z. B. wenn derselbe Tunnel
  gleichzeitig über mehrere WAN-Leitungen verbunden ist (Multi-WAN).
  Bisher blieb der Cloudflare-Verbindungstest in so einem Fall dauerhaft
  rot, ohne Möglichkeit, das bewusst zu übergehen, ohne die eingegebenen
  Zugangsdaten zu löschen. Der neue Schalter lässt Cloudflare komplett
  aus (TalkAnchor läuft dann allein mit der Fallback-Quelle), ohne Token/
  Account-/Tunnel-ID zu verlieren.

## [0.1.11] - 2026-08-13

### Behoben

- Die localStorage-Autospeicherung aus 0.1.10 half nur innerhalb
  desselben Browsers/Tabs — live bestätigt: Werte, die erfolgreich
  gespeichert wurden (in der Add-on-Konfigurationsansicht sichtbar),
  fehlten trotzdem beim erneuten Öffnen des Wizards (z. B. aus einer
  anderen Ingress-Sitzung/App heraus). Der Wizard lädt beim Start jetzt
  zusätzlich die bereits gespeicherte Konfiguration direkt vom Server
  (`GET /api/wizard/prefill`) als Grundlage; ein vorhandener,
  ungespeicherter lokaler Entwurf überschreibt das anschließend nur dort,
  wo tatsächlich neuer eingegeben wurde.

## [0.1.10] - 2026-08-13

### Hinzugefügt

- Der Wizard verlor bisher alle eingegebenen Werte (Cloudflare-Token, IDs,
  UniFi-Host, ...), sobald die Seite neu geladen wurde oder man zwischen
  Schritten navigierte, ohne vorher explizit zu speichern — Werte landeten
  serverseitig erst beim finalen "Speichern"/"GO LIVE". Alle Formularfelder
  werden jetzt bei jeder Änderung automatisch im Browser (localStorage)
  zwischengespeichert und bei erneutem Öffnen des Wizards wiederhergestellt
  (inkl. aktuellem Schritt und Host-Key-Bestätigungsstatus). Der
  Zwischenstand wird erst nach erfolgreichem "GO LIVE" gelöscht.

## [0.1.9] - 2026-08-13

### Behoben

- Die Sofia-Config-Suche schlug live mit "encountered RSA key, expected
  OPENSSH key" fehl, obwohl der neu erzeugte RSA-Schlüssel selbst
  einwandfrei war. Ursache: Paramiko probiert für dieselbe Schlüsseldatei
  nacheinander RSA-, ECDSA- und Ed25519-Klassen durch; lehnt der Server
  die Public-Key-Authentifizierung ab (z. B. weil der öffentliche
  Schlüssel nicht korrekt auf dem UniFi-Gerät hinterlegt wurde), bleibt
  am Ende nur die komplett irreführende Formatfehler-Meldung der
  *letzten* durchprobierten Klasse übrig — hat mit dem eigentlichen
  Problem nichts zu tun. `connect_ssh()` erkennt dieses Muster jetzt und
  gibt stattdessen eine klare Meldung aus: Authentifizierung wurde
  abgelehnt, bitte prüfen, ob der öffentliche Schlüssel vollständig und
  korrekt bei UniFi hinterlegt ist (die rohe Paramiko-Meldung bleibt für
  Debugging-Zwecke erhalten).

## [0.1.8] - 2026-08-13

### Hinzugefügt

- Der SSH-Schritt im Setup-Wizard verlangte bisher, dass man sich selbst
  (z. B. per Terminal-Add-on) einen passphrasefreien Schlüssel erzeugt,
  den öffentlichen Teil manuell bei UniFi hinterlegt und den privaten Teil
  zurück in den Wizard einfügt — für die meisten Nutzer zu viele manuelle
  Schritte über mehrere Apps hinweg. Der Wizard kann den Schlüssel jetzt
  auf Knopfdruck selbst erzeugen (RSA 3072, ohne Passphrase — TalkAnchor
  läuft unbeaufsichtigt und könnte ohnehin nicht danach fragen) und
  schreibt ihn direkt an den richtigen Ort; man bekommt nur noch die
  öffentliche Zeile zum Einfügen bei UniFi zu sehen. Manuelles Einfügen
  eines eigenen Schlüssels bleibt unter "Eigenen Schlüssel einfügen
  (fortgeschritten)" weiterhin möglich.

## [0.1.7] - 2026-08-13

### Behoben

- Der neue "Anzeigen"-Knopf aus 0.1.6 löste das Rätsel sofort: der
  eingefügte Wert begann mit `eyJhIjoi…` — das ist gar kein
  Cloudflare-API-Token, sondern der Base64-kodierte **Tunnel-Connector-
  Token** aus dem `cloudflared tunnel run --token …`-Befehl auf der
  Tunnel-Erstellungsseite. Beide werden von Cloudflare "Token" genannt,
  dienen aber komplett unterschiedlichen Zwecken (Tunnel-Authentifizierung
  vs. REST-API-Zugriff). Der Wizard warnt jetzt direkt am Cloudflare-
  Token-Feld explizit davor und verlinkt den korrekten Weg (My Profile →
  API Tokens → Create Token).

## [0.1.6] - 2026-08-13

### Hinzugefügt

- Die 0.1.5-Bereinigung griff auf dem echten Gerät nicht: der Token blieb
  weiterhin bei 248 statt 40 Zeichen, enthielt also weder ein `Bearer `-
  Präfix noch Leerraum, den man hätte abschneiden können. Da das Feld als
  `type="password"` maskiert war, konnte niemand sehen, was tatsächlich
  eingefügt wurde. Zwei Diagnose-Werkzeuge dafür: ein "Anzeigen"-Knopf
  neben dem Cloudflare-Token-Feld im Wizard, der die Eingabe temporär im
  Klartext zeigt, sowie eine serverseitige, sichere Kurzform des
  empfangenen Tokens in der Fehlermeldung (Länge, erste/letzte 6 Zeichen,
  Hinweis auf nicht-druckbare Zeichen) — ohne den Token vollständig
  preiszugeben.

## [0.1.5] - 2026-08-13

### Behoben

- Der neue Diagnose-Hinweis aus 0.1.4 zeigte live auf einem echten Gerät
  sofort die Ursache: ein eingefügter Cloudflare-Token war 248 statt der
  üblichen 40 Zeichen lang und wurde von Cloudflare mit "Invalid format
  for Authorization header" abgelehnt — typischerweise weil beim Kopieren
  mehr als der Token selbst erfasst wird (z. B. Cloudflares eigenes
  curl-Beispiel mit `Authorization: Bearer <token>` drumherum). Der Wizard
  erkennt jetzt ein eingebettetes `Bearer <token>`-Muster und extrahiert
  daraus automatisch nur den Token; verbleibender Text wird zusätzlich von
  jeglichem Leerraum/Zeilenumbrüchen bereinigt, bevor er gesendet wird.

## [0.1.4] - 2026-08-13

### Hinzugefügt

- Der Cloudflare-Verbindungstest im Setup-Wizard unterscheidet jetzt klar
  zwischen zwei Fehlerursachen: Cloudflare lehnt den API-Token selbst ab
  (per `/user/tokens/verify` geprüft, inkl. Zeichenlänge des empfangenen
  Tokens als Copy-Paste-Sanity-Check) oder der Token ist gültig, hat aber
  keinen Zugriff auf die angegebene Account-/Tunnel-ID. Vorher zeigte der
  Wizard nur die rohe Cloudflare-Fehlermeldung (z. B. Code 9106) ohne
  diese Einordnung.

## [0.1.3] - 2026-08-13

### Behoben

- Dashboard und Setup-Wizard waren unter Home Assistants Ingress-Proxy
  komplett ungestylt und der Wizard-Link/API-Aufrufe liefen ins Leere:
  alle CSS-/JS-/API-Pfade waren absolut (`/static/...`, `/api/...`), was
  unter dem Ingress-Pfadpräfix (`/api/hassio_ingress/<token>/...`) nicht
  auflöst. Jetzt setzt das Backend `<base href>` anhand des von Home
  Assistant gesendeten `X-Ingress-Path`-Headers, alle Links/Requests sind
  relativ. Außerhalb von Ingress (Standalone/Docker) unverändert.

## [0.1.2] - 2026-08-12

### Hinzugefügt

- Geführter Web-Setup-Wizard (`/wizard`), der den CLI-Wizard für
  Umgebungen ohne Terminal spiegelt: Schritte für Cloudflare, Fallback-
  Quelle, UniFi-SSH (inkl. Host-Key-Abruf mit Bestätigung und
  SSH-basierter Sofia-Config-Discovery) und Benachrichtigungen, jeweils
  inline testbar, mit abschließender Zusammenfassung, Dry-Run-Testlauf
  und explizit bestätigtem Scharfschalten. Schreibt im eigenständigen
  Betrieb direkt in `config.yaml` (Hot-Reload ohne Neustart) und im
  Home-Assistant-Add-on über die Supervisor-API in die Add-on-Optionen
  (automatischer Neustart zur Übernahme). Ersetzt den bisherigen
  „Setup-Helfer"-Bereich als primären Einrichtungsweg; dieser bleibt als
  „Diagnose"-Bereich für bereits konfigurierte Deployments erhalten.

## [0.1.1] - 2026-08-12

### Hinzugefügt

- Dashboard-Bereich „Setup-Helfer": SSH-Host-Key abrufen, Sofia-Config-Pfad
  per SSH suchen und die Cloudflare-Verbindung testen — als Web-Ersatz für
  die SSH-Schritte des CLI-Wizards dort, wo kein Terminal zur Verfügung
  steht (insbesondere im Home-Assistant-Add-on).

### Behoben

- Home-Assistant-Add-on-Repository lag zwei statt eine Ebene tief und
  wurde vom Supervisor nicht gefunden ("is not a valid app repository").
- Add-on-Options-Schema markierte Felder mit leerem Standardwert
  fälschlich als Pflichtfelder und blockierte dadurch das Speichern der
  Konfiguration.

## [0.1.0] - 2026-08-12

Erstes Alpha-Release.

### Hinzugefügt

- Reconcile-Loop mit zwei IP-Quellen: Cloudflare-Tunnel-Connector-IP
  (primär) wird gegen einen konfigurierbaren HTTP-Echo-Fallback
  gegengeprüft, beide müssen übereinstimmen, bevor gehandelt wird.
- UniFi-Talk-SSH-Zieladapter: Auth nur per Key mit Host-Key-Prüfung,
  zeitgestempelte Remote- und lokale Backups vor jedem Schreibzugriff,
  Sofia-XML-Patching, `fs_cli` reloadxml/Profil-Neustart,
  `sofia status`-Health-Check-Polling mit automatischem Rollback bei
  Fehlschlag, sowie Rate-Limiting gegen flatternde IPs.
- Dry-Run-Modus, standardmäßig aktiv.
- Austauschbare Benachrichtigungs-Adapter: ntfy, generischer Webhook,
  E-Mail.
- Interaktiver Setup-Wizard (`talkanchor setup`) mit SSH-basierter
  Sofia-Config-Erkennung und expliziter zweiter Bestätigung vor dem
  Scharfschalten.
- `talkanchor`-CLI: `setup`, `check`, `run`, `web`, `rollback`.
- Lokales Web-Dashboard: aktuelle IP, Health-Status, Änderungshistorie,
  Live-Log, manuelle Jetzt-prüfen-/Rollback-auf-Backup-Aktionen.
- Plugin-Architektur (`IPSource`-, `ConfigTarget`-, `Notifier`-Protokolle),
  sodass UniFi Talk ein Referenz-Ziel ist, nicht das einzig mögliche.
- Docker-Image + Compose-Datei; Multi-Arch-Veröffentlichung (amd64/arm64)
  zu GHCR bei getaggten Releases.
- Home-Assistant-Add-on-Wrapper.
- Vollständige Testsuite für den Kern-Reconcile-Loop mit In-Memory-Fakes
  (kein echtes Netzwerk/SSH nötig).

[Unreleased]: https://github.com/martin141089/UniFi-Talk/compare/v0.1.16...HEAD
[0.1.16]: https://github.com/martin141089/UniFi-Talk/compare/v0.1.15...v0.1.16
[0.1.15]: https://github.com/martin141089/UniFi-Talk/compare/v0.1.14...v0.1.15
[0.1.14]: https://github.com/martin141089/UniFi-Talk/compare/v0.1.13...v0.1.14
[0.1.13]: https://github.com/martin141089/UniFi-Talk/compare/v0.1.12...v0.1.13
[0.1.12]: https://github.com/martin141089/UniFi-Talk/compare/v0.1.11...v0.1.12
[0.1.11]: https://github.com/martin141089/UniFi-Talk/compare/v0.1.10...v0.1.11
[0.1.10]: https://github.com/martin141089/UniFi-Talk/compare/v0.1.9...v0.1.10
[0.1.9]: https://github.com/martin141089/UniFi-Talk/compare/v0.1.8...v0.1.9
[0.1.8]: https://github.com/martin141089/UniFi-Talk/compare/v0.1.7...v0.1.8
[0.1.7]: https://github.com/martin141089/UniFi-Talk/compare/v0.1.6...v0.1.7
[0.1.6]: https://github.com/martin141089/UniFi-Talk/compare/v0.1.5...v0.1.6
[0.1.5]: https://github.com/martin141089/UniFi-Talk/compare/v0.1.4...v0.1.5
[0.1.4]: https://github.com/martin141089/UniFi-Talk/compare/v0.1.3...v0.1.4
[0.1.3]: https://github.com/martin141089/UniFi-Talk/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/martin141089/UniFi-Talk/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/martin141089/UniFi-Talk/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/martin141089/UniFi-Talk/releases/tag/v0.1.0

# Sicherheitsrichtlinie

TalkAnchor verbindet sich per SSH mit deinem UniFi-Talk-Gerät und patcht
eine produktive FreeSWITCH-Konfigurationsdatei. Bitte dies vor dem
Einsatz lesen.

## Haftungsausschluss

⚠️ **TalkAnchor ist kein offizielles Ubiquiti-Produkt.** Es verändert eine
Konfigurationsdatei, die von der UniFi-Talk-Anwendung intern verwaltet und
nicht offiziell dokumentiert wird. Nutzung auf eigene Gefahr. Vor dem
ersten scharfen Lauf immer zuerst den Dry-Run-Modus nutzen und ein
aktuelles Backup des UniFi-Systems bereithalten.

## Design-Prinzipien

- **Nur SSH-Key-Authentifizierung.** Es gibt an keiner Stelle im
  Konfigurationsschema ein Passwort-Feld — `talkanchor.config.UniFiTalkTargetConfig`
  besitzt kein solches Feld, und der Wizard fragt nie danach.
- **Host-Key-Prüfung ist zwingend.** Der SSH-Client lehnt unbekannte
  Host-Keys ab (`paramiko.RejectPolicy`) statt Trust-on-First-Use. Vor der
  ersten Nutzung den Host-Key des UDM mit
  `ssh-keyscan -H <host> >> ~/.ssh/known_hosts` hinzufügen.
- **Dry-Run ist Standard.** `dry_run: true` ist der Standardwert in
  `config.yaml`/`.env.example`; das Scharfschalten über den Setup-Wizard
  erfordert eine zweite, explizite `GO LIVE`-Bestätigung.
- **Jeder Schreibzugriff wird vorher gesichert**, sowohl auf dem
  Zielgerät (`unifi_talk.backup_dir_remote`) als auch lokal
  (`<data_dir>/backups`), mit Zeitstempel, bevor irgendeine
  Konfigurationsdatei angefasst wird.
- **Health-Check statt Fire-and-Forget.** Nach einer scharfen Änderung
  fragt TalkAnchor bis zu `health_check_timeout_seconds` lang `sofia
  status` ab, bevor der Erfolg erklärt wird; bei Fehlschlag wird ein
  automatischer Rollback versucht und in beiden Fällen benachrichtigt — nie
  stillschweigend.
- **Rate-Limiting.** `min_seconds_between_changes` verhindert, dass ein
  flatterndes IP-Signal wiederholte Neustarts des SIP-Profils auslöst.
- **Secrets landen nie im Repo oder in Logs.** `config.yaml`/`.env` sind
  per `.gitignore` ausgeschlossen und werden vom Wizard mit `0600`-Rechten
  geschrieben; Log-Ausgaben enthalten nie Token- oder Passwortwerte.

## Empfohlener Scope für das Cloudflare-API-Token

Ein Token erstellen, das ausschließlich auf **Account → Cloudflare Tunnel
→ Read** beschränkt ist. Schreib- oder Zone-Zugriff wird nicht benötigt.

## Sicherheitslücke melden

Bei einem gefundenen Sicherheitsproblem bitte einen
[privaten Security-Advisory](https://github.com/martin141089/UniFi-Talk/security/advisories/new)
öffnen statt eines öffentlichen Issues. Wir antworten so schnell wie
möglich.

## Manuelle Wiederherstellung

Falls ein Backup von Hand wiederhergestellt werden muss (z. B. weil
TalkAnchor selbst gerade nicht läuft): Die Datei ist eine reine
XML-Kopie — per SSH verbinden und zurückkopieren:

```sh
ssh <user>@<udm-host>
cp /root/talkanchor-backups/<file>.bak <pfad-zur-sofia-profil.xml>
fs_cli -x "reloadxml"
fs_cli -x "sofia profile <profilname> restart"
```

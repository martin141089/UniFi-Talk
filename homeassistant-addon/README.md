<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="../assets/logo/wordmark-dark.svg">
    <img src="../assets/logo/wordmark.svg" alt="TalkAnchor" width="320">
  </picture>
</p>

# TalkAnchor — Home-Assistant-Add-on

Dieses Verzeichnis ist eine erste Ebene innerhalb des Haupt-Repositorys, das
gleichzeitig als [Home-Assistant-Add-on-Repository](https://developers.home-assistant.io/docs/add-ons/repository)
dient (`repository.yaml` liegt an der Repo-Wurzel, dieser Ordner enthält
das eigentliche Add-on mit seiner `config.yaml`). Es ist ein schlanker
Wrapper um das eigenständige TalkAnchor-Docker-Image (siehe die
[Repo-Wurzel](..)) für alle, die bereits Home Assistant im Netzwerk
betreiben und TalkAnchor lieber über den Supervisor verwalten möchten als
über ein separates `docker compose`-Deployment.

## Dieses Repository hinzufügen

In Home Assistant: **Settings → Add-ons → Add-on Store → ⋮ → Repositories**,
dann hinzufügen:

```
https://github.com/martin141089/UniFi-Talk
```

Das **TalkAnchor**-Add-on erscheint dann im Store. Konfigurationsdetails
stehen in [DOCS.md](DOCS.md).

Unsicher, ob das Add-on oder das eigenständige Docker-/Compose-Deployment
die richtige Wahl ist? Beides funktioniert — sie laufen mit demselben
Kern; das Add-on bildet seine Options-UI nur auf dieselbe `config.yaml` ab,
die auch die CLI nutzt. Wähle, was besser zur restlichen Verwaltung deines
Netzwerks passt.

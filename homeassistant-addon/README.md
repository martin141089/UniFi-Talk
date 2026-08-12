# TalkAnchor — Home Assistant Add-on

This directory is a [Home Assistant add-on repository](https://developers.home-assistant.io/docs/add-ons/repository).
It's a thin wrapper around the standalone TalkAnchor Docker image (see the
[repo root](..)) for users who already run Home Assistant on their network
and would rather manage TalkAnchor through the Supervisor than a separate
`docker compose` deployment.

## Add this repository

In Home Assistant: **Settings → Add-ons → Add-on Store → ⋮ → Repositories**,
then add:

```
https://github.com/martin141089/UniFi-Talk
```

The **TalkAnchor** add-on will show up in the store. See
[talkanchor/DOCS.md](talkanchor/DOCS.md) for configuration details.

Not sure whether you want the add-on or the standalone Docker/Compose
deployment? Either works — they run the exact same core; the add-on just
maps its options UI onto the same `config.yaml` the CLI uses. Pick whichever
fits how you already manage the rest of your network.

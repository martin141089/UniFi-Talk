# Schlanker Wrapper um das Haupt-TalkAnchor-Image: übersetzt das vom
# Home-Assistant-Supervisor bereitgestellte /data/options.json in eine
# talkanchor config.yaml und führt dann denselben Entrypoint wie das
# eigenständige Docker-Image aus.
FROM ghcr.io/martin141089/unifi-talk:latest

USER root
COPY run.py /run.py

ENTRYPOINT ["python3", "/run.py"]

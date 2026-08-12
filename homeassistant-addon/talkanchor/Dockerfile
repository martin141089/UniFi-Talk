# Thin wrapper around the main TalkAnchor image: translates Home Assistant's
# supervisor-provided /data/options.json into a talkanchor config.yaml, then
# execs the same entrypoint the standalone Docker image uses.
FROM ghcr.io/martin141089/unifi-talk:latest

USER root
COPY run.py /run.py

ENTRYPOINT ["python3", "/run.py"]

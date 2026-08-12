# syntax=docker/dockerfile:1
FROM python:3.12-slim AS builder

WORKDIR /build
COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --no-cache-dir --root-user-action=ignore build && \
    python -m build --wheel -o /dist

FROM python:3.12-slim

LABEL org.opencontainers.image.title="TalkAnchor" \
      org.opencontainers.image.description="Hält UniFi Talk verankert an der aktuellen dynamischen öffentlichen IP." \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.source="https://github.com/martin141089/UniFi-Talk"

RUN groupadd --gid 1000 talkanchor && \
    useradd --uid 1000 --gid talkanchor --shell /bin/bash --create-home talkanchor

COPY --from=builder /dist/*.whl /tmp/
RUN pip install --no-cache-dir --root-user-action=ignore /tmp/*.whl && rm -rf /tmp/*.whl

WORKDIR /app
RUN mkdir -p /app/data && chown -R talkanchor:talkanchor /app

USER talkanchor

VOLUME ["/app/data"]
EXPOSE 8420

ENTRYPOINT ["talkanchor"]
CMD ["run", "--config", "/app/config.yaml"]

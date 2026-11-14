# syntax=docker/dockerfile:1
# Includes TDLib's MTProto proxy support; pin BOT_API_IMAGE to an immutable
# verified digest before production deployments.
ARG BOT_API_IMAGE=ghcr.io/avbor/docker-telegram-bot-api:latest
FROM ${BOT_API_IMAGE}

USER root
RUN apk add --no-cache python3 py3-pip ca-certificates \
    && python3 -m venv /opt/tgws-venv

ENV PATH=/opt/tgws-venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TGWS_DATA_DIR=/var/lib/telegram-bot-api

WORKDIR /src/tgws-botapi
COPY pyproject.toml README.md LICENSE ./
COPY proxy ./proxy
COPY tgws_botapi ./tgws_botapi
RUN pip install --no-cache-dir ".[aiogram]"

WORKDIR /app
COPY --chown=telegram-bot-api:telegram-bot-api examples ./examples

USER telegram-bot-api
ENTRYPOINT ["tgws-botapi"]
CMD ["--help"]

# Build stage: resolve the locked dependencies into a virtualenv.
FROM docker.io/library/python:3.13-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

# App stage: the virtualenv plus the application itself.
FROM docker.io/library/python:3.13-slim

RUN useradd --create-home --uid 1000 odinfo

WORKDIR /app
COPY --from=builder --chown=odinfo:odinfo /app/.venv ./.venv
COPY --chown=odinfo:odinfo odinfo ./odinfo
COPY --chown=odinfo:odinfo odinfoweb ./odinfoweb
COPY --chown=odinfo:odinfo data ./data
# The scripts that keep the data up to date: scraping, schema updates, game data.
COPY --chown=odinfo:odinfo cron.py dbupdate.py refdata_update.py ./
# instance/ holds the config and database, out/ is where the town crier dump lands.
RUN install -d -o odinfo -g odinfo instance out

USER odinfo
ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 5000

ENTRYPOINT ["flask"]
CMD ["--app", "odinfoweb.flask_app", "run", "--host", "0.0.0.0"]
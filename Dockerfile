# BUILDER
FROM dhi.io/python:3.13-debian13-dev AS builder

COPY --from=dhi.io/uv:0 /usr/local/bin/uv \
    /usr/local/bin/uvx /usr/local/bin/

WORKDIR /app
RUN mkdir instance
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

# APP
FROM dhi.io/python:3.13-debian13

WORKDIR /app
COPY --from=builder --chown=nonroot /app/.venv /app/.venv
COPY --from=builder --chown=nonroot /app/instance /app/instance
COPY --chown=nonroot odinfo ./odinfo
COPY --chown=nonroot odinfoweb ./odinfoweb
COPY --chown=nonroot ref-data ./ref-data

ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 5000

ENTRYPOINT ["flask"]
CMD ["--app", "odinfoweb.flask_app", "run", "--host", "0.0.0.0"]

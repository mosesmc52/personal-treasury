FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=America/New_York \
    POETRY_VERSION=1.8.2 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends make ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir "poetry==${POETRY_VERSION}"

# Copy dependency metadata first so Docker can reuse the dependency layer.
COPY pyproject.toml poetry.lock README.md ./
COPY src ./src
COPY config ./config
COPY Makefile ./Makefile
COPY scheduler/run.sh ./run.sh
RUN poetry install --only main --no-ansi
RUN chmod +x /app/run.sh

# The application is intentionally a scheduled, one-shot CLI job.
CMD ["/app/run.sh"]

FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install --no-install-recommends --yes ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN python -m pip install --no-cache-dir .

RUN useradd --create-home --uid 10001 mevad \
    && mkdir -p /app/storage/jobs \
    && chown -R mevad:mevad /app/storage

USER mevad
EXPOSE 8000

CMD ["uvicorn", "mevad_api.app:app", "--host", "0.0.0.0", "--port", "8000"]

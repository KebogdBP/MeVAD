# API Foundation

## Назначение

Пакет `mevad_api` является HTTP adapter поверх независимого `mevad` core:

```text
HTTP client
    ↓
FastAPI / Pydantic schemas
    ↓
MediaAnalyzer port
    ↓
YtDlpAnalyzer adapter
```

Core не импортирует FastAPI, Pydantic Settings, Starlette или Uvicorn.

## Application factory

`create_app()` принимает:

- validated `Settings`;
- `MediaAnalyzer`;
- обнаруженные `RuntimeTools`.

Это позволяет тестам создавать изолированные app instances без environment
mutation, сети и реальных media tools.

Production entry point:

```text
mevad_api.app:app
```

## Конфигурация

Настройки загружаются через `pydantic-settings` с prefix `MEVAD_`:

- environment;
- API host/port;
- docs toggle;
- requirement FFmpeg/FFprobe для readiness;
- remote analyzer feature gate.

`.env.example` содержит только безопасные значения и пустые пути. Реальный
`.env` исключён из Git.

## Health endpoints

### `GET /health/live`

Проверяет только способность процесса отвечать. Не зависит от сети, FFmpeg,
базы данных или внешних платформ.

### `GET /health/ready`

Проверяет:

- импорт и работу core;
- наличие FFmpeg;
- наличие FFprobe.

Если `MEVAD_REQUIRE_MEDIA_TOOLS=true`, отсутствие инструмента возвращает 503.
API-only deployment может отключить это требование.

## Analyzer endpoint

### `POST /api/v1/media/analyze`

Request:

```json
{
  "url": "https://example.com/video"
}
```

Response содержит нормализованные metadata, formats, subtitles и available
actions. Сырые структуры `yt-dlp` наружу не передаются.

Blocking analyzer выполняется через threadpool, поэтому не блокирует event loop
FastAPI.

## Feature gate и SSRF

`MEVAD_ANALYZER_ENABLED=false` по умолчанию. В этом состоянии endpoint
возвращает:

```json
{
  "error": {
    "code": "analyzer_disabled",
    "message": "Remote media analysis is disabled."
  }
}
```

Feature gate не является SSRF-защитой. Включение допустимо только после
размещения analyzer/worker в сетевой песочнице, блокирующей private networks,
metadata endpoints, DNS rebinding и небезопасные redirects.

## Ошибки

API использует стабильный envelope:

```json
{
  "error": {
    "code": "machine_readable_code",
    "message": "Safe user-facing message"
  }
}
```

- invalid source URL → 400;
- upstream analysis failure → 502 без исходных details;
- disabled analyzer → 503;
- Pydantic request validation → 422.

## Версионирование

Product endpoints размещаются под `/api/v1`. Health endpoints остаются вне
version prefix для orchestrator probes.

## Пока не входит

- authentication и rate limits;
- PostgreSQL/Redis;
- durable job storage и worker execution;
- download endpoints;
- request IDs и structured logging;
- CORS policy;
- metrics и tracing;
- worker network sandbox.

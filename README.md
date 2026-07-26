# MeVAD

**MegaDownloader Video & Audio** — единое рабочее пространство для анализа,
скачивания, извлечения, обрезки и преобразования видео и аудио.

> Одна ссылка — все доступные действия с видео и аудио в одном интерфейсе.

## Статус

Backend-фундамент Phase 1–4 завершён. Сейчас проект находится на Phase 5:
интеграция Video & Audio MVP в пользовательский web-сценарий. Возможности
Cutter/GIF из Phase 6 уже реализованы в core и выведены в первый интерфейс, но
сама Phase 6 ещё не закрыта. Уже доступны:

- устанавливаемый Python-пакет `mevad`;
- типизированные доменные модели;
- проверка URL без сетевого доступа;
- базовая защита от localhost и прямых private/reserved IP;
- обнаружение FFmpeg и FFprobe;
- CLI, тесты и автоматические quality gates;
- Smart URL Analyzer через изолированный `yt-dlp` adapter;
- нормализованные форматы, субтитры, playlist metadata и доступные действия.
- single-video downloader с пресетами качества, контейнерами и progress events.
- Audio Extractor для MP3, M4A, Opus и WAV.
- Video Cutter с быстрым и точным режимами.
- GIF & Loop Maker для GIF, WebP, MP4 и WebM.
- FastAPI foundation с health/readiness и versioned API.
- Job System с типизированными задачами, status polling и отменой.
- Worker execution layer с dispatch, progress bridge и per-job storage.
- PostgreSQL job repository с optimistic locking.
- Redis queue с claim/ack и восстановлением in-flight задач.
- bounded retries и Redis dead-letter queue.
- managed FFmpeg subprocess cancellation и hard timeouts.
- изолированный yt-dlp worker subprocess для video/audio jobs.
- streaming download progress через bounded machine protocol.
- PostgreSQL worker leases, heartbeat и selective stale-job recovery.
- unique Redis delivery receipts и stale-ack fencing.
- timestamped Redis claim reaper для crash window до SQL lease.
- delayed exponential retries и transient/permanent error classification.
- transactional PostgreSQL outbox для initial Redis dispatch.
- checksum-verified versioned PostgreSQL migration runner.
- leased TTL cleanup для job workspaces и результатов.
- Linux rlimits для FFmpeg/yt-dlp и дочерних процессов.
- отдельный worker process и локальный Docker Compose stack.
- Next.js web workspace: анализ URL, превью, выбор Video/Audio/Clip/GIF action.
- создание job, polling прогресса и отмена через server-side API proxy.
- контролируемая потоковая выдача готового результата с проверкой job state и TTL.
- responsive SaaS-интерфейс и отдельные frontend quality gates.
- proxy-enforced network sandbox для analyzer и media downloads в Compose.

## Требования

- Python 3.11 или новее;
- Node.js 24 для локальной frontend-разработки;
- FFmpeg и FFprobe в `PATH` либо в переменных из `.env.example`.

## Локальная установка

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

Проверка runtime:

```bash
mevad doctor
```

Безопасная синтаксическая проверка URL:

```bash
mevad validate-url "https://example.com/video"
```

Команда не обращается к сети. DNS и каждый redirect target будут повторно
проверяться в будущем сетевом adapter перед соединением.

Анализ метаданных через `yt-dlp`:

```bash
mevad analyze "https://example.com/video"
```

Эта команда обращается к внешнему URL, но не скачивает медиапоток. На текущем
этапе она предназначена для локального CLI. Её нельзя напрямую публиковать как
web endpoint до добавления сетевой изоляции и проверки всех DNS/redirect
назначений.

Скачивание одного видео:

```bash
mevad download-video "https://example.com/video" \
  --quality 720p \
  --container mp4 \
  --output downloads
```

Доступные качества: `best`, `1080p`, `720p`, `480p`, `360p`. Контейнеры:
`auto`, `mp4`, `mkv`, `webm`. Команда предназначена для локального CLI и
наследует ограничения сетевой безопасности analyzer.

Извлечение аудио:

```bash
mevad extract-audio "https://example.com/video" \
  --codec mp3 \
  --bitrate 192 \
  --output downloads
```

Доступные кодеки: `mp3`, `m4a`, `opus`, `wav`. Bitrate-пресеты для сжатых
форматов: `128`, `192`, `256`, `320` kbps. Для WAV bitrate игнорируется.

Обрезка локального видео:

```bash
mevad cut-video input.mp4 \
  --start 10.5 \
  --end 25 \
  --mode accurate \
  --output downloads
```

`fast` использует stream copy и может начать фрагмент с ближайшего keyframe.
`accurate` перекодирует видео в H.264/AAC для более точных границ.

Создание GIF или loop-ready video:

```bash
mevad make-loop input.mp4 \
  --start 2 \
  --end 7 \
  --format gif \
  --width 640 \
  --fps 15 \
  --quality balanced \
  --speed 1 \
  --output downloads
```

Форматы: `gif`, `webp`, `mp4`, `webm`. Quality presets: `small`, `balanced`,
`high`. Скорость: `0.5`, `1`, `1.5`, `2`.

## API

Локальный запуск:

```bash
uvicorn mevad_api.app:app --host 127.0.0.1 --port 8000
```

Проверки процесса:

```text
GET /health/live
GET /health/ready
```

Контракт analyzer:

```text
POST /api/v1/media/analyze
```

Remote analyzer по умолчанию выключен. `MEVAD_ANALYZER_ENABLED=true` требует
`MEVAD_NETWORK_SANDBOX=external_proxy` и `MEVAD_MEDIA_PROXY_URL`.
Интерактивная документация доступна по `/docs` и отключается через
`MEVAD_API_DOCS_ENABLED=false`.

Job API:

```text
POST /api/v1/jobs
GET  /api/v1/jobs/{job_id}
POST /api/v1/jobs/{job_id}/cancel
GET  /api/v1/jobs/{job_id}/result
```

Result endpoint доступен только для успешно завершённой задачи до истечения TTL.
Он не раскрывает внутренний storage path, проверяет принадлежность файла workspace
задачи и отдаёт результат как attachment с `Cache-Control: private, no-store`.

По умолчанию API использует process-local repository и queue для простых тестов.
Production-intent режим связывает API и worker через PostgreSQL и Redis:

```bash
docker compose up --build
```

После запуска API доступен на `http://localhost:8000`. PostgreSQL хранит job
state, Redis переносит job identifiers, а API и worker используют общий volume
`storage/jobs`. Worker повторяет failed operation до `MEVAD_JOB_MAX_ATTEMPTS`,
после чего переносит exhausted claim в `mevad:jobs:dead`.
Зависший claim без SQL lease автоматически возвращается в ready после
`MEVAD_WORKER_CLAIM_STALE_SECONDS`.
Transient failure ждёт неблокирующий exponential backoff между
`MEVAD_WORKER_RETRY_BASE_SECONDS` и `MEVAD_WORKER_RETRY_MAX_SECONDS`;
permanent failure сразу переносится в dead-letter.
Initial queue publication выполняет отдельный `mevad-outbox` relay: Redis
outage не теряет job и не заставляет API откатывать уже созданный intent.

Web workspace доступен на `http://localhost:3000`. Для запуска отдельно:

```bash
cd apps/web
npm ci
npm run dev
```

Next.js proxy использует `MEVAD_API_INTERNAL_URL` (по умолчанию
`http://127.0.0.1:8000`). В Compose remote analyzer включён внутри
proxy-enforced network sandbox. При локальном запуске он остаётся выключенным,
пока явно не заданы sandbox mode и proxy URL.

Для ручного запуска задайте `MEVAD_JOB_BACKEND=postgres`,
`MEVAD_QUEUE_BACKEND=redis`, database/Redis URLs, затем запустите
`mevad-migrate`, `uvicorn mevad_api.app:app`, `mevad-outbox` и
`mevad-worker`, `mevad-cleanup` отдельно. Migration failure должна
останавливать deployment.

## Проверки

```bash
ruff check .
ruff format --check .
mypy
pytest --cov=mevad --cov=mevad_api --cov=mevad_worker --cov-report=term-missing
cd apps/web
npm run lint
npm run typecheck
npm test
npm run build
```

## Документы

- [Project Vision](MEGADOWNLOADER_PROJECT_VISION.md)
- [Phase 0 — Repository Audit and Cleanup](docs/product/PHASE_0_REPOSITORY_AUDIT_AND_CLEANUP.md)
- [Initial Repository Audit](docs/audits/INITIAL_REPOSITORY_AUDIT.md)
- [Smart URL Analyzer Architecture](docs/architecture/SMART_URL_ANALYZER.md)
- [Video Downloader Architecture](docs/architecture/VIDEO_DOWNLOADER.md)
- [Audio Extractor Architecture](docs/architecture/AUDIO_EXTRACTOR.md)
- [Video Cutter Architecture](docs/architecture/VIDEO_CUTTER.md)
- [GIF and Loop Maker Architecture](docs/architecture/GIF_LOOP_MAKER.md)
- [API Foundation Architecture](docs/architecture/API_FOUNDATION.md)
- [Job System Architecture](docs/architecture/JOB_SYSTEM.md)
- [Worker Execution Architecture](docs/architecture/WORKER_EXECUTION.md)
- [Durable Job Infrastructure](docs/architecture/DURABLE_JOB_INFRASTRUCTURE.md)
- [Managed yt-dlp Worker](docs/architecture/MANAGED_YT_DLP_WORKER.md)
- [Web Workspace](docs/architecture/WEB_WORKSPACE.md)
- [ADR 0023 — Proxy-enforced Network Sandbox](docs/adr/0023-proxy-enforced-network-sandbox.md)

## Планируемая архитектура

```text
Browser
   ↓
Next.js
   ↓
FastAPI
   ├── PostgreSQL
   ├── Redis
   ├── Object Storage
   └── Task Queue
          ↓
      Media Worker
      ├── yt-dlp
      └── FFmpeg
```

Следующий критический инкремент добавит контролируемую выдачу готовых файлов.

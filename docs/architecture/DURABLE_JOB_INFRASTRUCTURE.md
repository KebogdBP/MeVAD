# Durable Job Infrastructure

## Поток данных

```text
POST /api/v1/jobs
        ↓
JobService
        ↓
PostgreSQL transaction
   ├── INSERT jobs
   └── INSERT job_outbox
                ↓
           Outbox relay
                ↓
          LPUSH ready (Redis)
                    ↓
              BRPOPLPUSH
                    ↓
             processing list
                    ↓
               JobExecutor
                    ↓
       version-guarded job updates
                    ↓
             LREM processing
```

PostgreSQL хранит полную модель задачи. Redis переносит только `job_id`, поэтому
повтор broker message не создаёт второй источник истины.

## SQL repository

`SqlJobRepository` реализует тот же синхронный port, что и in-memory adapter:

- `add` выполняет transactional insert;
- `get` восстанавливает immutable domain model;
- `update` содержит `WHERE job_id = ... AND version = expected_version`;
- `rowcount != 1` означает concurrent update.

Тесты используют SQLite через тот же SQLAlchemy Core mapping. Production URL
использует dialect `postgresql+psycopg`.

Начальная PostgreSQL schema находится в
`migrations/0001_create_jobs.sql`. `mevad-migrate` проверяет непрерывную
последовательность файлов и их SHA-256 checksums, затем применяет pending batch
в transaction. Compose не запускает API, worker и outbox до успешного
migration service. `MEVAD_AUTO_CREATE_SCHEMA=true` остаётся только для
ephemeral development/tests.

## Redis delivery

Очередь использует три Redis lists и один sorted set:

- `mevad:jobs` — ready;
- `mevad:jobs:processing` — claimed, но ещё не acknowledged.
- `mevad:jobs:dead` — exhausted after bounded retries.
- `mevad:jobs:delayed` — retry deliveries с Unix timestamp доступности.

Каждый ready payload содержит уникальный `delivery_id`. Worker получает
`JobClaim`, а acknowledge/retry/dead-letter используют полный opaque receipt.
Retry создаёт новый receipt атомарно с перемещением обратно в ready, поэтому
старый worker не может удалить delivery новой попытки.

`BRPOPLPUSH` одновременно забирает oldest ready item и сохраняет его в
processing. Сразу после claim payload атомарно заменяется версией с
`claimed_at`. После завершения worker вызывает `LREM`.

Это at-least-once delivery. PostgreSQL lease отделяет abandoned claim от
активной работы другого worker.

## Worker leases

При старте attempt worker сохраняет:

```text
lease_owner
lease_expires_at
claim_receipt
```

Managed subprocess polling и progress callbacks продлевают deadline с
настраиваемым интервалом. Heartbeat использует optimistic job version и
отклоняется для другого owner или уже просроченной lease.

Runtime периодически выбирает из PostgreSQL только истёкшие non-terminal jobs.
Expired running/processing job получает безопасный `worker_lease_expired`, затем
обычная retry policy возвращает его в ready либо переносит в dead-letter.
`cancel_requested` с истёкшей lease завершается как `cancelled`.

Тот же recovery cycle выбирает Redis claims старше grace period. Claim
возвращается в ready только если SQL job всё ещё `queued` и не успела получить
lease receipt. Terminal/missing jobs и claims, вытесненные другой lease,
очищаются. Активные совпадающие leases reaper не затрагивает.

Настройки:

- `MEVAD_WORKER_LEASE_SECONDS`;
- `MEVAD_WORKER_HEARTBEAT_SECONDS`;
- `MEVAD_WORKER_RECOVERY_INTERVAL_SECONDS`;
- `MEVAD_WORKER_CLAIM_STALE_SECONDS`;
- опциональный `MEVAD_WORKER_ID`.

Legacy queue entries, содержащие только `job_id`, остаются читаемыми во время
rolling upgrade. Новые публикации всегда используют JSON payload с delivery ID.

## Retry policy

Job хранит `attempt_count` и `max_attempts`. Переход `queued → running`
увеличивает attempt atomically вместе с version. Failed result сначала
классифицируется по стабильному `error_code`:

```text
transient && attempt_count < max_attempts
    failed → queued
    processing → delayed → ready

permanent || attempt_count == max_attempts
    processing → dead
```

Задержка растёт как capped exponential backoff. Перемещение exact claim в
sorted set и promotion наступивших deliveries выполняются Redis Lua scripts.
`MEVAD_JOB_MAX_ATTEMPTS` принимает значения 1–10.

Настройки backoff:

- `MEVAD_WORKER_RETRY_BASE_SECONDS` — первая задержка, default 5;
- `MEVAD_WORKER_RETRY_MAX_SECONDS` — потолок, default 300.

## Transactional submission outbox

Production API одной PostgreSQL transaction вставляет job и `job_outbox`
event. Отдельный `mevad-outbox` process арендует pending events, публикует
`job_id` в Redis и отмечает `published_at`. Redis outage больше не превращает
новую job в terminal failure: intent остаётся durable и будет опубликован
после восстановления.

Relay lease переживает process crash. Crash после Redis enqueue, но до
`published_at`, может создать duplicate delivery; lifecycle fencing worker
безопасно его удаляет. Это at-least-once dispatch.

## Worker runtime

Команда `mevad-worker` требует PostgreSQL/Redis backends, общие с API URLs и
общий storage root. SIGINT и SIGTERM останавливают polling loop после текущего
синхронного шага.

## Локальный stack

```bash
docker compose up --build
```

Compose поднимает PostgreSQL, Redis с AOF, API, outbox relay и worker.
API/worker запускаются после healthchecks инфраструктуры и используют общий
named volume результатов.

## Storage retention

Terminal transition назначает `result_expires_at`. Отдельный `mevad-cleanup`
process арендует expired terminal rows, удаляет confined job workspace и
очищает публичный `result_reference`. `storage_deleted_at` отличает истёкший
результат от job, которая никогда не создавала файл.

Настройки:

- `MEVAD_STORAGE_RETENTION_SECONDS`;
- `MEVAD_CLEANUP_POLL_INTERVAL_SECONDS`;
- `MEVAD_CLEANUP_LEASE_SECONDS`;
- `MEVAD_CLEANUP_BATCH_SIZE`.

## Media process limits

Linux worker применяет к каждому FFmpeg/yt-dlp process и descendants:

- `MEVAD_WORKER_CPU_LIMIT_SECONDS`;
- `MEVAD_WORKER_MEMORY_LIMIT_BYTES`;
- `MEVAD_WORKER_FILE_SIZE_LIMIT_BYTES`;
- `MEVAD_WORKER_OPEN_FILES_LIMIT`.

Это дополняет wall-clock timeout и не заменяет container/cgroup limits.

Для ручного обновления schema:

```bash
mevad-migrate
```

## Следующие ограничения

- retry jitter;
- command outbox для retry/dead-letter broker transitions;
- structured metrics and tracing.

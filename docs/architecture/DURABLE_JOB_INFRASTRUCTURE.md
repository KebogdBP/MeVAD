# Durable Job Infrastructure

## Поток данных

```text
POST /api/v1/jobs
        ↓
JobService
   ├── INSERT jobs (PostgreSQL)
   └── LPUSH ready (Redis)
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
`migrations/0001_create_jobs.sql`. Compose монтирует её в init directory.
`MEVAD_AUTO_CREATE_SCHEMA=true` допустим для ephemeral development, но не
заменяет versioned migrations.

## Redis delivery

Очередь использует три Redis lists:

- `mevad:jobs` — ready;
- `mevad:jobs:processing` — claimed, но ещё не acknowledged.
- `mevad:jobs:dead` — exhausted after bounded retries.

`BRPOPLPUSH` одновременно забирает oldest ready item и сохраняет его в
processing. После завершения worker вызывает `LREM`. При restart runtime
возвращает оставшиеся processing entries в ready.

Это at-least-once delivery. Recovery текущего MVP рассчитан на один worker.

## Retry policy

Job хранит `attempt_count` и `max_attempts`. Переход `queued → running`
увеличивает attempt atomically вместе с version. Если executor возвращает
`failed`:

```text
attempt_count < max_attempts
    failed → queued
    processing → ready

attempt_count == max_attempts
    processing → dead
```

Перемещения claim выполняются Redis Lua script как одна операция. Настройка
`MEVAD_JOB_MAX_ATTEMPTS` принимает значения 1–10 и применяется при создании
новой задачи.

## Ошибка публикации

Сначала создаётся durable job, затем публикуется queue message. Если Redis
недоступен, job переводится в `failed`, сохраняется `job_enqueue_failed`, а API
отвечает `503 job_queue_unavailable`. Полностью атомарная гарантия между
PostgreSQL и Redis потребует transactional outbox.

## Worker runtime

Команда `mevad-worker` требует PostgreSQL/Redis backends, общие с API URLs и
общий storage root. SIGINT и SIGTERM останавливают polling loop после текущего
синхронного шага.

## Локальный stack

```bash
docker compose up --build
```

Compose поднимает PostgreSQL, Redis с AOF, API и worker. API/worker запускаются
после healthchecks инфраструктуры и используют общий named volume результатов.

## Следующие ограничения

- per-worker lease и heartbeat;
- безопасное recovery при нескольких workers;
- retry backoff и transient/permanent error classification;
- transactional outbox;
- migration runner;
- result TTL/cleanup scheduler;
- structured metrics and tracing.

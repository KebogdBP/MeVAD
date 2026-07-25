# Job System

## Назначение

Job System отделяет короткий HTTP request от длительной media operation:

```text
POST /api/v1/jobs
        ↓
JobService
        ↓
JobRepository
        ↓
queued job
        ↓
future worker
```

Domain, repository contract и HTTP lifecycle дополнены отдельным
`JobExecutor`. Process-local API repository пока не связан с отдельным worker
process: для этой границы нужны PostgreSQL/Redis adapters.

## Операции

- `download_video`;
- `extract_audio`;
- `cut_video`;
- `make_loop`.

Каждая операция имеет собственную Pydantic options schema. API использует
discriminated union по полю `operation`, поэтому параметры одной операции
нельзя случайно передать другой.

## Состояния

```text
queued
  ├── running
  │     ├── processing
  │     │     ├── succeeded
  │     │     ├── failed
  │     │     └── cancel_requested
  │     ├── succeeded
  │     ├── failed
  │     └── cancel_requested
  └── cancelled

cancel_requested
  ├── cancelled
  └── failed
```

Terminal states:

- `succeeded`;
- `failed`;
- `cancelled`.

Queued job отменяется сразу. Для running/processing job API выставляет
`cancel_requested`; worker обязан остановить операцию и вызвать cancellation
acknowledgement.

## Модель Job

- UUID-compatible opaque `job_id`;
- operation;
- normalized source URL;
- immutable parameters;
- status;
- progress 0–100;
- UTC created/updated timestamps;
- monotonic version;
- result reference;
- safe error code/message.

Progress может только увеличиваться и до terminal success не достигает 100.
`succeed()` атомарно устанавливает 100.

## Repository contract

```text
add(job)
get(job_id)
update(job, expected_version)
```

Update использует optimistic concurrency. Несовпадение version не должно
незаметно перезаписывать новое состояние.

`InMemoryJobRepository`:

- потокобезопасен внутри одного Python process;
- использует `RLock`;
- не переживает restart;
- не разделяется между несколькими API replicas;
- предназначен только для тестов и разработки.

Production adapter должен использовать PostgreSQL transaction/row version.

## HTTP API

### Создание

```http
POST /api/v1/jobs
```

Пример:

```json
{
  "operation": "download_video",
  "source_url": "https://example.com/video",
  "options": {
    "quality": "720p",
    "container": "mp4"
  }
}
```

Ответ 201 содержит queued job. URL проходит core normalization до сохранения.

### Получение

```http
GET /api/v1/jobs/{job_id}
```

Клиент использует polling до terminal state. SSE/WebSocket появятся после
worker.

### Отмена

```http
POST /api/v1/jobs/{job_id}/cancel
```

- queued → cancelled;
- running/processing → cancel_requested;
- terminal → 409.

## Следующий adapter

Production Job System потребует:

- PostgreSQL job repository;
- Redis broker/queue;
- отдельный worker process;
- job claim/lease и heartbeat;
- retry policy;
- stale-job recovery;
- TTL результата;
- idempotency keys;
- per-user quotas;
- structured job events.

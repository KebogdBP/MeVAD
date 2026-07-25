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
Redis queue
        ↓
worker
```

Domain, repository contract и HTTP lifecycle дополнены `JobExecutor`,
PostgreSQL repository, Redis queue и отдельным worker process.

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
- attempt count и immutable max attempts;
- internal worker lease owner/deadline;
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

`SqlJobRepository` использует PostgreSQL transaction и row version.

Failed job может вернуться в `queued`, пока `attempt_count < max_attempts`.
После исчерпания попыток Redis claim переносится в dead-letter list.

Lease metadata остаётся internal и не входит в `JobResponse`. Heartbeat
продлевает deadline только для текущего owner; expired jobs восстанавливаются
selective SQL query, а не глобальным replay processing queue.

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

Клиент использует polling до terminal state. SSE/WebSocket появятся позже.

### Отмена

```http
POST /api/v1/jobs/{job_id}/cancel
```

- queued → cancelled;
- running/processing → cancel_requested;
- terminal → 409.

## Следующий инкремент

Production Job System потребует:

- claim-to-lease gap recovery;
- retry backoff и error classification;
- stale-job recovery;
- TTL результата;
- idempotency keys;
- per-user quotas;
- structured job events.

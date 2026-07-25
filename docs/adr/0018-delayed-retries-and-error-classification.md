# ADR 0018: Delayed retries and error classification

## Статус

Принято.

## Контекст

Немедленный повтор transient failure создаёт tight retry loop, усиливает
upstream outage и несправедливо занимает worker. Permanent ошибки вроде
неверных параметров повтором не исправляются. Блокирующий `sleep` внутри
runtime неприемлем: один job остановил бы polling всей очереди.

## Решение

- Transient codes: `job_execution_failed`, `job_timed_out`,
  `worker_lease_expired`.
- Неверные параметры, unsupported media, отсутствующий runtime tool,
  cancellation и неизвестные codes считаются permanent.
- Retry разрешён только transient failure с оставшимися attempts.
- Delay равен `base × 2^(attempt_count−1)` с configurable maximum.
- Defaults: 5 и 300 секунд.
- Redis атомарно перемещает exact claim в `mevad:jobs:delayed` sorted set.
- Перед poll наступившие deliveries атомарно переносятся в ready list.
- In-memory adapter реализует ту же семантику через injected UTC clock.

Настройки: `MEVAD_WORKER_RETRY_BASE_SECONDS` и
`MEVAD_WORKER_RETRY_MAX_SECONDS`.

## Последствия

Worker не блокируется во время backoff, Redis AOF сохраняет delayed deliveries,
а permanent failure сразу попадает в dead-letter.

Jitter пока отсутствует. Между SQL transition `failed → queued` и Redis move в
delayed остаётся dual-write window; claim reaper восстановит job, но может
обойти задержку. Полное устранение окна требует transactional outbox или
единого durable broker/state protocol.

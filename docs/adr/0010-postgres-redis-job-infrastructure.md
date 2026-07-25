# ADR 0010: PostgreSQL state and Redis delivery

## Статус

Принято.

## Контекст

API и worker должны разделять job state между процессами. Process-local
repository и queue теряют данные при restart и не подходят для нескольких
реплик.

## Решение

- PostgreSQL является source of truth для `Job`.
- SQLAlchemy Core реализует repository port и version-guarded update.
- Redis list хранит только opaque `job_id`, но не дублирует job payload.
- Claim атомарно перемещает ID из ready list в processing list.
- Worker подтверждает claim после terminal handling.
- При старте single-worker runtime возвращает старые processing entries в
  ready list.
- In-memory adapters остаются default для unit tests и локальных smoke tests.

## Последствия

API и worker теперь могут быть отдельными процессами. Доставка имеет
at-least-once semantics, поэтому stale/duplicate queue entries считаются
нормальными. Текущая recovery-модель рассчитана на один worker; перед
горизонтальным масштабированием нужны per-claim lease, heartbeat и worker
identity.

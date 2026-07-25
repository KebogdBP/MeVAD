# ADR 0011: Bounded retries and dead-letter delivery

## Статус

Принято.

## Контекст

Transient media/network failure не должен требовать ручного пересоздания job,
но бесконечный retry расходует CPU, bandwidth и storage. Retry policy должна
сохраняться вместе с job и переживать restart API/worker.

## Решение

- `attempt_count` увеличивается атомарно при `queued → running`.
- `max_attempts` фиксируется при создании job и ограничен диапазоном 1–10.
- Failed job с оставшимися попытками сбрасывается в `queued`.
- Redis Lua script атомарно перемещает claim из processing обратно в ready.
- Exhausted claim тем же способом перемещается в `mevad:jobs:dead`.
- Успешные и отменённые задачи не повторяются.

## Последствия

Worker обеспечивает bounded at-least-once execution и сохраняет exhausted
записи для диагностики. Backoff пока отсутствует: retries возвращаются в конец
FIFO-потока сразу. Классификация transient/permanent ошибок и delayed sorted-set
queue остаются следующим улучшением.

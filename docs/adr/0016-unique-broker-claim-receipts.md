# ADR 0016: Unique broker claim receipts

## Статус

Принято.

## Контекст

Redis processing list раньше содержал только `job_id`. После lease recovery
старая и новая попытки имели одинаковый payload. Поздно оживший worker мог
выполнить `LREM job_id` и удалить claim новой попытки.

## Решение

- Ready payload содержит `job_id` и уникальный `delivery_id`.
- `dequeue()` возвращает immutable `JobClaim(job_id, receipt)`.
- Полный raw payload является opaque receipt для exact Redis operations.
- SQL lease сохраняет receipt текущей попытки.
- Retry атомарно удаляет old receipt и создаёт новый delivery receipt.
- Ack/dead-letter используют exact receipt, а не `job_id`.
- Legacy plain `job_id` payload читается как self-receipt для rolling upgrade.

## Последствия

Stale worker больше не может подтвердить или переместить delivery новой
попытки. Crash между Redis claim и записью SQL lease всё ещё оставляет unleased
processing entry; для него нужен timestamped claim reaper.

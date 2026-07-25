# ADR 0015: PostgreSQL worker leases and heartbeats

## Статус

Принято.

## Контекст

Redis processing list показывает, что message был claimed, но не доказывает,
что worker жив. Глобальный recovery processing list при старте одного worker
может повторно запустить активную задачу другого worker.

## Решение

- `queued → running` атомарно сохраняет `lease_owner` и `lease_expires_at`.
- Managed process polling и progress events вызывают throttled heartbeat.
- Heartbeat проверяет owner, допустимый state и непросроченный deadline.
- Terminal, cancellation и retry transitions очищают lease.
- Repository выбирает только non-terminal jobs с истёкшим deadline.
- Runtime переводит expired job в failed, затем применяет обычную bounded retry
  или dead-letter policy.
- Active leases других workers никогда не восстанавливаются.
- Lease metadata не публикуется в пользовательском API.

## Последствия

Несколько workers используют selective recovery без глобального startup replay.
Unique receipts отдельно fence stale acknowledgements. Остаётся узкое окно
между Redis claim и созданием SQL lease; его закроет broker claim timestamp.

# ADR 0019: Transactional job submission outbox

## Статус

Принято.

## Контекст

API раньше сначала вставлял job в PostgreSQL, затем публиковал `job_id` в Redis.
Отказ Redis оставлял durable job без delivery либо требовал переводить её в
terminal failure. Распределённой transaction между PostgreSQL и Redis нет.

## Решение

- В production JobService не публикует initial delivery напрямую.
- Job и `job_outbox` event вставляются одной PostgreSQL transaction.
- API возвращает queued job после durable commit, независимо от доступности
  Redis.
- Отдельный `mevad-outbox` relay арендует pending events ограниченными leases.
- Relay публикует `job_id` в Redis и только затем отмечает event published.
- При Redis failure lease освобождается для немедленного следующего прохода.
- При crash relay lease истекает и event становится доступен другому instance.
- Outbox delivery имеет at-least-once семантику; duplicate безопасно
  отбрасывается worker lifecycle fencing.

## Последствия

Initial job больше не теряется в окне между SQL commit и Redis publish.
PostgreSQL хранит attempt count, lease и sanitized last error relay.

Crash после Redis publish, но до `published_at`, создаёт duplicate delivery.
Это ожидаемая цена at-least-once outbox.

Outbox этого ADR покрывает initial submission. Retry transition всё ещё
координирует SQL state и exact Redis processing receipt двумя durable
операциями; claim reaper гарантирует восстановление, но может обойти backoff.
Устранение этого остаточного окна потребует command outbox для broker
transitions или переноса lifecycle в единый durable broker protocol.

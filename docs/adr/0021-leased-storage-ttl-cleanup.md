# ADR 0021: Leased storage TTL cleanup

## Статус

Принято.

## Контекст

Worker workspaces содержат results, partial downloads и intermediate files.
Без bounded retention общий volume растёт неограниченно. Удаление по filesystem
mtime небезопасно: cleaner может принять активную долгую job за старую.

## Решение

- Первый terminal transition сохраняет `result_expires_at`.
- Default retention — 86400 секунд, диапазон 60–2592000.
- Retry очищает прежний expiry и `storage_deleted_at`.
- `mevad-cleanup` выбирает только expired terminal jobs.
- Cleaner instances арендуют rows через bounded cleanup leases.
- Lease увеличивает job version и блокирует lifecycle update, поэтому retry не
  может начаться одновременно с удалением.
- Удаляется только confined `{storage_root}/{safe_job_id}` path.
- Symlinked root отвергается; отсутствующий root считается уже удалённым.
- Затем repository очищает `result_reference` и сохраняет
  `storage_deleted_at`.
- После безопасной filesystem ошибки lease освобождается для повтора.

## Последствия

Storage usage ограничивается retention policy, active jobs не зависят от
filesystem timestamps, несколько cleaner replicas не обрабатывают один row
одновременно.

Filesystem delete и SQL completion не образуют общую transaction. Crash после
удаления до SQL update приводит к идемпотентному повтору после lease expiry.
Cleanup lease следует настраивать выше ожидаемого времени удаления большого
workspace.

# ADR 0009: Worker Dispatch and Per-Job Workspaces

**Статус:** accepted
**Дата:** 2026-07-25

## Контекст

Job state machine требует исполнителя, который повторно использует core
adapters, передаёт progress и не смешивает временные файлы разных задач.

## Решение

- Создать отдельный package `mevad_worker`.
- Выполнять dispatch по `JobOperation`.
- Для cut/loop сначала скачивать source в intermediate directory.
- Использовать отдельные per-job intermediate/results directories.
- Публиковать только relative result reference.
- Масштабировать progress для одно- и двухэтапных операций.
- Читать cancellation из актуального job state.
- Очищать intermediate storage в `finally`.
- Преобразовывать expected failures в безопасную job error.

## Последствия

Worker behavior полностью тестируется без сети и реальных media tools. Для
отдельного worker process пока отсутствуют durable repository и broker.
Следующий infrastructure increment должен связать API и worker через
PostgreSQL/Redis с atomic claim и lease semantics.

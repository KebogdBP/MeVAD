# ADR 0008: Explicit Job State Machine

**Статус:** accepted
**Дата:** 2026-07-25

## Контекст

Download, FFmpeg и playlist operations не должны выполняться внутри HTTP
request. API и worker нуждаются в общем контракте состояния и отмены.

## Решение

- Создать immutable `Job` domain model.
- Зафиксировать явные lifecycle states и terminal states.
- Выполнять переходы только через `JobService`.
- Использовать monotonic progress и version.
- Определить optimistic `JobRepository` contract.
- Добавить thread-safe in-memory reference adapter.
- Опубликовать create/get/cancel endpoints.
- Не запускать media operations в API process.

## Последствия

HTTP lifecycle можно разрабатывать и тестировать до подключения Redis и
PostgreSQL. In-memory jobs теряются при restart и не подходят для production.
Worker integration должна реализовать claim, heartbeat, cancellation
acknowledgement и durable result references.

# ADR 0007: FastAPI as a Separate Adapter

**Статус:** accepted
**Дата:** 2026-07-25

## Контекст

После формирования downloader core проекту нужен versioned HTTP contract, но
долгие media operations нельзя выполнять напрямую в request lifecycle.

## Решение

- Создать отдельный Python package `mevad_api`.
- Использовать FastAPI app factory и Pydantic Settings.
- Инжектировать core ports и runtime discovery через app state/dependencies.
- Добавить liveness/readiness endpoints.
- Опубликовать только analyzer contract на первом шаге.
- Выполнять blocking analyzer в threadpool.
- Держать remote analyzer выключенным по умолчанию до SSRF network sandbox.
- Не добавлять download/cut endpoints до Job System.

## Последствия

API можно тестировать без сети и внешних процессов, а core остаётся
framework-independent. Analyzer endpoint существует как стабильный контракт,
но production feature остаётся закрытой. Следующий архитектурный шаг —
PostgreSQL/Redis-backed Job System и отдельный worker.

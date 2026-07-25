# ADR 0003: Typed Single-Video Downloads

**Статус:** accepted
**Дата:** 2026-07-25

## Контекст

Video Downloader должен поддерживать простой выбор качества и контейнера,
передавать прогресс будущему worker и не раскрывать пользователю произвольные
аргументы `yt-dlp`.

## Решение

- Создать отдельный `VideoDownloader` port.
- Принимать immutable `VideoDownloadRequest`.
- Ограничить качество и контейнер enum-пресетами.
- Строить format selector внутри core.
- Использовать callbacks для progress events.
- Принимать read-only cancellation token.
- Проверять итоговый output path и существование файла.
- Не обрабатывать плейлисты в single-video операции.

## Последствия

CLI и будущий worker используют один контракт, а пользовательский ввод не
попадает в shell или произвольную format expression. Новые пресеты требуют
явного изменения enum, planner и тестов. Полноценная отмена внешнего процесса,
квоты и TTL будут реализованы на уровне job worker.

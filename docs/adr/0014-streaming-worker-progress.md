# ADR 0014: Bounded streaming worker progress

## Статус

Принято.

## Контекст

Managed yt-dlp subprocess обеспечивал cancellation и timeout, но job видел
только started/completed. Чтение всего stdout через `communicate()` также не
позволяло обрабатывать progress до завершения процесса.

## Решение

- stdout и stderr дренируются отдельными reader threads.
- Machine callbacks выполняются только в основном worker thread.
- Capture ограничен одним мегабайтом на stream во время чтения.
- Одна прочитанная порция ограничена 64 KiB.
- yt-dlp получает фиксированные `download:` и `postprocess:` templates.
- Parser принимает только строки с `MEVAD_PROGRESS=`/`MEVAD_PROCESSING=`.
- Missing/NA numeric fields преобразуются в `None`.

## Последствия

Job progress обновляется во время загрузки, а processing state появляется при
postprocessing. Ошибка callback завершает process group. Reader threads не
выполняют database calls и не могут скрыть исключение progress bridge.

# ADR 0004: Typed Audio Extraction

**Статус:** accepted
**Дата:** 2026-07-25

## Контекст

Audio extraction требует скачивания исходного потока и запуска FFmpeg, но
пользовательский интерфейс не должен раскрывать codec-specific параметры или
произвольные аргументы внешних инструментов.

## Решение

- Создать отдельный `AudioExtractor` port.
- Поддержать MP3, M4A, Opus и WAV как enum.
- Поддержать фиксированные bitrate presets.
- Не передавать bitrate для WAV.
- Выбирать совместимый source stream, когда это возможно.
- Настраивать `FFmpegExtractAudio` только внутри adapter.
- Повторно использовать общий progress/cancellation contract.
- Проверять итоговый файл и containment output directory.

## Последствия

CLI и будущий worker получают стабильный типизированный контракт. Добавление
нового кодека требует явного изменения моделей, selector, postprocessor tests
и пользовательской документации. Advanced FFmpeg options пока намеренно не
поддерживаются.

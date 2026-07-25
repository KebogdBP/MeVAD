# ADR 0002: yt-dlp Adapter Boundary

**Статус:** accepted
**Дата:** 2026-07-25

## Контекст

Smart URL Analyzer должен использовать возможности `yt-dlp`, не связывая
модели core с нестабильным словарём metadata внешней библиотеки.

## Решение

- Добавить `MediaAnalyzer` protocol в core.
- Инкапсулировать `yt-dlp` в `YtDlpAnalyzer`.
- Использовать официальный embedding API `extract_info(..., download=False)`.
- Нормализовать metadata в immutable dataclasses.
- Преобразовывать внешние ошибки в доменные исключения.
- Подменять клиент factory в unit-тестах и не использовать сеть.
- Не подключать adapter к публичному API до сетевой изоляции SSRF.

## Последствия

Core не зависит от CLI, FastAPI или структуры сырого `yt-dlp` info dict.
Обновления `yt-dlp` требуют проверки adapter tests и отдельного dependency PR.
Полная SSRF-защита переносится на инфраструктурную сетевую границу, поскольку
одной проверки исходного URL недостаточно.

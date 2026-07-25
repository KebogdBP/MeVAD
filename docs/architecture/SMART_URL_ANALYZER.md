# Smart URL Analyzer

## Назначение

Analyzer получает удалённый HTTP(S) URL, извлекает metadata без загрузки
медиапотока и возвращает нормализованный `MediaAnalysis`.

```text
CLI / future API
       ↓
MediaAnalyzer port
       ↓
YtDlpAnalyzer adapter
       ↓
yt-dlp extract_info(download=False)
       ↓
normalized MediaAnalysis
```

## Контракт

Результат содержит:

- extractor и media ID;
- заголовок, автора, длительность и thumbnail;
- canonical webpage URL;
- признак и размер плейлиста;
- доступные форматы;
- языки обычных и автоматических субтитров;
- действия, доступные для обнаруженного медиа.

Форматы не передаются наружу как необработанные словари `yt-dlp`. Adapter
преобразует их в стабильные типизированные модели core.

## Параметры yt-dlp

- `download=False` и `skip_download=True` запрещают скачивание медиапотока;
- `extract_flat="in_playlist"` не раскрывает каждый элемент плейлиста полностью;
- `playlistend=100` ограничивает первичный объём playlist metadata;
- `socket_timeout=15`, один transport retry и один extractor retry ограничивают
  зависание локального анализа;
- `quiet=True` и `no_warnings=True` не допускают прямой пользовательский вывод
  библиотеки из core.

Версия `yt-dlp` закреплена в `pyproject.toml`, поскольку поведение extractors и
security fixes меняются между релизами.

## Ошибки

Исключения внешней библиотеки не выходят за adapter boundary. Они преобразуются
в:

- `MediaAnalysisError`;
- `UnsupportedMediaError`;
- `InvalidSourceURLError`.

Текст ошибки не должен содержать cookies, headers, proxy credentials или
полный debug output внешнего процесса.

## SSRF-модель

Текущий слой `normalize_remote_url` блокирует:

- схемы кроме HTTP(S);
- credentials внутри URL;
- localhost;
- прямые private, loopback, link-local и reserved IP.

`yt-dlp` самостоятельно выполняет DNS, redirects и дополнительные extractor
requests, поэтому публичный analyzer выполняется через отдельную сетевую
песочницу:

- без доступа к loopback и private networks;
- без доступа к cloud metadata endpoints;
- с разрешённым только исходящим HTTP(S);
- с DNS и redirect policy на уровне Squid proxy;
- с таймаутом и лимитом количества запросов;
- без пользовательских `netrc`, config files и произвольных external
  downloaders.

В Compose API и worker находятся во внутренней сети без прямого internet
route. Egress proxy подключён одновременно к внутренней и внешней сети,
проверяет destination каждого HTTP/HTTPS соединения и блокирует non-global
диапазоны. Analyzer fail-closed: его нельзя включить без proxy sandbox и proxy
URL. Вне Compose команда `mevad analyze` остаётся локальным developer/CLI
инструментом.

## Тестирование

Unit-тесты используют fake `YoutubeDLClient` и не обращаются к сети. Реальные
platform tests должны быть отдельными, опциональными и использовать
разрешённые test fixtures.

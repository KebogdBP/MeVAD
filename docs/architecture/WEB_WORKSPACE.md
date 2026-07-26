# Web Workspace

## Назначение

Первый web-инкремент превращает backend-возможности MeVAD в единый
пользовательский сценарий:

```text
URL → анализ → превью → выбор действия → job → прогресс/отмена → скачивание
```

Интерфейс построен на Next.js App Router и использует server-side proxy
`/api/backend/*`. Браузер не получает внутренний адрес FastAPI, а в Docker
Compose web-контейнер обращается к API по имени сервиса `api`.

## Границы текущего инкремента

- URL Analyzer и карточка метаданных;
- Video, Audio, Clip и GIF/Loop actions;
- настройки формата, доступного качества и интервала;
- приблизительная оценка размера Video и Audio до запуска job;
- Cutter fast/accurate modes с source-aware interval validation;
- GIF/Loop controls для format, width, FPS, quality, speed и repeat;
- preview metadata и приблизительный размер GIF/Loop результата;
- создание job, polling статуса и отмена;
- same-origin скачивание успешно завершённого результата;
- responsive интерфейс и базовые accessibility states;
- production standalone build;
- отдельные lint, typecheck, unit test и build gates в CI.

Remote analyzer остаётся выключенным по умолчанию для локального запуска.
Compose включает его только вместе с proxy-enforced network sandbox, который
проверяет destination каждого соединения. UI корректно показывает backend
error, если безопасный analyzer не активирован.

## Runtime

```text
Browser
   ↓ /api/backend/*
Next.js server
   ↓ /api/v1/*
FastAPI
   ↓
PostgreSQL + Redis + Worker
```

Next.js proxy сохраняет `Content-Disposition`, content metadata и защитные
заголовки result response. Для большого файла proxy не применяет обычный
30-секундный request timeout и передаёт response body потоково.

`GET /api/v1/jobs/{job_id}/result` использует непрогнозируемый job identifier как
временную capability текущего безаккаунтного MVP. API выдаёт файл только если job
успешен, TTL не истёк, cleanup не удалил storage и persisted reference указывает
на обычный файл внутри `<job_id>/results`. Traversal, cross-job reference и
symbolic links отклоняются. В версии с аккаунтами capability должна быть дополнена
проверкой владельца или короткоживущей подписью.

Video quality presets строятся из реально обнаруженных analyzer heights.
Приблизительный video size складывает размер выбранного видеопотока с лучшим
известным аудиопотоком, если источник требует merge. Audio size рассчитывается
по duration и выбранному bitrate; для WAV используется ориентир PCM 44.1 kHz
stereo. Если analyzer не вернул достаточно metadata, UI показывает
`Size unavailable`, а не выдуманное число.

Cutter и GIF/Loop валидируются в браузере до создания job теми же продуктовыми
границами, которые зафиксированы в FastAPI schema: end позже start и не выходит
за duration источника, GIF/WebP не длиннее 30 секунд и не выше 30 FPS, video
loop не длиннее 120 секунд. Backend остаётся окончательной границей доверия.
Preview показывает длительность, режим обработки или render settings. GIF/Loop
size — эвристика по разрешению, FPS, длительности, формату и quality preset,
поэтому интерфейс явно обозначает её как приблизительную.

Переменная `MEVAD_API_INTERNAL_URL` задаёт адрес FastAPI для Next.js server.
По умолчанию используется `http://127.0.0.1:8000`, в Compose —
`http://api:8000`.

## Следующие продуктовые разрывы

1. component/integration tests с эмуляцией API;
2. локальная загрузка файлов;
3. SEO landing pages и Advanced Mode.

## Dependency risk

Next.js 16.2.12 фиксировал уязвимые транзитивные версии `postcss` и `sharp`.
Проект использует совместимые overrides `postcss@8.5.23` и `sharp@0.35.0`;
`npm audit --omit=dev --audit-level=high` входит в CI и подтверждает отсутствие
известных production-уязвимостей.

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
- простые настройки формата, качества и интервала;
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

Переменная `MEVAD_API_INTERNAL_URL` задаёт адрес FastAPI для Next.js server.
По умолчанию используется `http://127.0.0.1:8000`, в Compose —
`http://api:8000`.

## Следующие продуктовые разрывы

1. component/integration tests с эмуляцией API;
2. оценка размера выбранного результата;
3. локальная загрузка файлов;
4. SEO landing pages и Advanced Mode.

## Dependency risk

На момент фиксации `npm audit` сообщает high advisories для транзитивных
`postcss` и `sharp` в Next.js 16.2.12. Предлагаемый npm auto-fix откатывает
Next.js до несовместимой версии 9.3.3, поэтому он не применяется. Версии
зафиксированы lockfile; advisory нужно пересмотреть при следующем совместимом
релизе Next.js.

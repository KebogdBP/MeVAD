# Web Workspace

## Назначение

Первый web-инкремент превращает backend-возможности MeVAD в единый
пользовательский сценарий:

```text
URL → анализ → превью → выбор действия → job → прогресс/отмена
```

Интерфейс построен на Next.js App Router и использует server-side proxy
`/api/backend/*`. Браузер не получает внутренний адрес FastAPI, а в Docker
Compose web-контейнер обращается к API по имени сервиса `api`.

## Границы текущего инкремента

- URL Analyzer и карточка метаданных;
- Video, Audio, Clip и GIF/Loop actions;
- простые настройки формата, качества и интервала;
- создание job, polling статуса и отмена;
- responsive интерфейс и базовые accessibility states;
- production standalone build;
- отдельные lint, typecheck, unit test и build gates в CI.

Remote analyzer остаётся выключенным по умолчанию. Его нельзя включать в
публичном окружении до network sandbox, который проверяет DNS resolution и
каждый redirect target. Поэтому текущий UI корректно показывает backend error,
если безопасный analyzer ещё не активирован.

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

Переменная `MEVAD_API_INTERNAL_URL` задаёт адрес FastAPI для Next.js server.
По умолчанию используется `http://127.0.0.1:8000`, в Compose —
`http://api:8000`.

## Следующие продуктовые разрывы

1. network sandbox для безопасного remote analyze/download;
2. авторизованная выдача готового результата;
3. component/integration tests с эмуляцией API;
4. локальная загрузка файлов;
5. SEO landing pages и Advanced Mode.

## Dependency risk

На момент фиксации `npm audit` сообщает high advisories для транзитивных
`postcss` и `sharp` в Next.js 16.2.12. Предлагаемый npm auto-fix откатывает
Next.js до несовместимой версии 9.3.3, поэтому он не применяется. Версии
зафиксированы lockfile; advisory нужно пересмотреть при следующем совместимом
релизе Next.js.

# Phase 8.4 — Public launch readiness

**Дата:** 2026-07-27
**Статус:** repository-ready; external deployment and ownership pending

## Что готово в репозитории

- Production Compose overlay с обязательными domain, database URL и secret.
- Caddy `2.11.4` как единственная публичная точка входа на `80/443` с
  автоматическим HTTPS.
- Security headers: HSTS, nosniff, DENY framing, strict referrer policy и
  запрет camera/microphone/geolocation.
- API и web container healthchecks; web readiness fail-closed проверяет API.
- Canonical origin и telemetry/webmaster значения передаются на этапе Next.js
  build, поэтому build не может случайно сохранить локальный origin.
- Опциональные Google и Bing verification meta tags.
- GitHub Actions validation для Compose/Caddy и ручной production smoke.

## Подготовка окружения

1. Скопировать `deploy/production.env.example` в неотслеживаемый
   `deploy/production.env`.
2. Указать реальный `MEVAD_DOMAIN` без схемы и тот же origin с `https://` в
   `NEXT_PUBLIC_SITE_URL`.
3. Сгенерировать длинный PostgreSQL password и отдельно URL-encode его внутри
   `MEVAD_DATABASE_URL`.
4. Оставить telemetry выключенной, пока Privacy Notice не содержит реальный
   provider, регион и retention.
5. При наличии verification tokens вставить только значения токенов, а не
   полные meta tags.

## Запуск

```bash
docker compose \
  -f compose.yaml \
  -f compose.production.yaml \
  --env-file deploy/production.env \
  config --quiet

docker compose \
  -f compose.yaml \
  -f compose.production.yaml \
  --env-file deploy/production.env \
  up -d --build
```

DNS A/AAAA должен указывать на host, а входящие TCP `80/443` и UDP `443` должны
быть доступны Caddy. PostgreSQL, Redis, API и web не публикуются во внешний
интерфейс; dev-порты привязаны только к loopback host.

## Production validation

После deployment:

```bash
cd apps/web
MEVAD_PRODUCTION_URL=https://mevad.example.com npm run test:production-url
```

Тот же audit доступен через GitHub Actions → **Production smoke**. Он проверяет:

- HTTP → HTTPS;
- web/API readiness;
- security headers;
- 10 публичных маршрутов, canonical и Open Graph;
- валидный JSON во всех structured-data blocks;
- robots и sitemap;
- webmaster meta tags, если tokens переданы workflow;
- telemetry allowlist, отсутствие cookie и блокировку media URL.

## Внешние действия, которые нельзя подтвердить из репозитория

| Проверка | Статус | Условие закрытия |
|---|---|---|
| Реальный domain и deployment | pending | URL отвечает и production smoke зелёный |
| Google Search Console ownership | pending | ownership подтверждён в аккаунте |
| Bing Webmaster ownership | pending | ownership подтверждён в аккаунте |
| Rich Results Test | pending | production URL без blocking errors |
| URL Inspection | pending | canonical/indexing подтверждены |
| NVDA + Firefox | pending | ручная AT-матрица пройдена |
| VoiceOver + Safari | pending | ручная AT-матрица пройдена |
| Mobile performance target 75 | pending | повторяемый score ≥75 или принятое exception |

## Решение о готовности

Репозиторий готов к воспроизводимому deployment, но продукт ещё нельзя называть
публично запущенным. Для этого нужны реальный domain/host, юридические реквизиты,
ownership внешних webmaster-сервисов, production URL inspection и закрытие
ручных accessibility/performance исключений.

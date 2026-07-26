# Phase 8 — SEO and Public Launch MVP

**Статус:** in progress (Slices 8.1–8.3 complete; 8.4 repository-ready)

**Входная точка:** commit `802c821`

**Vision:** `MEGADOWNLOADER_PROJECT_VISION.md`, разделы 9, 17, 18 и Phase 8

## Цель

Подготовить MeVAD к безопасной индексации и первым измеримым публичным
пользовательским сценариям. SEO строится вокруг задач пользователя, а не вокруг
неподтверждённых обещаний поддержки конкретных платформ.

## Порядок реализации

### Slice 8.1 — Technical SEO and task landing foundation

- [x] Добавить canonical origin и уникальные metadata для публичных маршрутов.
- [x] Добавить `robots.txt`, `sitemap.xml` и web manifest.
- [x] Подключить единый Open Graph / X social preview.
- [x] Создать первые task-based страницы: video, audio, cutter и GIF.
- [x] Добавить видимый FAQ и соответствующий JSON-LD.
- [x] Добавить CI gate для metadata, canonical, structured data, robots и sitemap.

### Slice 8.2 — Trust and information architecture

- [x] Создать How It Works и Supported Sites.
- [x] Добавить Privacy, Terms, Copyright и acceptable-use positioning.
- [x] Добавить согласованную глобальную навигацию и footer IA.
- [x] Проверить отсутствие thin/duplicate content.

### Slice 8.3 — Measurement and operations

- [x] Зафиксировать privacy-conscious analytics events.
- [x] Добавить Core Web Vitals reporting.
- [x] Подключить error monitoring без утечки media URL.
- [x] Определить dashboards для organic impressions, clicks и conversion.

### Slice 8.4 — Public launch readiness

- [x] Подготовить production Compose overlay, HTTPS ingress и healthchecks.
- [x] Добавить конфигурируемые Google/Bing verification meta tags.
- [x] Добавить post-deploy audit и ручной GitHub Actions smoke workflow.
- [ ] Настроить production domain и deployment.
- [ ] Проверить Search Console / Bing Webmaster ownership.
- [ ] Прогнать Rich Results Test и URL Inspection на production.
- [ ] Закрыть Phase 7 manual AT и mobile performance exceptions.

## Критерии контента

- Страница отвечает одному устойчивому пользовательскому намерению.
- Title, H1, description и canonical уникальны и согласованы.
- Structured data описывает только видимый контент.
- Нет гарантий поддержки платформы без compatibility evidence.
- Legal copy ограничивает сценарий собственным, разрешённым или законно
  используемым контентом.
- Все CTA ведут в единый workspace, а не создают параллельные продуктовые пути.

## Технические gates

- production build;
- sitemap/robots/canonical regression audit;
- structured-data JSON parse;
- Lighthouse SEO и accessibility;
- Storybook accessibility;
- production dependency audit.

## Launch blockers после repository-ready Slice 8.4

- Подтвердить юридическое лицо или оператора продукта и его адрес.
- Опубликовать приватный email для privacy- и copyright-запросов.
- Выбрать применимое право и провести юридическую проверку Terms и Privacy.
- Определить необходимость регистрации designated copyright agent.
- Зафиксировать production-провайдеров, фактическую географию обработки и retention.
- Выбрать telemetry log destination и retention, затем явно включить оба
  telemetry-флага в production.
- Выбрать реальный HTTPS domain/host, заполнить `deploy/production.env` и
  выполнить deployment.
- Получить Google/Bing verification tokens и подтвердить ownership во внешних
  кабинетах.
- Выполнить production Rich Results / URL Inspection и ручную AT-матрицу.
- Поднять mobile performance с release-floor 50 до целевого уровня 75 либо
  оформить отдельное принятое launch exception.

Текущий legal copy намеренно маркирован как public-launch draft и не заявляет
соответствие конкретной юрисдикции или copyright safe-harbor.

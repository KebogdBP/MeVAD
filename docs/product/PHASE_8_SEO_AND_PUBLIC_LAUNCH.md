# Phase 8 — SEO and Public Launch MVP

**Статус:** in progress (Slice 8.1)

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

- [ ] Создать How It Works и Supported Sites.
- [ ] Добавить Privacy, Terms, Copyright и acceptable-use positioning.
- [ ] Добавить согласованную глобальную навигацию и footer IA.
- [ ] Проверить отсутствие thin/duplicate content.

### Slice 8.3 — Measurement and operations

- [ ] Зафиксировать privacy-conscious analytics events.
- [ ] Добавить Core Web Vitals reporting.
- [ ] Подключить error monitoring без утечки media URL.
- [ ] Определить dashboards для organic impressions, clicks и conversion.

### Slice 8.4 — Public launch readiness

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

# Phase 8.2 — Content and trust audit

**Дата:** 2026-07-27
**Статус:** complete for pre-launch implementation

## Результат

Добавлены пять статических информационных маршрутов:

| Маршрут | Устойчивое намерение | Structured data |
|---|---|---|
| `/how-it-works` | Понять продуктовый workflow | `WebPage`, `HowTo` |
| `/supported-sites` | Проверить модель совместимости источников | `WebPage` |
| `/privacy` | Понять обработку URL, jobs, logs и результатов | `WebPage` |
| `/terms` | Увидеть permitted use и запрещённые сценарии | `WebPage` |
| `/copyright` | Понять права и порядок copyright report | `WebPage` |

Каждый маршрут имеет уникальные title, description, H1, canonical и видимый
контент. Все маршруты включены в sitemap и production SEO audit.

## Thin и duplicate content

Автоматический тест требует для каждой информационной страницы:

- уникальные title, description и headline;
- не менее трёх смысловых секций;
- уникальные заголовки секций;
- не менее 1200 символов видимого основного контента;
- description длиной не менее 100 символов.

HowTo JSON-LD формируется из тех же шагов, которые видны пользователю.

## Trust-модель

- Совместимость заявляется для конкретного URL после анализа, а не как вечное
  обещание поддержки платформы.
- Не предлагается передавать cookies, пароли или токены и обходить DRM,
  аутентификацию либо ограничения источника.
- Privacy copy описывает фактические категории обработки, временное хранение и
  local theme preference без неподтверждённой декларации compliance.
- Terms ограничивают использование собственным, разрешённым, public-domain или
  иным законно используемым контентом.
- Copyright policy повторяет состав содержательного notice, но не заявляет
  designated agent или safe-harbor до их фактического оформления.

## Использованные первичные ориентиры

- European Commission, GDPR principles:
  https://commission.europa.eu/law/law-topic/data-protection/information-business-and-organisations/principles-gdpr_en
- FTC, Privacy and Security:
  https://www.ftc.gov/business-guidance/privacy-security
- U.S. Copyright Office, Section 512:
  https://www.copyright.gov/512/
- U.S. Copyright Office, designated agents:
  https://www.copyright.gov/onlinesp/

Эти источники использованы как ориентиры для минимизации, прозрачности и
структуры copyright report. Они не заменяют юридическую проверку.

## Открытые launch blockers

1. Юридический оператор, адрес и применимое право не подтверждены.
2. Приватные privacy/copyright контакты не опубликованы.
3. Production-провайдеры, география обработки и фактическая retention policy
   ещё не зафиксированы.
4. Не принято решение о designated copyright agent.
5. До закрытия этих пунктов legal-страницы остаются явно маркированными
   pre-launch drafts.

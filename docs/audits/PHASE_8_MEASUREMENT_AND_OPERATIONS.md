# Phase 8.3 — Measurement and operations

**Дата:** 2026-07-27
**Статус:** implementation complete; production activation pending

## Решение

MeVAD использует first-party telemetry contract без cookies, fingerprinting и
постоянного visitor/session ID. Клиент отправляет события только на
same-origin `/api/telemetry`. Collector принимает строго фиксированную схему,
ограничивает payload 8 KiB и отклоняет неизвестные поля.

Телеметрия выключена по умолчанию:

```env
NEXT_PUBLIC_MEVAD_TELEMETRY_ENABLED=false
MEVAD_TELEMETRY_MODE=off
```

После выбора production log destination, retention и правового основания
значения меняются на `true` и `stdout`. JSON-события stdout затем должны
агрегироваться инфраструктурным log provider.

## Event contract

| Event | Разрешённые dimensions | Назначение |
|---|---|---|
| `page_view` | route | Посещение публичной страницы |
| `analysis_started` | route | Начало основной воронки |
| `analysis_succeeded` | duration_ms, available_actions | Успех и latency анализа |
| `analysis_failed` | duration_ms, failure_kind | Ошибки анализа без URL/message |
| `action_selected` | action | Интерес к video/audio/clip/loop |
| `job_created` | action | Конверсия в processing job |
| `job_terminal` | action, status | Успех, failure или cancellation |
| `job_cancel_requested` | action | Намерение отменить job |
| `web_vital` | metric, rating, value, navigation_type | Field CWV |
| `client_error` | source, error_name | Ошибки браузера без message/stack |
| `api_proxy_failed` | operation, status_class | Ошибки web-to-API boundary |

Общая dimension `route` содержит только allowlisted pathname. Query string,
referrer, IP, user agent, source URL, media ID, job ID, title, author, cookies,
error message и stack trace не входят в application event.

## Dashboards

### 1. Organic acquisition

Источник: Google Search Console и Bing Webmaster Tools.

- impressions и clicks по landing route;
- CTR и average position;
- query groups: video, audio, cutter, GIF;
- landing-page conversion =
  `analysis_started / organic clicks`.

Search query не переносится в продуктовую телеметрию. Связь строится по
агрегированным route/day данным.

### 2. Product funnel

- `page_view → analysis_started`;
- `analysis_started → analysis_succeeded`;
- `analysis_succeeded → job_created`;
- `job_created → job_terminal{succeeded}`;
- conversion по route и action;
- cancellation и failure rate.

### 3. Reliability

- analysis failure rate по `failure_kind`;
- API proxy 5xx/network rate по `operation`;
- job failure/cancellation rate по action;
- alert: 5xx или network errors > 5% за 15 минут;
- alert: analysis success < 80% при не менее 50 попытках.

### 4. Real-user performance

- p75 LCP ≤ 2500 ms;
- p75 INP ≤ 200 ms;
- p75 CLS ≤ 0.1;
- разрез по route и rolling 7/28 days;
- alert при переходе p75 из `good` в `needs-improvement`.

## Privacy and security controls

- allowlist event names, property names and enum values;
- exact same-origin check и `Sec-Fetch-Site` validation;
- no response cookies and `cache-control: no-store`;
- no raw exception text or stack;
- no URL beyond normalized public pathname;
- client instrumentation failure never interrupts the product;
- React error fallback explicitly tells the user what was and was not recorded.

## Production activation checklist

1. Назначить владельца telemetry и incident response.
2. Выбрать log destination, регион и retention; рекомендуемый старт — 30 дней
   raw events и 13 месяцев агрегатов.
3. Проверить договоры с provider и обновить Privacy Notice конкретными данными.
4. Настроить dashboards и alerts из этого документа.
5. Включить оба environment flags.
6. Провести smoke test без реального private media URL.
7. Проверить удаление raw events по окончании retention.

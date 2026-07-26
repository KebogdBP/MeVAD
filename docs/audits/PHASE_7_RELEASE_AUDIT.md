# Phase 7 release audit

**Дата:** 2026-07-26

**Базовый commit:** `a68827a` (`main`)

**Scope:** Project Vision Phase 7 / Design System and SaaS UX

## Решение

Phase 7 завершена. Design system, workspace states, темы, responsive shell и
accessibility gates имеют воспроизводимые артефакты и включены в CI. Переход к
Phase 8 допустим с двумя известными release-исключениями ниже; они не блокируют
разработку SEO-страниц, но должны быть закрыты до публичного запуска.

## Проверяемые результаты

| Проверка | Результат | Команда |
|---|---:|---|
| Unit tests | 24/24 | `npm test` |
| Storybook states | 33 stories | `npm run build:storybook` |
| WCAG 2.2 AA / contrast | 66 light/dark story variants, 0 axe violations | `npm run test:storybook` |
| Keyboard walkthrough | URL → Analyze → action → options → Create job; visible focus | `npm run test:storybook` |
| Screen-reader semantics | analyze status → job live region/progress → error/download | `npm run test:storybook` |
| Responsive/reflow | 320, 375, 720@200%, 768, 1024, 1440 px | `npm run test:storybook` |
| Alternative display modes | reduced motion and forced colors | `npm run test:storybook` |
| Design-token policy | existing raw literals frozen; new literals fail CI | `npm run lint:tokens` |
| Production dependencies | 0 known vulnerabilities | `npm audit --omit=dev --audit-level=high` |

## Lighthouse baseline

Локальный production build, Lighthouse 13.3.0:

| Режим | Performance | Accessibility | Best Practices | SEO | CLS |
|---|---:|---:|---:|---:|---:|
| Mobile | 60 | 100 | 96 | 100 | 0 |
| Desktop | 92 | 100 | 100 | 100 | 0 |

CI запрещает падение ниже mobile `50/100/90/90` и desktop `75/100/90/90`
для Performance/Accessibility/Best Practices/SEO соответственно. Performance
оценивается как baseline, а accessibility является строгим gate со score 100.

## Известные исключения

| Исключение | Риск | Владелец | Срок |
|---|---|---|---|
| Mobile Lighthouse Performance ниже целевого SaaS-уровня 75 (baseline 60; TBT около 2.7 s, LCP около 3.5 s в симулированном профиле) | Более медленная интерактивность на слабых устройствах | Web UI / Performance | Phase 8 RC, 2026-08-15 |
| Не выполнена ручная матрица NVDA + Firefox и VoiceOver + Safari; автоматический role/name/live-region walkthrough проходит | Возможны AT/browser-specific отличия, которые не видит DOM-аудит | QA / Accessibility | До public launch, 2026-08-31 |

## Правила продолжения

- Не снижать accessibility threshold ниже 100 без отдельного утверждённого
  исключения.
- Новые reusable states добавлять в Storybook и обе темы.
- Изменения raw color/spacing должны сначала становиться design tokens; обновление
  fingerprint без design review запрещено.
- Повторить ручную AT-матрицу и mobile performance profiling перед public launch.

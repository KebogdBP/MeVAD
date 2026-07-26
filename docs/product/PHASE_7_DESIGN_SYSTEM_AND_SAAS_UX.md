# Phase 7 — Design System and SaaS UX

**Статус:** in progress (Slices 7.1–7.3)

**Входная точка:** commit `219910b`  
**Vision:** `MEGADOWNLOADER_PROJECT_VISION.md`, разделы 8 и Phase 7

## Цель

Превратить текущий качественный прототип workspace в устойчивую,
переиспользуемую и доступную SaaS design system без изменения media-domain
контрактов.

## Scope

- primitive, semantic и component design tokens;
- typography, spacing, radius, elevation и motion;
- Button, Input, Select, Checkbox/Switch, Segmented Control и Card;
- Status Badge, Progress, Skeleton, Empty State и Error State;
- responsive shell и мобильная навигация;
- light/dark themes;
- WCAG 2.2 AA audit;
- Storybook с документацией и accessibility checks;
- visual regression baseline для ключевых состояний workspace.

Не входят: SEO-страницы Phase 8, аккаунты, billing, playlist, subtitles и
изменения backend/API без отдельного дефекта.

## Порядок реализации

### Slice 7.1 — Foundations

- [x] Вынести исходные tokens из `globals.css`.
- [x] Разделить palette и semantic tokens для light/dark themes.
- [x] Подключить Inter/Manrope через `next/font`.
- [ ] Запретить новые raw color/spacing values правилом review/lint.
- [ ] Документировать правила neumorphism и contrast.

### Slice 7.2 — Component primitives

- [x] Создать `components/ui` с typed variants.
- [ ] Покрыть keyboard, focus, disabled, loading и error states.
- [x] Обеспечить touch target не меньше 44×44 px.
- [x] Добавить unit tests для интерактивных контрактов.

### Slice 7.3 — Storybook and quality gates

- [x] Подключить Storybook для Next.js.
- [x] Добавить stories для всех variants/states.
- [x] Включить automated a11y checks.
- [x] Зафиксировать desktop/tablet/mobile screenshots.
- [x] Добавить Storybook build и a11y gate в CI.

### Slice 7.4 — Workspace migration

- [x] Разделить orchestration и presentation в `media-workspace.tsx`.
- [x] Перевести URL form, action selector, fields и job states на primitives.
- [x] Добавить skeleton для анализа и запуска job.
- [x] Устранить layout shift и унифицировать status/error copy.

### Slice 7.5 — Themes and responsive UX

- [x] Реализовать system/light/dark preference без flash.
- [ ] Добавить доступную мобильную навигацию.
- [ ] Проверить 320, 375, 768, 1024 и 1440 px.
- [ ] Проверить zoom 200%, reduced motion и forced colors.

### Slice 7.6 — Accessibility and release audit

- [ ] Полный keyboard-only walkthrough.
- [ ] Screen reader walkthrough analyze → job → download.
- [ ] WCAG 2.2 AA contrast report.
- [ ] Lighthouse/accessibility baseline.
- [ ] Зафиксировать известные исключения с владельцем и сроком.

## Definition of Done

- Все пункты Phase 7 из Project Vision имеют реализацию и проверяемый артефакт.
- Все reusable UI states представлены в Storybook.
- Основной workflow проходит клавиатурой без ловушек и потери контекста.
- Light/dark themes проходят WCAG 2.2 AA.
- UI не содержит platform-specific branching.
- Web lint, typecheck, unit tests, Storybook build, a11y и production build
  проходят в CI.
- Visual regression охватывает empty, analyzed, validation error, processing,
  failed и succeeded states на desktop и mobile.

## Рекомендуемое разбиение PR

1. `feat(web): establish phase 7 design tokens`
2. `feat(web): add accessible UI primitives`
3. `chore(web): add Storybook and accessibility gates`
4. `refactor(web): migrate media workspace to design system`
5. `feat(web): add themes and responsive navigation`
6. `test(web): complete phase 7 UX and accessibility audit`

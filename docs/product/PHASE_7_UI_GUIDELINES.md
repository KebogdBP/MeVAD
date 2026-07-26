# Phase 7 UI guidelines

## Design-token policy

- New component colors must use semantic variables from `tokens.css`.
- New spacing, radii, elevation and motion values must reuse the corresponding
  token scale.
- `globals.css` contains the pre-token visual prototype. Its existing raw color
  and spacing literals are frozen by `npm run lint:tokens`; changing the
  fingerprint requires an explicit design review and an update to this document.
- Component-local dynamic values are allowed only when they represent content
  data rather than styling decisions, for example a media duration or calculated
  progress percentage.
- Phase 8 adds reviewed responsive layout bounds for the task landing template
  and manifest theme colors. Component colors and reusable spacing still use the
  existing semantic tokens; the updated fingerprint freezes these additions.
- Phase 8.2 adds reviewed responsive bounds for long-form information pages and
  the grouped footer navigation. The layout continues to use the existing
  semantic color, spacing, radius, elevation and motion tokens.

## Neumorphism

Neumorphism is decorative, not structural. It may be used for non-essential
depth on cards and previews, but never as the only indicator of selection,
focus, disabled state or hierarchy. Interactive controls must retain a visible
border, text/icon label and WCAG-compliant focus ring in light, dark and forced
color modes.

## Contrast and interaction

- Normal text targets WCAG 2.2 AA contrast of at least 4.5:1; large text targets
  3:1.
- Focus indicators and meaningful non-text UI target 3:1 against adjacent
  colors.
- Every interactive target is at least 44×44 CSS pixels.
- Loading controls expose `aria-busy`; disabled controls use the native
  `disabled` attribute; errors use `aria-invalid`, descriptions and live alerts.
- Motion is supplementary and must be disabled by `prefers-reduced-motion`.

The executable evidence is `npm run test:storybook`, which audits every story in
both themes with axe, keyboard traversal, live-region semantics, reduced motion,
forced colors and responsive reflow.

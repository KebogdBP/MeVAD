# ADR 0006: Bounded GIF and Loop Rendering

**Статус:** accepted
**Дата:** 2026-07-25

## Контекст

GIF и animated media легко создают чрезмерную нагрузку на CPU, память и диск.
При этом пользователю нужны простые настройки, а не произвольные FFmpeg
filters.

## Решение

- Поддержать GIF, WebP, MP4 и WebM через один `LoopMaker` port.
- Ограничить width, FPS и source duration в typed request.
- Разрешить только фиксированные quality и speed presets.
- Строить filter graph внутри adapter.
- Использовать palette pipeline для GIF.
- Удалять audio из всех loop outputs.
- Повторно использовать safe process runner и atomic output lifecycle.

## Последствия

Операции имеют предсказуемые верхние границы и безопасный CLI-контракт.
Crop, target filesize, visual presets и size estimation остаются следующими
инкрементами. MP4/WebM являются loop-ready файлами без embedded repeat flag.

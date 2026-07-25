# GIF and Loop Maker

## Назначение

Loop Maker создаёт из локального видео:

- GIF;
- animated WebP;
- loop-ready MP4;
- loop-ready WebM.

```text
CLI / future worker
        ↓
LoopMaker port
        ↓
FFmpegLoopMaker
        ├── FFprobe duration validation
        ├── trusted filter graph builder
        ├── format/quality presets
        └── atomic output lifecycle
```

## Параметры

- start/end в секундах;
- ширина 160–1920 px;
- FPS 1–60;
- quality: small, balanced, high;
- speed: 0.5×, 1×, 1.5×, 2×;
- repeat flag для GIF/WebP.

GIF и WebP дополнительно ограничены:

- source duration до 30 секунд;
- FPS до 30;
- ширина до 1280 px.

MP4/WebM source duration ограничена 120 секундами. Итоговая длительность равна
`source duration / speed`.

## Общий filter graph

Все числовые значения сначала валидируются типизированной моделью. После этого
adapter строит:

```text
setpts=PTS/SPEED,fps=FPS,scale=WIDTH:-2:flags=lanczos
```

Пользователь не может передать произвольный filter graph.

## GIF

GIF использует palette generation и palette application в одном
`filter_complex`:

1. нормализация speed/FPS/scale;
2. split потока;
3. `palettegen` с 64, 128 или 256 цветами;
4. `paletteuse` с dithering.

Это даёт заметно лучшее качество, чем прямое преобразование RGB в GIF.

## Animated WebP

- codec: `libwebp_anim`;
- quality: 50, 75 или 90;
- repeat: бесконечно либо один проход;
- audio удаляется.

## MP4 loop

- H.264 `libx264`;
- CRF 28, 23 или 18;
- `yuv420p`;
- `+faststart`;
- audio удаляется.

MP4 не содержит универсального loop flag. Результат является коротким
loop-ready клипом, а повторение выполняет player/UI.

## WebM loop

- VP9 `libvpx-vp9`;
- CRF 40, 32 или 24;
- constant-quality mode через bitrate 0;
- `yuv420p`;
- audio удаляется.

## Безопасность и lifecycle

- subprocess запускается с `shell=False`;
- filter/codec arguments строятся только из enum и проверенных чисел;
- stdin отключён;
- перезапись запрещена;
- обработка имеет timeout, зависящий от duration, width и FPS;
- managed process group поддерживает немедленную отмену и TERM→KILL;
- partial output удаляется при ошибке;
- существующий final/temporary output не трогается;
- результат публикуется через atomic `.part` rename.

Текущий progress coarse-grained: `processing` и `completed`. Немедленная отмена
уже поддерживается managed runner; покадровый progress потребует FFmpeg
`-progress pipe`.

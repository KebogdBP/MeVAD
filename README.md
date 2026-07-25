# MeVAD

**MegaDownloader Video & Audio** — единое рабочее пространство для анализа,
скачивания, извлечения, обрезки и преобразования видео и аудио.

> Одна ссылка — все доступные действия с видео и аудио в одном интерфейсе.

## Статус

Проект находится на границе Phase 0 и Phase 1. Уже доступны:

- устанавливаемый Python-пакет `mevad`;
- типизированные доменные модели;
- проверка URL без сетевого доступа;
- базовая защита от localhost и прямых private/reserved IP;
- обнаружение FFmpeg и FFprobe;
- CLI, тесты и автоматические quality gates;
- Smart URL Analyzer через изолированный `yt-dlp` adapter;
- нормализованные форматы, субтитры, playlist metadata и доступные действия.
- single-video downloader с пресетами качества, контейнерами и progress events.
- Audio Extractor для MP3, M4A, Opus и WAV.
- Video Cutter с быстрым и точным режимами.
- GIF & Loop Maker для GIF, WebP, MP4 и WebM.

Web API и фоновая job system ещё не реализованы.

## Требования

- Python 3.11 или новее;
- FFmpeg и FFprobe в `PATH` либо в переменных из `.env.example`.

## Локальная установка

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

Проверка runtime:

```bash
mevad doctor
```

Безопасная синтаксическая проверка URL:

```bash
mevad validate-url "https://example.com/video"
```

Команда не обращается к сети. DNS и каждый redirect target будут повторно
проверяться в будущем сетевом adapter перед соединением.

Анализ метаданных через `yt-dlp`:

```bash
mevad analyze "https://example.com/video"
```

Эта команда обращается к внешнему URL, но не скачивает медиапоток. На текущем
этапе она предназначена для локального CLI. Её нельзя напрямую публиковать как
web endpoint до добавления сетевой изоляции и проверки всех DNS/redirect
назначений.

Скачивание одного видео:

```bash
mevad download-video "https://example.com/video" \
  --quality 720p \
  --container mp4 \
  --output downloads
```

Доступные качества: `best`, `1080p`, `720p`, `480p`, `360p`. Контейнеры:
`auto`, `mp4`, `mkv`, `webm`. Команда предназначена для локального CLI и
наследует ограничения сетевой безопасности analyzer.

Извлечение аудио:

```bash
mevad extract-audio "https://example.com/video" \
  --codec mp3 \
  --bitrate 192 \
  --output downloads
```

Доступные кодеки: `mp3`, `m4a`, `opus`, `wav`. Bitrate-пресеты для сжатых
форматов: `128`, `192`, `256`, `320` kbps. Для WAV bitrate игнорируется.

Обрезка локального видео:

```bash
mevad cut-video input.mp4 \
  --start 10.5 \
  --end 25 \
  --mode accurate \
  --output downloads
```

`fast` использует stream copy и может начать фрагмент с ближайшего keyframe.
`accurate` перекодирует видео в H.264/AAC для более точных границ.

Создание GIF или loop-ready video:

```bash
mevad make-loop input.mp4 \
  --start 2 \
  --end 7 \
  --format gif \
  --width 640 \
  --fps 15 \
  --quality balanced \
  --speed 1 \
  --output downloads
```

Форматы: `gif`, `webp`, `mp4`, `webm`. Quality presets: `small`, `balanced`,
`high`. Скорость: `0.5`, `1`, `1.5`, `2`.

## Проверки

```bash
ruff check .
ruff format --check .
mypy
pytest --cov=mevad --cov-report=term-missing
```

## Документы

- [Project Vision](MEGADOWNLOADER_PROJECT_VISION.md)
- [Phase 0 — Repository Audit and Cleanup](docs/product/PHASE_0_REPOSITORY_AUDIT_AND_CLEANUP.md)
- [Initial Repository Audit](docs/audits/INITIAL_REPOSITORY_AUDIT.md)
- [Smart URL Analyzer Architecture](docs/architecture/SMART_URL_ANALYZER.md)
- [Video Downloader Architecture](docs/architecture/VIDEO_DOWNLOADER.md)
- [Audio Extractor Architecture](docs/architecture/AUDIO_EXTRACTOR.md)
- [Video Cutter Architecture](docs/architecture/VIDEO_CUTTER.md)
- [GIF and Loop Maker Architecture](docs/architecture/GIF_LOOP_MAKER.md)

## Планируемая архитектура

```text
Browser
   ↓
Next.js
   ↓
FastAPI
   ├── PostgreSQL
   ├── Redis
   ├── Object Storage
   └── Task Queue
          ↓
      Media Worker
      ├── yt-dlp
      └── FFmpeg
```

Разработка начнётся после завершения решений Phase 0, включая стратегию
использования кода прежнего CLI, lock tool и лицензию.

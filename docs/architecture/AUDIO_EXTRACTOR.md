# Audio Extractor

## Назначение

Audio Extractor скачивает лучший доступный аудиопоток одного remote media URL и
преобразует его через FFmpeg postprocessor:

```text
CLI / future worker
        ↓
AudioExtractor port
        ↓
YtDlpAudioExtractor
        ├── audio source selector
        ├── FFmpegExtractAudio
        ├── progress/cancellation
        └── output path confinement
```

## Поддерживаемые пресеты

Кодеки:

- MP3;
- M4A;
- Opus;
- WAV.

Bitrate для сжатых форматов:

- 128 kbps;
- 192 kbps;
- 256 kbps;
- 320 kbps.

WAV является несжатым форматом, поэтому bitrate не передаётся FFmpeg.

## Выбор исходного потока

- M4A сначала предпочитает `bestaudio[ext=m4a]`;
- Opus сначала предпочитает поток с Opus codec;
- MP3 и WAV используют лучший доступный audio source;
- каждый selector содержит fallback;
- пользователь не может передать произвольную format expression.

Совместимый исходный поток может уменьшить лишнее перекодирование, но итоговый
codec всегда задаётся через структурированный `FFmpegExtractAudio`
postprocessor.

## Выходные файлы

Audio adapter использует те же ограничения, что Video Downloader:

- single-item operation с `noplaylist=True`;
- ограниченный output template;
- Windows-compatible имена и ограничение длины;
- запрет перезаписи;
- `.part` для продолжения загрузки;
- проверка, что финальный путь остаётся внутри output directory;
- подтверждение файла и размера после FFmpeg.

## Прогресс и отмена

Загрузка, post-processing и завершение используют общий `DownloadProgress`.
Это позволит Video Downloader и Audio Extractor публиковать одинаковые события
в будущую job system.

Cancellation token проверяется до старта, в download hooks и postprocessor
hooks. CLI поддерживает `Ctrl+C`; worker позднее привяжет token к состоянию job.

## Граница безопасности

Пользователь управляет только URL, codec, bitrate и output directory. Он не
может передавать:

- shell-команды;
- FFmpeg arguments;
- postprocessor definitions;
- произвольный output template;
- proxy, netrc или external downloader;
- playlist selection.

До создания изолированного worker этот adapter остаётся локальной CLI-функцией,
а не публичным web endpoint.

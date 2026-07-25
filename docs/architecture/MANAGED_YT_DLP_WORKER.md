# Managed yt-dlp Worker

## Поток

```text
JobExecutor
    ↓
YtDlpCommandVideoDownloader / YtDlpCommandAudioExtractor
    ↓
run_process(Popen, new process group)
    ↓
python -m yt_dlp [fixed typed arguments] URL
    ↓
after_move markers → validated result path
```

Worker не вызывает embedded `YoutubeDL.extract_info(download=True)`. Отдельный
процесс позволяет polling cancellation, hard deadline и TERM→KILL всей process
group вместе с FFmpeg postprocessor.

## Command safety

- `shell=False`;
- executable и flags задаёт приложение;
- URL проходит `normalize_remote_url`;
- format selector строится из enums;
- playlist отключён;
- overwrite отключён;
- retries ограничены;
- output template фиксирован;
- путь результата обязан находиться внутри job workspace.

## Result protocol

yt-dlp получает три `--print after_move:` templates:

```text
MEVAD_ID=...
MEVAD_TITLE=...
MEVAD_PATH=...
```

Отсутствующие markers, non-zero exit, escaped path или отсутствующий файл
считаются безопасной `MediaDownloadError`. stderr не возвращается пользователю.

## Deadline и cancellation

`MEVAD_WORKER_MEDIA_TIMEOUT_SECONDS` задаёт общий download/postprocessing
deadline от 60 секунд до 24 часов. Cancellation token читает PostgreSQL job
state на каждом process poll.

## Streaming progress

yt-dlp получает отдельные machine templates:

```text
MEVAD_PROGRESS=downloaded|total|estimated_total|speed|eta
MEVAD_PROCESSING=1
```

Parser игнорирует все немаркированные строки, выбирает declared или estimated
total и преобразует отсутствующие значения в `None`. `DownloadProgress`
поступает в `ProgressBridge` до завершения процесса.

stdout/stderr дренируются reader threads, но callback исполняется в основном
worker thread. Capture ограничен одним мегабайтом на stream и не растёт вместе
с длительностью download.

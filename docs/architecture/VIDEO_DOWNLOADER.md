# Video Downloader

## Назначение

Single-video downloader принимает типизированный `VideoDownloadRequest`,
скачивает одно видео через `yt-dlp` и возвращает `VideoDownloadResult`.

```text
CLI / future worker
        ↓
VideoDownloader port
        ↓
YtDlpVideoDownloader
        ├── format planner
        ├── progress hooks
        ├── cancellation token
        └── output path confinement
```

## Контракт запроса

- HTTP(S) `MediaSource`;
- output directory;
- quality: `best`, `1080p`, `720p`, `480p`, `360p`;
- container: `auto`, `mp4`, `mkv`, `webm`.

Произвольная format-строка от пользователя не принимается. Adapter строит
выражение `yt-dlp` только из доверенных enum-значений.

Плейлисты отключены через `noplaylist=True`. Playlist Workspace будет отдельной
операцией с собственными лимитами и моделью результата.

## Выходные файлы

Adapter:

- создаёт output directory;
- передаёт путь через `paths.home`;
- использует ограниченный шаблон имени;
- включает Windows-compatible filenames;
- ограничивает длину имени;
- не перезаписывает существующие результаты;
- сохраняет `.part` для штатного продолжения;
- после обработки проверяет, что итоговый путь находится внутри output
  directory;
- подтверждает существование файла и получает размер с файловой системы.

Путь, сообщённый внешней библиотекой, нельзя считать доверенным до
`resolve()` и проверки containment.

## Выбор формата

Format planner предпочитает раздельные video/audio streams и разрешает
progressive fallback:

```text
bestvideo[height<=LIMIT]+bestaudio/best[height<=LIMIT]
```

Для MP4 сначала выбираются MP4 video и M4A audio, для WebM — WebM streams.
`merge_output_format` устанавливается только при явном выборе контейнера.

## Progress events

Внешние hook dictionaries преобразуются в `DownloadProgress`:

- `downloading`;
- `processing`;
- `completed`.

Event может содержать downloaded bytes, total/estimated bytes, скорость, ETA и
имя файла. Core не печатает прогресс напрямую: callback выбирает CLI, worker
или будущая очередь задач.

## Отмена

`CancellationToken` проверяется:

- до начала операции;
- на каждом progress hook;
- на каждом postprocessor hook;
- после внешней ошибки, если `yt-dlp` обернул исключение hook.

В worker token будет связан с состоянием job в Redis/БД. Текущий CLI также
поддерживает обычное прерывание `Ctrl+C`.

## Ограничения безопасности

Downloader пока является локальным инструментом. Для публичного SaaS нужны:

- отдельный worker/container;
- запрет private networks и metadata endpoints;
- ограничения CPU, памяти, диска и длительности;
- per-job временная директория;
- quota на размер результата;
- очистка `.part` и завершённых файлов по TTL;
- запрет пользовательских config, netrc, proxy и external downloader options.

Unit-тесты не используют сеть и создают только временные файлы pytest.

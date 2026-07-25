# Video Cutter

## Назначение

Video Cutter создаёт фрагмент из локального видео:

```text
CLI / future worker
        ↓
VideoCutter port
        ↓
FFmpegVideoCutter
        ├── FFprobe duration validation
        ├── argument-array FFmpeg call
        ├── bounded timeout
        └── atomic .part → final rename
```

## Интервал

`ClipInterval` принимает секунды с дробной частью и проверяет:

- значения конечны;
- start не отрицательный;
- end строго больше start.

Перед обработкой FFprobe получает реальную длительность контейнера. End не
может превышать её более чем на один миллисекундный допуск.

CLI намеренно принимает числа секунд. Парсинг `HH:MM:SS` будет частью будущего
web presentation layer и не влияет на контракт core.

## Режим Fast

FFmpeg получает input seek, duration и stream copy:

```text
-ss START -i INPUT -t DURATION -c copy
```

Преимущества:

- высокая скорость;
- почти нет CPU-затрат;
- нет потери качества.

Ограничение: при stream copy старт может привязаться к ближайшему keyframe.
Исходное расширение контейнера сохраняется.

## Режим Accurate

FFmpeg использует input seeking с включённым по умолчанию accurate seek и
перекодирует:

- video: H.264 через `libx264`, CRF 20, preset medium;
- audio: AAC 192 kbps;
- container: MP4 с `+faststart`.

Этот режим требует больше CPU и может незначительно менять качество, но точнее
соблюдает границы фрагмента.

## Безопасность subprocess

- `shell=False`;
- команда передаётся массивом аргументов;
- пользователь не передаёт codec, filter или FFmpeg arguments;
- stdin отключён через `-nostdin`;
- перезапись запрещена через `-n`;
- stderr сокращается до последней строки и 500 символов;
- FFprobe и FFmpeg имеют timeout;
- FFmpeg запускается в отдельной process group;
- cancellation опрашивается во время кодирования;
- timeout/cancel выполняет TERM с последующим KILL fallback;
- output filename строится приложением.

## Файловый lifecycle

FFmpeg пишет в файл вида `name.clip-START-END.part.mp4`. Только после успешного
кода возврата и подтверждения файла он атомарно переименовывается в финальный
путь.

При FFmpeg error или timeout частичный файл удаляется. Существующий final или
temporary output не перезаписывается и не удаляется.

## Progress и отмена

Текущая реализация публикует coarse events:

- `processing`;
- `completed`.

Cancellation проверяется до FFprobe, перед FFmpeg, каждые 250 мс во время
кодирования и после завершения процесса. Managed runner завершает всю process
group, поэтому дочерние encoder-процессы не остаются orphan.

## Ограничения

- обрабатывается только локальный файл;
- точный режим всегда создаёт MP4 H.264/AAC;
- subtitle/data streams не копируются;
- отсутствуют crop, resize и social presets;
- нет покадрового progress из `-progress pipe`.

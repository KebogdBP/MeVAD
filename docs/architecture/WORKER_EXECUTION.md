# Worker Execution Layer

## Назначение

Worker выполняет одну сохранённую задачу вне HTTP request lifecycle:

```text
broker delivers job_id
        ↓
JobExecutor.execute(job_id)
        ↓
queued → running
        ↓
operation adapter(s)
        ↓
progress / cancellation
        ↓
succeeded | failed | cancelled
```

Broker пока не реализован. `JobExecutor` является синхронным application
service, который будущий Redis consumer вызовет с полученным `job_id`.

## Dispatch

### Download video

```text
YtDlpVideoDownloader → results/
```

### Extract audio

```text
YtDlpAudioExtractor → results/
```

### Cut video

```text
YtDlpVideoDownloader → intermediate/
FFmpegVideoCutter     → results/
cleanup intermediate/
```

### Make loop

```text
YtDlpVideoDownloader → intermediate/
FFmpegLoopMaker       → results/
cleanup intermediate/
```

Worker повторно строит типизированные core requests из сохранённых job
parameters. Неизвестные enum, отсутствующие или неверно типизированные
параметры завершают job безопасной общей ошибкой.

## Workspace

Каждая задача получает:

```text
storage/jobs/{job_id}/
├── intermediate/
└── results/
```

`WorkspaceManager`:

- разрешает в job ID только ASCII letters, digits, `_` и `-`;
- ограничивает длину 128 символами;
- делает `resolve()` и containment checks;
- запрещает symbolic links для служебных директорий;
- возвращает только relative result reference;
- проверяет существование результата;
- удаляет intermediate directory staged operations в `finally`.

Абсолютный filesystem path не публикуется в API Job.

## Progress bridge

Core adapters публикуют `DownloadProgress`. `ProgressBridge` преобразует events
в monotonic job percent:

- direct download/audio: 0–99;
- staged download: 0–50;
- staged cut/loop: 50–99;
- `JobService.succeed`: 100.

`processing` event переводит running job в processing. Повторяющиеся или
уменьшающиеся значения не записываются.

Managed yt-dlp передаёт downloaded bytes, total/estimated bytes, speed и ETA
через маркированный streaming stdout protocol. Произвольный extractor output
игнорируется.

## Cancellation

`JobCancellationToken` каждый раз читает актуальное job state:

- running/processing job после API cancel становится `cancel_requested`;
- adapter видит token и прерывает операцию;
- executor вызывает cancellation acknowledgement;
- итоговый state становится `cancelled`.

Тот же polling вызывает throttled PostgreSQL heartbeat. Поэтому download,
FFmpeg и postprocessing продлевают worker lease даже между progress events.

Executor сохраняет opaque broker receipt вместе с lease. Runtime подтверждает
только этот exact delivery; retry получает новый receipt.

Если внешняя операция завершилась ошибкой одновременно с cancel request,
executor предпочитает cancellation acknowledgement, не раскрывая внутренние
details.

## Ошибки

Transient domain/processing errors преобразуются в:

```text
status: failed
error_code: job_execution_failed
error_message: The media job could not be completed.
```

Сырые stderr, URL credentials, cookies и upstream details в job не сохраняются.

Managed FFmpeg deadline получает отдельный стабильный результат:

```text
status: failed
error_code: job_timed_out
error_message: The media job exceeded its processing deadline.
```

Неверные job parameters, unsupported media и отсутствие runtime tool получают
отдельные permanent codes. Runtime повторяет только allowlist transient codes;
неизвестная ошибка считается permanent. Retry ждёт capped exponential backoff
в Redis delayed sorted set, не блокируя worker process.

`run_process` использует `Popen(start_new_session=True)`, polling cancellation и
завершение process group через TERM→KILL. Worker video/audio adapters также
запускают yt-dlp отдельной командой; embedded Python API остаётся только в
локальных CLI/analyzer границах.

Production factory связывает все command adapters с Linux rlimits:
CPU seconds, address space, output file size и open descriptors. Потомки
yt-dlp/FFmpeg наследуют policy. SIGXCPU/SIGXFSZ становятся permanent
`job_resource_limit_exceeded`; wall-clock timeout остаётся отдельным пределом.

## Текущая граница

`SqlJobRepository`, `RedisJobQueue` и `WorkerRuntime` теперь связывают API и
отдельный process. Следующий infrastructure layer требует:

- retry jitter;
- network sandbox.

Runtime уже выполняет два selective recovery прохода: timestamped Redis reaper
для claim-to-lease gap и SQL lease recovery для зависших running jobs.

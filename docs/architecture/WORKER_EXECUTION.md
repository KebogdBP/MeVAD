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

## Cancellation

`JobCancellationToken` каждый раз читает актуальное job state:

- running/processing job после API cancel становится `cancel_requested`;
- adapter видит token и прерывает операцию;
- executor вызывает cancellation acknowledgement;
- итоговый state становится `cancelled`.

Если внешняя операция завершилась ошибкой одновременно с cancel request,
executor предпочитает cancellation acknowledgement, не раскрывая внутренние
details.

## Ошибки

Ожидаемые domain, parameter и processing errors преобразуются в:

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

`run_process` использует `Popen(start_new_session=True)`, polling cancellation и
завершение process group через TERM→KILL. Встроенные yt-dlp adapters пока
остаются Python API calls с socket timeout и hook-based cancellation; hard
overall timeout для них потребует отдельного subprocess adapter.

## Текущая граница

`SqlJobRepository`, `RedisJobQueue` и `WorkerRuntime` теперь связывают API и
отдельный process. Следующий infrastructure layer требует:

- per-worker atomic lease;
- worker heartbeat;
- retry backoff и permanent-error classification;
- recovery зависших running jobs;
- storage TTL;
- process-level resource limits;
- network sandbox.

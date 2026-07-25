# ADR 0022: Linux media process resource limits

## Статус

Принято.

## Контекст

Hard wall-clock timeout не ограничивает CPU time, virtual memory, размер
создаваемого файла и file descriptors. Повреждённый media input или внешний
tool мог исчерпать ресурсы worker host до наступления timeout.

## Решение

- Все production FFmpeg и yt-dlp command adapters получают один immutable
  `ProcessLimits`.
- Перед `exec` на Linux child получает `RLIMIT_CPU`, `RLIMIT_AS`,
  `RLIMIT_FSIZE` и `RLIMIT_NOFILE`.
- Ограничения наследуют FFmpeg postprocessors и другие descendants yt-dlp.
- Requested limits никогда не повышают более низкий inherited hard limit.
- SIGXCPU и SIGXFSZ преобразуются в стабильный permanent
  `job_resource_limit_exceeded`.
- Wall-clock timeout, cancellation и process-group TERM→KILL остаются
  независимыми слоями защиты.
- Compose worker дополнительно ограничен 2 CPU, 3 GiB memory и 256 processes
  через container runtime.
- На macOS/Windows rlimit policy не применяется: эти платформы сохраняют
  managed process controls, но не считаются production sandbox.

Defaults:

- CPU: 7200 секунд;
- address space: 2 GiB;
- один output file: 10 GiB;
- open files: 256.

## Последствия

Media subprocess и его descendants не могут бесконтрольно занять основные
process resources Linux worker. Настройки доступны через
`MEVAD_WORKER_*_LIMIT_*`.

RLIMIT_AS ограничивает virtual address space, а не container RSS. Production
orchestrator должен сохранять cgroup limits не слабее Compose defaults.
Network egress и filesystem namespace этим ADR не изолируются.

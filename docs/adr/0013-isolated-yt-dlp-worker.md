# ADR 0013: Isolated yt-dlp worker commands

## Статус

Принято.

## Контекст

Встроенный `YoutubeDL.extract_info()` нельзя принудительно остановить из другого
Python thread. Из-за этого worker hard timeout и API cancellation не могли
гарантированно завершить зависший download/postprocessor.

## Решение

- Worker использует `python -m yt_dlp` через managed process runner.
- CLI arguments строятся только из typed enums и нормализованного URL.
- Result protocol использует маркированные `--print after_move:` значения.
- Публикуемый filepath проходит resolve/containment/file checks.
- stderr и upstream details не попадают в job error.
- Общий deadline задаётся `MEVAD_WORKER_MEDIA_TIMEOUT_SECONDS`.
- Python API adapters сохраняются для локального CLI и dependency-injected tests.

## Последствия

Video/audio worker operations теперь имеют hard timeout, немедленную durable
cancellation и process-group cleanup, включая дочерний FFmpeg postprocessor.
Текущий progress coarse: started/completed. Streaming `--progress-template`
protocol будет отдельным улучшением.

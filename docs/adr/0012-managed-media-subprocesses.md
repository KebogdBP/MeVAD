# ADR 0012: Managed media subprocesses

## Статус

Принято.

## Контекст

`subprocess.run(timeout=...)` ограничивает длительность, но не позволяет worker
регулярно проверять durable cancellation или heartbeat. FFmpeg также может
создавать дочерние процессы, которые нельзя оставлять после отмены job.

## Решение

- Использовать `Popen` без shell и с новой process session.
- Вызывать `communicate()` короткими bounded polling-интервалами.
- На каждом poll проверять cancellation и вызывать optional callback.
- При cancel/timeout завершать process group через SIGTERM.
- Через две секунды применять SIGKILL fallback.
- Хранить timeout в job как стабильный `job_timed_out`, без stderr/details.

## Последствия

FFmpeg cutting и loop rendering теперь немедленно отменяются и имеют hard
deadline. Poll callback является точкой расширения для lease heartbeat.
yt-dlp пока работает через встроенный Python API; для общего hard deadline его
нужно вынести в отдельный subprocess adapter с безопасным progress protocol.

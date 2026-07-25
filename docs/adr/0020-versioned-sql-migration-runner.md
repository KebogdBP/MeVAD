# ADR 0020: Versioned SQL migration runner

## Статус

Принято.

## Контекст

PostgreSQL init directory выполняет SQL только при создании пустого data
volume. Новая migration не применялась к существующей установке, поэтому
deployment мог запустить код против старой schema.

## Решение

- `mevad-migrate` читает ordered `NNNN_name.sql` files.
- Версии обязаны начинаться с `0001`, быть уникальными и contiguous.
- `schema_migrations` хранит version, SHA-256 checksum и UTC application time.
- Уже применённый файл с другим checksum считается ошибкой deployment.
- Неизвестная БД-версия, отсутствующая в checkout, также считается ошибкой.
- Все pending migrations и journal records применяются одной transaction.
- PostgreSQL advisory transaction lock сериализует параллельные runners.
- Compose запускает одноразовый `migrate` service после PostgreSQL healthcheck.
- API, worker и outbox relay стартуют только после
  `service_completed_successfully`.

## Последствия

Existing PostgreSQL volumes обновляются тем же путём, что и новые. Ошибка
migration откатывает весь pending batch и не допускает запуск application
processes.

SQL splitter поддерживает обычные statements, quoted strings/identifiers и
line comments. Миграции, которым нужны stored procedures, dollar quoting или
non-transactional DDL, потребуют расширения runner либо специального
versioned Python migration.

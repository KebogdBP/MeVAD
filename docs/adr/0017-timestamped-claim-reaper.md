# ADR 0017: Timestamped claim reaper

## Статус

Принято.

## Контекст

`BRPOPLPUSH` надёжно переносит delivery в processing list, а SQL lease
создаётся следующим независимым действием. Если worker завершается между этими
операциями, job остаётся `queued`, claim не имеет lease и больше не попадает в
ready queue.

Глобальный replay processing list небезопасен: он дублирует активную работу.

## Решение

- Ready payload содержит `created_at`.
- После `BRPOPLPUSH` worker атомарно заменяет processing payload версией с
  `claimed_at`.
- Queue port предоставляет выборку claims старше заданного UTC deadline.
- Runtime раз в recovery interval проверяет claims старше настраиваемого grace
  period (`MEVAD_WORKER_CLAIM_STALE_SECONDS`, по умолчанию 120 секунд).
- Stale claim возвращается в ready только когда SQL job всё ещё `queued` и не
  содержит `claim_receipt`.
- Claim отсутствующей или terminal job удаляется.
- Claim, который не совпадает с receipt уже созданной lease, также удаляется.
- Активный claim с совпадающей SQL lease обрабатывается lease recovery и этим
  reaper не перемещается.

Повторная доставка получает новый opaque receipt и новый `claimed_at`, поэтому
поздний ack старой доставки не может удалить новую.

## Совместимость

JSON payload без `claimed_at` использует `created_at` как conservative fallback.
Legacy plain `job_id` получает timestamp при первом claim.

## Последствия

Crash в claim-to-lease gap восстанавливается автоматически без replay активных
задач. Job может ждать не более grace period плюс recovery interval.

Timestamp stamping выполняется сразу после Redis claim, но отдельной Redis
операцией. Crash до stamping оставляет payload с `created_at`; он всё равно
будет найден reaper, хотя старая запись, долго ожидавшая в ready queue, может
быть восстановлена раньше полного grace period после фактического claim. Полное
устранение этого окна потребует другой broker primitive, Redis Streams или
согласованного transactional dispatch протокола.

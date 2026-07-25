# ADR 0023: Proxy-enforced media network sandbox

## Статус

Принято.

## Контекст

Синтаксическая проверка исходного URL не предотвращает DNS rebinding, redirect
на private address и дополнительные запросы extractor. `yt-dlp` сам управляет
DNS и HTTP-переходами, поэтому проверка только первого hostname создаёт SSRF
риск.

## Решение

- API и worker в Compose подключены только к `internal` backend network.
- Прямого маршрута из media processes в интернет нет.
- Единственный egress bridge — Squid proxy с отдельным внешним network.
- Proxy разрешает только HTTP/HTTPS и запрещает private, loopback, link-local,
  carrier-grade NAT, documentation, multicast и reserved IPv4/IPv6 ranges.
- Analyzer и managed download commands получают proxy явно.
- Пользовательские yt-dlp config и netrc отключены.
- `MEVAD_ANALYZER_ENABLED=true` невалиден без
  `MEVAD_NETWORK_SANDBOX=external_proxy` и абсолютного
  `MEVAD_MEDIA_PROXY_URL`.

Redirect и extractor subrequests также проходят через proxy, где destination
ACL применяется к каждому соединению.

## Последствия

Compose может безопасно включить remote analyzer. Локальный запуск по умолчанию
оставляет его выключенным. Поддержка дополнительных outbound-протоколов
запрещена; для неё потребуется отдельное security review.

Этот boundary не заменяет лимиты процессов, таймауты и URL normalization — все
слои применяются одновременно.

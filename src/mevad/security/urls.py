"""Syntactic URL validation performed before any network access."""

from ipaddress import ip_address
from urllib.parse import SplitResult, urlsplit, urlunsplit

from mevad.exceptions import InvalidSourceURLError

_ALLOWED_SCHEMES = frozenset({"http", "https"})
_BLOCKED_HOSTNAMES = frozenset({"localhost", "localhost.localdomain"})


def normalize_remote_url(raw_url: str) -> str:
    """Validate and normalize a public HTTP(S) media URL.

    This function intentionally performs no DNS lookup. The network adapter must
    resolve every redirect target and reject private/reserved addresses again
    immediately before connecting.
    """

    candidate = raw_url.strip()
    if not candidate:
        raise InvalidSourceURLError("URL must not be empty.")

    try:
        parsed = urlsplit(candidate)
        port = parsed.port
    except ValueError as error:
        raise InvalidSourceURLError("URL is malformed.") from error

    if parsed.scheme.lower() not in _ALLOWED_SCHEMES:
        raise InvalidSourceURLError("Only http and https URLs are allowed.")
    if parsed.username is not None or parsed.password is not None:
        raise InvalidSourceURLError("Credentials in URLs are not allowed.")
    if parsed.hostname is None:
        raise InvalidSourceURLError("URL must include a hostname.")

    hostname = parsed.hostname.rstrip(".").lower()
    if hostname in _BLOCKED_HOSTNAMES or hostname.endswith(".localhost"):
        raise InvalidSourceURLError("Localhost URLs are not allowed.")

    _reject_non_public_ip(hostname)

    normalized_host = f"[{hostname}]" if ":" in hostname else hostname
    if port is not None:
        normalized_host = f"{normalized_host}:{port}"

    normalized = SplitResult(
        scheme=parsed.scheme.lower(),
        netloc=normalized_host,
        path=parsed.path or "/",
        query=parsed.query,
        fragment="",
    )
    return urlunsplit(normalized)


def _reject_non_public_ip(hostname: str) -> None:
    try:
        address = ip_address(hostname)
    except ValueError:
        return

    if not address.is_global:
        raise InvalidSourceURLError("Private, loopback, reserved, and link-local IPs are blocked.")

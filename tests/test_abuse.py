from starlette.requests import Request

from mevad_api.abuse import InMemoryAbuseProtector, client_key
from mevad_api.config import Settings


def test_memory_rate_limit_resets_on_next_window() -> None:
    now = [100.0]
    protector = InMemoryAbuseProtector(clock=lambda: now[0])

    assert protector.check_rate("client", "analyze", limit=1, window=60).allowed
    assert not protector.check_rate("client", "analyze", limit=1, window=60).allowed

    now[0] = 120.0
    assert protector.check_rate("client", "analyze", limit=1, window=60).allowed


def test_client_key_uses_forwarded_ip_only_when_trusted() -> None:
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [(b"x-forwarded-for", b"203.0.113.10, 10.0.0.2")],
            "client": ("127.0.0.1", 1234),
        }
    )
    trusted = Settings(
        environment="test",
        trust_proxy_headers=True,
        abuse_client_salt="test-secret",
    )
    direct = Settings(
        environment="test",
        trust_proxy_headers=False,
        abuse_client_salt="test-secret",
    )

    assert client_key(request, trusted) != client_key(request, direct)
    assert "203.0.113.10" not in client_key(request, trusted)

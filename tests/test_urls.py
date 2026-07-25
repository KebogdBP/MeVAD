import pytest

from mevad.exceptions import InvalidSourceURLError
from mevad.security import normalize_remote_url


@pytest.mark.parametrize(
    ("raw_url", "expected"),
    [
        ("https://Example.com/watch?v=1#chapter", "https://example.com/watch?v=1"),
        (" http://media.example/path ", "http://media.example/path"),
        ("https://example.com", "https://example.com/"),
        ("https://[2606:4700:4700::1111]/video", "https://[2606:4700:4700::1111]/video"),
    ],
)
def test_normalizes_public_http_urls(raw_url: str, expected: str) -> None:
    assert normalize_remote_url(raw_url) == expected


@pytest.mark.parametrize(
    "raw_url",
    [
        "",
        "file:///etc/passwd",
        "ftp://example.com/video",
        "https://localhost/video",
        "https://service.localhost/video",
        "http://127.0.0.1/video",
        "http://10.0.0.4/video",
        "http://169.254.169.254/latest/meta-data",
        "http://[::1]/video",
        "https://user:password@example.com/video",
        "https://[not-an-ip]/video",
    ],
)
def test_rejects_unsafe_or_invalid_urls(raw_url: str) -> None:
    with pytest.raises(InvalidSourceURLError):
        normalize_remote_url(raw_url)

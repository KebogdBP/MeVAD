from mevad.models import MediaSource, SourceKind


def test_media_source_is_immutable() -> None:
    source = MediaSource(kind=SourceKind.REMOTE_URL, value="https://example.com/video")

    assert source.kind is SourceKind.REMOTE_URL
    assert source.value == "https://example.com/video"

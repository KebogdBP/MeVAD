import json
from typing import Any

import pytest

import mevad.cli
from mevad.cli import main
from mevad.exceptions import MediaAnalysisError
from mevad.models import MediaAnalysis, MediaSource, SourceKind


def test_validate_url_command_prints_normalized_url(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["validate-url", "https://Example.com/video#fragment"])

    assert exit_code == 0
    assert capsys.readouterr().out == "https://example.com/video\n"


def test_validate_url_command_rejects_private_address(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["validate-url", "http://127.0.0.1/video"])

    assert exit_code == 2
    assert "invalid URL:" in capsys.readouterr().out


def test_analyze_command_prints_json(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeAnalyzer:
        def analyze(self, source: MediaSource) -> MediaAnalysis:
            return MediaAnalysis(
                source=source,
                extractor="Example",
                media_id="video-1",
                title="Example video",
                author=None,
                duration_seconds=10.0,
                thumbnail_url=None,
                webpage_url=source.value,
                is_playlist=False,
                playlist_entry_count=None,
                formats=(),
                subtitle_languages=(),
                available_actions=(),
            )

    monkeypatch.setattr(mevad.cli, "YtDlpAnalyzer", FakeAnalyzer)

    exit_code = main(["analyze", "https://example.com/video"])
    output: dict[str, Any] = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert output["media_id"] == "video-1"
    assert output["source"]["kind"] == SourceKind.REMOTE_URL


def test_analyze_command_reports_domain_error(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FailingAnalyzer:
        def analyze(self, source: MediaSource) -> MediaAnalysis:
            raise MediaAnalysisError(f"failed to analyze {source.value}")

    monkeypatch.setattr(mevad.cli, "YtDlpAnalyzer", FailingAnalyzer)

    exit_code = main(["analyze", "https://example.com/video"])

    assert exit_code == 2
    assert "analysis error: failed to analyze" in capsys.readouterr().out

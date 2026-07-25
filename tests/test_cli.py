import json
from pathlib import Path
from typing import Any

import pytest

import mevad.cli
from mevad.cli import main
from mevad.exceptions import MediaAnalysisError, MediaDownloadError
from mevad.models import (
    AudioCodec,
    AudioExtractionRequest,
    AudioExtractionResult,
    ClipInterval,
    CutMode,
    DownloadProgress,
    DownloadStatus,
    MediaAnalysis,
    MediaSource,
    SourceKind,
    VideoCutRequest,
    VideoCutResult,
    VideoDownloadRequest,
    VideoDownloadResult,
)


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


def test_download_command_prints_progress_and_result(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    class FakeDownloader:
        def download(
            self,
            request: VideoDownloadRequest,
            *,
            on_progress: Any = None,
        ) -> VideoDownloadResult:
            assert request.output_directory == tmp_path
            on_progress(
                DownloadProgress(
                    status=DownloadStatus.DOWNLOADING,
                    downloaded_bytes=5,
                    total_bytes=10,
                )
            )
            return VideoDownloadResult(
                media_id="video-1",
                title="Example",
                output_path=tmp_path / "video.mp4",
                filesize_bytes=10,
            )

    monkeypatch.setattr(mevad.cli, "YtDlpVideoDownloader", FakeDownloader)

    exit_code = main(
        [
            "download-video",
            "https://example.com/video",
            "--output",
            str(tmp_path),
            "--quality",
            "720p",
            "--container",
            "mp4",
        ]
    )
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "downloading 50.0%" in output
    assert '"media_id": "video-1"' in output


def test_download_command_reports_domain_error(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FailingDownloader:
        def download(self, request: VideoDownloadRequest, **_kwargs: Any) -> VideoDownloadResult:
            raise MediaDownloadError(f"failed to download {request.source.value}")

    monkeypatch.setattr(mevad.cli, "YtDlpVideoDownloader", FailingDownloader)

    exit_code = main(["download-video", "https://example.com/video"])

    assert exit_code == 2
    assert "download error: failed to download" in capsys.readouterr().out


def test_audio_command_prints_progress_and_result(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    class FakeExtractor:
        def extract(
            self,
            request: AudioExtractionRequest,
            *,
            on_progress: Any = None,
        ) -> AudioExtractionResult:
            assert request.output_directory == tmp_path
            assert request.codec is AudioCodec.OPUS
            on_progress(
                DownloadProgress(
                    status=DownloadStatus.DOWNLOADING,
                    downloaded_bytes=25,
                    total_bytes=100,
                )
            )
            return AudioExtractionResult(
                media_id="audio-1",
                title="Example",
                codec=AudioCodec.OPUS,
                output_path=tmp_path / "audio.opus",
                filesize_bytes=100,
            )

    monkeypatch.setattr(mevad.cli, "YtDlpAudioExtractor", FakeExtractor)

    exit_code = main(
        [
            "extract-audio",
            "https://example.com/audio",
            "--output",
            str(tmp_path),
            "--codec",
            "opus",
            "--bitrate",
            "256",
        ]
    )
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "downloading 25.0%" in output
    assert '"codec": "opus"' in output


def test_audio_command_reports_domain_error(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FailingExtractor:
        def extract(self, request: AudioExtractionRequest, **_kwargs: Any) -> AudioExtractionResult:
            raise MediaDownloadError(f"failed to extract {request.source.value}")

    monkeypatch.setattr(mevad.cli, "YtDlpAudioExtractor", FailingExtractor)

    exit_code = main(["extract-audio", "https://example.com/audio"])

    assert exit_code == 2
    assert "audio error: failed to extract" in capsys.readouterr().out


def test_cut_command_prints_progress_and_result(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    input_path = tmp_path / "input.mp4"

    class FakeCutter:
        def cut(
            self,
            request: VideoCutRequest,
            *,
            on_progress: Any = None,
        ) -> VideoCutResult:
            assert request.input_path == input_path
            assert request.interval == ClipInterval(1.0, 2.5)
            assert request.mode is CutMode.FAST
            on_progress(DownloadProgress(status=DownloadStatus.PROCESSING))
            return VideoCutResult(
                output_path=tmp_path / "clip.mp4",
                duration_seconds=1.5,
                filesize_bytes=25,
                mode=CutMode.FAST,
            )

    monkeypatch.setattr(mevad.cli, "FFmpegVideoCutter", FakeCutter)

    exit_code = main(
        [
            "cut-video",
            str(input_path),
            "--start",
            "1",
            "--end",
            "2.5",
            "--output",
            str(tmp_path),
            "--mode",
            "fast",
        ]
    )
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "processing" in output
    assert '"duration_seconds": 1.5' in output
    assert '"mode": "fast"' in output


def test_cut_command_reports_invalid_interval(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(
        [
            "cut-video",
            "input.mp4",
            "--start",
            "2",
            "--end",
            "1",
        ]
    )

    assert exit_code == 2
    assert "cut error: Clip end must be greater" in capsys.readouterr().out

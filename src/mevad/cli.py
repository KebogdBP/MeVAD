"""Command-line adapter for the MeVAD core."""

import argparse
import json
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path

from mevad import __version__
from mevad.adapters import YtDlpAnalyzer, YtDlpVideoDownloader
from mevad.exceptions import InvalidSourceURLError, MediaAnalysisError, MediaDownloadError
from mevad.models import (
    DownloadProgress,
    MediaSource,
    SourceKind,
    VideoContainer,
    VideoDownloadRequest,
    VideoQuality,
)
from mevad.runtime import discover_runtime_tools
from mevad.security import normalize_remote_url


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mevad",
        description="MegaDownloader Video & Audio command-line interface.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("doctor", help="Check local runtime dependencies.")

    validate = commands.add_parser(
        "validate-url",
        help="Validate a remote media URL without accessing the network.",
    )
    validate.add_argument("url")

    analyze = commands.add_parser(
        "analyze",
        help="Analyze remote media metadata through yt-dlp.",
    )
    analyze.add_argument("url")

    download = commands.add_parser(
        "download-video",
        help="Download one remote video.",
    )
    download.add_argument("url")
    download.add_argument(
        "--output",
        type=Path,
        default=Path("downloads"),
        help="Output directory (default: downloads).",
    )
    download.add_argument(
        "--quality",
        choices=[quality.value for quality in VideoQuality],
        default=VideoQuality.BEST.value,
    )
    download.add_argument(
        "--container",
        choices=[container.value for container in VideoContainer],
        default=VideoContainer.AUTO.value,
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "doctor":
        tools = discover_runtime_tools()
        print(f"ffmpeg: {tools.ffmpeg or 'not found'}")
        print(f"ffprobe: {tools.ffprobe or 'not found'}")
        return 0 if tools.ready else 1

    if args.command == "validate-url":
        try:
            normalized_url = normalize_remote_url(args.url)
        except InvalidSourceURLError as error:
            print(f"invalid URL: {error}")
            return 2
        print(normalized_url)
        return 0

    if args.command == "analyze":
        try:
            analysis = YtDlpAnalyzer().analyze(
                MediaSource(kind=SourceKind.REMOTE_URL, value=args.url)
            )
        except (InvalidSourceURLError, MediaAnalysisError) as error:
            print(f"analysis error: {error}")
            return 2
        print(json.dumps(asdict(analysis), ensure_ascii=False, indent=2))
        return 0

    if args.command == "download-video":
        request = VideoDownloadRequest(
            source=MediaSource(kind=SourceKind.REMOTE_URL, value=args.url),
            output_directory=args.output,
            quality=VideoQuality(args.quality),
            container=VideoContainer(args.container),
        )
        try:
            result = YtDlpVideoDownloader().download(
                request,
                on_progress=_print_download_progress,
            )
        except (InvalidSourceURLError, MediaDownloadError) as error:
            print(f"download error: {error}")
            return 2
        except KeyboardInterrupt:
            print("download cancelled")
            return 130
        print(
            json.dumps(
                {
                    "media_id": result.media_id,
                    "title": result.title,
                    "output_path": str(result.output_path),
                    "filesize_bytes": result.filesize_bytes,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    build_parser().error("unknown command")
    return 2


def _print_download_progress(progress: DownloadProgress) -> None:
    percent = progress.fraction
    percent_text = f" {percent:.1%}" if percent is not None else ""
    print(f"{progress.status.value}{percent_text}")


if __name__ == "__main__":
    raise SystemExit(main())

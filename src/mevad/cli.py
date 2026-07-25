"""Command-line adapter for the MeVAD core."""

import argparse
import json
from collections.abc import Sequence
from dataclasses import asdict

from mevad import __version__
from mevad.adapters import YtDlpAnalyzer
from mevad.exceptions import InvalidSourceURLError, MediaAnalysisError
from mevad.models import MediaSource, SourceKind
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

    build_parser().error("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

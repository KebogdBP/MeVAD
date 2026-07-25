"""Discovery of external media-processing tools."""

import os
import shutil
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RuntimeTools:
    """Resolved paths for external runtime executables."""

    ffmpeg: str | None
    ffprobe: str | None

    @property
    def ready(self) -> bool:
        return self.ffmpeg is not None and self.ffprobe is not None


def discover_runtime_tools() -> RuntimeTools:
    """Resolve configured tools, falling back to PATH."""

    return RuntimeTools(
        ffmpeg=_resolve_tool("MEVAD_FFMPEG_PATH", "ffmpeg"),
        ffprobe=_resolve_tool("MEVAD_FFPROBE_PATH", "ffprobe"),
    )


def _resolve_tool(variable: str, executable: str) -> str | None:
    configured_path = os.environ.get(variable, "").strip()
    if configured_path:
        return configured_path
    return shutil.which(executable)

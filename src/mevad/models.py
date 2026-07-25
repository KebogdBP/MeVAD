"""Typed domain models shared by CLI and future application adapters."""

from dataclasses import dataclass
from enum import StrEnum


class SourceKind(StrEnum):
    """Supported source categories."""

    REMOTE_URL = "remote_url"
    LOCAL_FILE = "local_file"


@dataclass(frozen=True, slots=True)
class MediaSource:
    """A normalized media source accepted by the core."""

    kind: SourceKind
    value: str

"""Domain exceptions exposed by the MeVAD core."""


class MeVADError(Exception):
    """Base class for expected domain errors."""


class InvalidSourceURLError(MeVADError, ValueError):
    """Raised when a source URL is invalid or unsafe."""


class MissingRuntimeToolError(MeVADError):
    """Raised when a required external runtime tool is unavailable."""


class MediaAnalysisError(MeVADError):
    """Raised when media metadata cannot be analyzed."""


class UnsupportedMediaError(MediaAnalysisError):
    """Raised when extracted metadata does not describe supported media."""

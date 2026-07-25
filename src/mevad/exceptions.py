"""Domain exceptions exposed by the MeVAD core."""


class MeVADError(Exception):
    """Base class for expected domain errors."""


class InvalidSourceURLError(MeVADError, ValueError):
    """Raised when a source URL is invalid or unsafe."""


class MissingRuntimeToolError(MeVADError):
    """Raised when a required external runtime tool is unavailable."""

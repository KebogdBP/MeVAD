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


class MediaDownloadError(MeVADError):
    """Raised when a media download cannot be completed."""


class DownloadCancelledError(MediaDownloadError):
    """Raised when a download is cancelled by its caller."""


class MediaProcessingError(MeVADError):
    """Raised when local media processing cannot be completed."""


class InvalidClipIntervalError(MediaProcessingError, ValueError):
    """Raised when a requested clip interval is invalid."""


class JobError(MeVADError):
    """Base class for job system errors."""


class JobNotFoundError(JobError):
    """Raised when a job identifier does not exist."""


class InvalidJobTransitionError(JobError):
    """Raised when a job state transition is not allowed."""


class ConcurrentJobUpdateError(JobError):
    """Raised when optimistic job version validation fails."""


class JobQueueError(JobError):
    """Raised when a job cannot be published to or claimed from the queue."""

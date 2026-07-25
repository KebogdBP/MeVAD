from mevad.runtime import RuntimeTools


def test_runtime_is_ready_when_both_tools_are_available() -> None:
    assert RuntimeTools(ffmpeg="/bin/ffmpeg", ffprobe="/bin/ffprobe").ready


def test_runtime_is_not_ready_when_one_tool_is_missing() -> None:
    assert not RuntimeTools(ffmpeg="/bin/ffmpeg", ffprobe=None).ready

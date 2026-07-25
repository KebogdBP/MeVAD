from mevad.cli import main


def test_validate_url_command_prints_normalized_url(capsys: object) -> None:
    exit_code = main(["validate-url", "https://Example.com/video#fragment"])

    assert exit_code == 0
    assert capsys.readouterr().out == "https://example.com/video\n"  # type: ignore[attr-defined]


def test_validate_url_command_rejects_private_address(capsys: object) -> None:
    exit_code = main(["validate-url", "http://127.0.0.1/video"])

    assert exit_code == 2
    assert "invalid URL:" in capsys.readouterr().out  # type: ignore[attr-defined]

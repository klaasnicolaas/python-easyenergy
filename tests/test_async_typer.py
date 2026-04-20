"""Test the async Typer helper."""

from __future__ import annotations

import click
import pytest
import typer
from typer.testing import CliRunner

from easyenergy.cli.async_typer import AsyncTyper


def test_async_typer_supports_async_command_and_handler() -> None:
    """Test async commands and registered error handlers."""
    runner = CliRunner()
    app = AsyncTyper()

    class BoomError(Exception):
        """Custom CLI error."""

    @app.command()
    async def ok() -> None:
        typer.echo("async command")

    @app.command()
    def fail() -> None:
        msg = "boom"
        raise BoomError(msg)

    @app.error_handler(BoomError)
    def handle_boom(exception: Exception) -> None:
        typer.echo(str(exception))
        raise typer.Exit(code=1)

    ok_result = runner.invoke(app, ["ok"])
    with pytest.raises(click.exceptions.Exit) as exit_error:
        app(args=["fail"], prog_name="easyenergy", standalone_mode=False)

    assert ok_result.exit_code == 0
    assert "async command" in ok_result.output
    assert exit_error.value.exit_code == 1


def test_async_typer_returns_exit_code_for_handled_error_in_standalone_mode(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test handled errors return exit code without traceback in standalone mode."""
    app = AsyncTyper()

    class BoomError(Exception):
        """Custom CLI error."""

    @app.command()
    def fail() -> None:
        msg = "boom"
        raise BoomError(msg)

    @app.error_handler(BoomError)
    def handle_boom(_: Exception) -> None:
        typer.echo("boom")
        raise typer.Exit(code=1)

    assert app(args=[], prog_name="easyenergy") == 1
    captured = capsys.readouterr()
    assert "boom" in captured.out
    assert "Traceback" not in captured.err


def test_async_typer_supports_sync_callback_and_sync_command() -> None:
    """Test sync callbacks and sync commands."""
    runner = CliRunner()
    app = AsyncTyper()
    calls: list[str] = []

    @app.callback()
    def main() -> None:
        calls.append("callback")

    @app.command()
    def ping() -> None:
        typer.echo("pong")

    result = runner.invoke(app, ["ping"])

    assert result.exit_code == 0
    assert "pong" in result.output
    assert calls == ["callback"]


def test_async_typer_supports_async_callback() -> None:
    """Test async callbacks are wrapped correctly."""
    runner = CliRunner()
    app = AsyncTyper()
    calls: list[str] = []

    @app.callback()
    async def main() -> None:
        calls.append("async callback")

    @app.command()
    def ping() -> None:
        typer.echo("pong")

    result = runner.invoke(app, ["ping"])

    assert result.exit_code == 0
    assert "pong" in result.output
    assert calls == ["async callback"]


def test_async_typer_reraises_unhandled_exception_without_handler() -> None:
    """Test unhandled exceptions are re-raised."""
    app = AsyncTyper()

    @app.command()
    def fail() -> None:
        msg = "broken"
        raise RuntimeError(msg)

    with pytest.raises(RuntimeError, match="broken"):
        app(args=[], prog_name="easyenergy", standalone_mode=False)


def test_async_typer_reraises_unhandled_exception_with_other_handlers() -> None:
    """Test unhandled exceptions are re-raised with a different handler registry."""
    app = AsyncTyper()

    @app.command()
    def fail() -> None:
        msg = "broken"
        raise RuntimeError(msg)

    @app.error_handler(ValueError)
    def handle_value_error(_: Exception) -> None:
        raise typer.Exit(code=1)

    with pytest.raises(RuntimeError, match="broken"):
        app(args=[], prog_name="easyenergy", standalone_mode=False)


def test_async_typer_propagates_exit() -> None:
    """Test Typer exits are propagated unchanged."""
    app = AsyncTyper()

    @app.command()
    def stop() -> None:
        raise typer.Exit(code=2)

    assert app(args=[], prog_name="easyenergy", standalone_mode=False) == 2

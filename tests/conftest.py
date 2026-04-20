"""Fixture for the easyEnergy tests."""

from collections.abc import AsyncGenerator

import pytest
from aiohttp import ClientSession

from easyenergy import EasyEnergy


@pytest.fixture(name="stable_terminal")
def fixture_stable_terminal(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force deterministic Rich rendering for CLI tests."""
    monkeypatch.setenv("COLUMNS", "100")
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setenv("TERM", "dumb")


@pytest.fixture(name="easyenergy_client")
async def client() -> AsyncGenerator[EasyEnergy, None]:
    """Fixture to create a EasyEnergy client."""
    async with (
        ClientSession() as session,
        EasyEnergy(session=session) as easyenergy_client,
    ):
        yield easyenergy_client

"""Basic tests for the easyEnergy API."""

# pylint: disable=protected-access
import asyncio
from unittest.mock import patch

import pytest
from aiohttp import ClientError, ClientResponse, ClientSession
from aresponses import Response, ResponsesMockServer

from easyenergy import EasyEnergy
from easyenergy.exceptions import EasyEnergyConnectionError, EasyEnergyError

from . import load_fixtures


async def test_json_request(
    aresponses: ResponsesMockServer, easyenergy_client: EasyEnergy
) -> None:
    """Test JSON response is handled correctly."""
    aresponses.add(
        "mijn.easyenergy.com",
        "/nl/api/tariff/test",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixtures("energy.json"),
        ),
    )
    response = await easyenergy_client._request("test")
    assert response is not None
    await easyenergy_client.close()


async def test_internal_session(aresponses: ResponsesMockServer) -> None:
    """Test internal session is handled correctly."""
    aresponses.add(
        "mijn.easyenergy.com",
        "/nl/api/tariff/test",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixtures("energy.json"),
        ),
    )
    async with EasyEnergy() as client:
        await client._request("test")


async def test_timeout(aresponses: ResponsesMockServer) -> None:
    """Test request timeout is handled correctly."""

    # Faking a timeout by sleeping
    async def reponse_handler(_: ClientResponse) -> Response:
        await asyncio.sleep(0.2)
        return aresponses.Response(body="Goodmorning!")

    aresponses.add("mijn.easyenergy.com", "/nl/api/tariff/test", "GET", reponse_handler)

    async with ClientSession() as session:
        client = EasyEnergy(session=session, request_timeout=0.1)
        with pytest.raises(EasyEnergyConnectionError):
            assert await client._request("test")


async def test_content_type(
    aresponses: ResponsesMockServer, easyenergy_client: EasyEnergy
) -> None:
    """Test request content type error is handled correctly."""
    aresponses.add(
        "mijn.easyenergy.com",
        "/nl/api/tariff/test",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "blabla/blabla"},
        ),
    )
    with pytest.raises(EasyEnergyError):
        assert await easyenergy_client._request("test")


async def test_client_error() -> None:
    """Test request client error is handled correctly."""
    async with ClientSession() as session:
        client = EasyEnergy(session=session)
        with (
            patch.object(
                session,
                "request",
                side_effect=ClientError,
            ),
            pytest.raises(EasyEnergyConnectionError),
        ):
            assert await client._request("test")

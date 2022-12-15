"""Test the models."""
from datetime import datetime, timezone
from unittest.mock import Mock, patch

import aiohttp
import pytest
from aresponses import ResponsesMockServer

from easyenergy import EasyEnergy, EasyEnergyNoDataError, Electricity, Gas

from . import load_fixtures


@pytest.mark.asyncio
@patch(
    "easyenergy.models.Electricity.utcnow",
    Mock(return_value=datetime(2022, 12, 14, 14, 0).replace(tzinfo=timezone.utc)),
)
async def test_electricity_model_usage(aresponses: ResponsesMockServer) -> None:
    """Test the electricity model for usage."""
    aresponses.add(
        "mijn.easyenergy.com",
        "/nl/api/tariff/getapxtariffs",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixtures("energy.json"),
        ),
    )
    async with aiohttp.ClientSession() as session:
        today = datetime.strptime("2022-12-14", "%Y-%m-%d")
        client = EasyEnergy(session=session)
        energy: Electricity = await client.energy_prices(
            start_date=today, end_date=today
        )
        assert energy is not None and isinstance(energy, Electricity)
        assert energy.extreme_usage_prices[1] == 0.6431
        assert energy.extreme_usage_prices[0] == 0.29463
        assert energy.average_usage_price == 0.47735
        assert energy.current_usage_price == 0.5761
        # The next hour price
        next_hour = datetime(2022, 12, 14, 15, 0).replace(tzinfo=timezone.utc)
        assert energy.price_at_time(next_hour) == 0.59405
        assert energy.lowest_usage_price_time == datetime.strptime(
            "2022-12-13 23:00", "%Y-%m-%d %H:%M"
        ).replace(tzinfo=timezone.utc)
        assert energy.highest_usage_price_time == datetime.strptime(
            "2022-12-14 16:00", "%Y-%m-%d %H:%M"
        ).replace(tzinfo=timezone.utc)
        assert energy.pct_of_max_usage == 89.58
        assert isinstance(energy.timestamp_useage_prices, list)


@pytest.mark.asyncio
@patch(
    "easyenergy.models.Electricity.utcnow",
    Mock(return_value=datetime(2022, 12, 14, 14, 0).replace(tzinfo=timezone.utc)),
)
async def test_electricity_model_return(aresponses: ResponsesMockServer) -> None:
    """Test the electricity model for return."""
    aresponses.add(
        "mijn.easyenergy.com",
        "/nl/api/tariff/getapxtariffs",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixtures("energy.json"),
        ),
    )
    async with aiohttp.ClientSession() as session:
        today = datetime.strptime("2022-12-14", "%Y-%m-%d")
        client = EasyEnergy(session=session)
        energy: Electricity = await client.energy_prices(
            start_date=today, end_date=today
        )
        assert energy is not None and isinstance(energy, Electricity)
        assert energy.extreme_return_prices[1] == 0.59
        assert energy.extreme_return_prices[0] == 0.2703
        assert energy.average_return_price == 0.43794
        assert energy.current_return_price == 0.5761
        # The next hour price
        next_hour = datetime(2022, 12, 14, 15, 0).replace(tzinfo=timezone.utc)
        assert energy.price_at_time(next_hour, "return") == 0.545
        assert energy.lowest_return_price_time == datetime.strptime(
            "2022-12-13 23:00", "%Y-%m-%d %H:%M"
        ).replace(tzinfo=timezone.utc)
        assert energy.highest_return_price_time == datetime.strptime(
            "2022-12-14 16:00", "%Y-%m-%d %H:%M"
        ).replace(tzinfo=timezone.utc)
        assert energy.pct_of_max_return == 97.64
        assert isinstance(energy.timestamp_return_prices, list)


@pytest.mark.asyncio
async def test_no_electricity_data(aresponses: ResponsesMockServer) -> None:
    """Test when there is no electricity data."""
    aresponses.add(
        "mijn.easyenergy.com",
        "/nl/api/tariff/getapxtariffs",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text="[]",
        ),
    )
    async with aiohttp.ClientSession() as session:
        today = datetime.strptime("2022-12-16", "%Y-%m-%d")
        client = EasyEnergy(session=session)
        with pytest.raises(EasyEnergyNoDataError):
            await client.energy_prices(start_date=today, end_date=today)


@pytest.mark.asyncio
@patch(
    "easyenergy.models.Gas.utcnow",
    Mock(return_value=datetime(2022, 12, 14, 14, 0).replace(tzinfo=timezone.utc)),
)
async def test_gas_model(aresponses: ResponsesMockServer) -> None:
    """Test the gas model - easyEnergy."""
    aresponses.add(
        "mijn.easyenergy.com",
        "/nl/api/tariff/getlebatariffs",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixtures("gas.json"),
        ),
    )
    async with aiohttp.ClientSession() as session:
        today = datetime.strptime("2022-12-14", "%Y-%m-%d")
        client = EasyEnergy(session=session)
        gas: Gas = await client.gas_prices(start_date=today, end_date=today)
        assert gas is not None and isinstance(gas, Gas)
        assert gas.extreme_prices[1] == 1.48534
        assert gas.extreme_prices[0] == 1.4645
        assert gas.average_price == 1.48013
        assert gas.current_price == 1.48534


@pytest.mark.asyncio
async def test_no_gas_data(aresponses: ResponsesMockServer) -> None:
    """Test when there is no gas data."""
    aresponses.add(
        "mijn.easyenergy.com",
        "/nl/api/tariff/getlebatariffs",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text="[]",
        ),
    )
    async with aiohttp.ClientSession() as session:
        today = datetime.strptime("2022-12-16", "%Y-%m-%d")
        client = EasyEnergy(session=session)
        with pytest.raises(EasyEnergyNoDataError):
            await client.gas_prices(start_date=today, end_date=today)

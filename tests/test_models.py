"""Test the models."""
from datetime import date, datetime, timezone

import aiohttp
import pytest
from aresponses import ResponsesMockServer

from easyenergy import EasyEnergy, EasyEnergyNoDataError, Electricity, Gas

from . import load_fixtures


@pytest.mark.asyncio
@pytest.mark.freeze_time("2022-12-29 14:00:00 UTC")
async def test_electricity_model_usage(aresponses: ResponsesMockServer) -> None:
    """Test the electricity model for usage at 14:00:00 UTC."""
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
        today = date(2022, 12, 29)
        client = EasyEnergy(session=session)
        energy: Electricity = await client.energy_prices(
            start_date=today, end_date=today
        )
        assert energy is not None and isinstance(energy, Electricity)
        assert energy.extreme_usage_prices[1] == 0.13345
        assert energy.extreme_usage_prices[0] == -0.00277
        assert energy.average_usage_price == 0.07133
        assert energy.current_usage_price == 0.1199
        # The next hour price
        next_hour = datetime(2022, 12, 29, 15, 0).replace(tzinfo=timezone.utc)
        assert energy.price_at_time(next_hour) == 0.11979
        assert energy.lowest_usage_price_time == datetime.strptime(
            "2022-12-29 02:00", "%Y-%m-%d %H:%M"
        ).replace(tzinfo=timezone.utc)
        assert energy.highest_usage_price_time == datetime.strptime(
            "2022-12-29 17:00", "%Y-%m-%d %H:%M"
        ).replace(tzinfo=timezone.utc)
        assert energy.pct_of_max_usage == 89.85
        assert isinstance(energy.timestamp_useage_prices, list)


@pytest.mark.asyncio
@pytest.mark.freeze_time("2022-12-29 14:00:00 UTC")
async def test_electricity_model_return(aresponses: ResponsesMockServer) -> None:
    """Test the electricity model for return at 14:00:00 UTC."""
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
        today = date(2022, 12, 29)
        client = EasyEnergy(session=session)
        energy: Electricity = await client.energy_prices(
            start_date=today, end_date=today
        )
        assert energy is not None and isinstance(energy, Electricity)
        assert energy.extreme_return_prices[1] == 0.12243
        assert energy.extreme_return_prices[0] == -0.00254
        assert energy.average_return_price == 0.06544
        assert energy.current_return_price == 0.11
        # The next hour price
        next_hour = datetime(2022, 12, 29, 15, 0).replace(tzinfo=timezone.utc)
        assert energy.price_at_time(next_hour, data_type="return") == 0.1099
        assert energy.lowest_return_price_time == datetime.strptime(
            "2022-12-29 02:00", "%Y-%m-%d %H:%M"
        ).replace(tzinfo=timezone.utc)
        assert energy.highest_return_price_time == datetime.strptime(
            "2022-12-29 17:00", "%Y-%m-%d %H:%M"
        ).replace(tzinfo=timezone.utc)
        assert energy.pct_of_max_return == 89.85
        assert isinstance(energy.timestamp_return_prices, list)


@pytest.mark.asyncio
async def test_electricity_none_data(aresponses: ResponsesMockServer) -> None:
    """Test when there is no data for the current datetime."""
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
        today = date(2022, 12, 29)
        client = EasyEnergy(session=session)
        energy: Electricity = await client.energy_prices(
            start_date=today, end_date=today
        )
        assert energy is not None and isinstance(energy, Electricity)
        assert energy.current_return_price is None
        assert energy.average_return_price == 0.06544


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
        today = date(2022, 12, 16)
        client = EasyEnergy(session=session)
        with pytest.raises(EasyEnergyNoDataError):
            await client.energy_prices(start_date=today, end_date=today)


@pytest.mark.asyncio
@pytest.mark.freeze_time("2022-12-14 14:00:00 UTC")
async def test_gas_model(aresponses: ResponsesMockServer) -> None:
    """Test the gas model - easyEnergy at 14:00:00 UTC."""
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
        today = date(2022, 12, 14)
        client = EasyEnergy(session=session)
        gas: Gas = await client.gas_prices(start_date=today, end_date=today)
        assert gas is not None and isinstance(gas, Gas)
        assert gas.extreme_prices[1] == 1.48534
        assert gas.extreme_prices[0] == 1.4645
        assert gas.average_price == 1.48013
        assert gas.current_price == 1.48534


@pytest.mark.asyncio
@pytest.mark.freeze_time("2022-12-14 03:00:00 UTC")
async def test_gas_morning_model(aresponses: ResponsesMockServer) -> None:
    """Test the gas model in the morning - easyEnergy at 03:00:00 UTC."""
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
        today = date(2022, 12, 14)
        client = EasyEnergy(session=session)
        gas: Gas = await client.gas_prices(start_date=today, end_date=today)
        assert gas is not None and isinstance(gas, Gas)
        assert gas.extreme_prices[1] == 1.48534
        assert gas.extreme_prices[0] == 1.4645
        assert gas.average_price == 1.48013
        assert gas.current_price == 1.4645


@pytest.mark.asyncio
async def test_gas_none_data(aresponses: ResponsesMockServer) -> None:
    """Test when there is no data for the current datetime."""
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
        today = date(2022, 12, 14)
        client = EasyEnergy(session=session)
        gas: Gas = await client.gas_prices(start_date=today, end_date=today)
        assert gas is not None and isinstance(gas, Gas)
        assert gas.current_price is None
        assert gas.average_price == 1.48013


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
        today = date(2022, 12, 16)
        client = EasyEnergy(session=session)
        with pytest.raises(EasyEnergyNoDataError):
            await client.gas_prices(start_date=today, end_date=today)

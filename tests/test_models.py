"""Test the models."""

from datetime import UTC, date, datetime

import pytest
from aresponses import ResponsesMockServer
from syrupy.assertion import SnapshotAssertion

from easyenergy import EasyEnergy, EasyEnergyNoDataError, Electricity, Gas, VatOption

from . import load_fixtures


@pytest.mark.freeze_time("2022-12-29 15:00:00+01:00")
async def test_electricity_model_usage(
    aresponses: ResponsesMockServer,
    snapshot: SnapshotAssertion,
    easyenergy_client: EasyEnergy,
) -> None:
    """Test the electricity model for usage at 15:00:00 CET."""
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
    today = date(2022, 12, 29)
    energy: Electricity = await easyenergy_client.energy_prices(
        start_date=today,
        end_date=today,
        vat=VatOption.INCLUDE,
    )
    assert energy == snapshot
    assert isinstance(energy, Electricity)

    # Test the electricity model
    assert energy.extreme_usage_prices[1] == 0.13345
    assert energy.extreme_usage_prices[0] == -0.00277
    assert energy.average_usage_price == 0.06941
    assert energy.current_usage_price == 0.1199

    # The next hour price
    next_hour = datetime(2022, 12, 29, 15, 0, tzinfo=UTC)
    assert energy.price_at_time(next_hour) == 0.11979
    assert energy.lowest_usage_price_time == datetime.strptime(
        "2022-12-29 02:00",
        "%Y-%m-%d %H:%M",
    ).replace(tzinfo=UTC)
    assert energy.highest_usage_price_time == datetime.strptime(
        "2022-12-29 17:00",
        "%Y-%m-%d %H:%M",
    ).replace(tzinfo=UTC)

    assert energy.pct_of_max_usage == 89.85
    assert isinstance(energy.timestamp_usage_prices, list)
    assert energy.hours_priced_equal_or_lower_usage == 21
    assert energy.hours_priced_equal_or_higher_return == 5


@pytest.mark.freeze_time("2022-12-29 15:00:00+01:00")
async def test_electricity_model_return(
    aresponses: ResponsesMockServer,
    snapshot: SnapshotAssertion,
    easyenergy_client: EasyEnergy,
) -> None:
    """Test the electricity model for return at 15:00:00 CET."""
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
    today = date(2022, 12, 29)
    energy: Electricity = await easyenergy_client.energy_prices(
        start_date=today,
        end_date=today,
        vat=VatOption.INCLUDE,
    )
    assert energy == snapshot
    assert isinstance(energy, Electricity)

    # Test the electricity model
    assert energy.extreme_return_prices[1] == 0.12243
    assert energy.extreme_return_prices[0] == -0.00254
    assert energy.average_return_price == 0.06368
    assert energy.current_return_price == 0.11

    # The next hour price
    next_hour = datetime(2022, 12, 29, 15, 0, tzinfo=UTC)
    assert energy.price_at_time(next_hour, data_type="return") == 0.1099
    assert energy.lowest_return_price_time == datetime.strptime(
        "2022-12-29 02:00",
        "%Y-%m-%d %H:%M",
    ).replace(tzinfo=UTC)
    assert energy.highest_return_price_time == datetime.strptime(
        "2022-12-29 17:00",
        "%Y-%m-%d %H:%M",
    ).replace(tzinfo=UTC)
    assert energy.pct_of_max_return == 89.85
    assert isinstance(energy.timestamp_return_prices, list)


@pytest.mark.freeze_time("2022-12-29 00:30:00+02:00")
async def test_electricity_midnight(
    aresponses: ResponsesMockServer,
    snapshot: SnapshotAssertion,
    easyenergy_client: EasyEnergy,
) -> None:
    """Test the electricity model between 00:00 and 01:00 with in CEST."""
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
    today = date(2022, 12, 29)
    energy: Electricity = await easyenergy_client.energy_prices(
        start_date=today,
        end_date=today,
        vat=VatOption.INCLUDE,
    )
    assert energy == snapshot
    assert isinstance(energy, Electricity)

    # Test the electricity model
    assert energy.current_usage_price == 0.02341
    assert energy.current_return_price == 0.02148


async def test_electricity_none_data(
    aresponses: ResponsesMockServer,
    snapshot: SnapshotAssertion,
    easyenergy_client: EasyEnergy,
) -> None:
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
    today = date(2022, 12, 29)
    energy: Electricity = await easyenergy_client.energy_prices(
        start_date=today,
        end_date=today,
    )
    assert energy == snapshot
    assert isinstance(energy, Electricity)
    assert energy.current_return_price is None
    assert energy.average_return_price == 0.06368


async def test_no_electricity_data(
    aresponses: ResponsesMockServer,
    easyenergy_client: EasyEnergy,
) -> None:
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
    today = date(2022, 12, 16)
    with pytest.raises(EasyEnergyNoDataError):
        await easyenergy_client.energy_prices(start_date=today, end_date=today)


@pytest.mark.freeze_time("2022-12-14 15:00:00+01:00")
async def test_gas_model(
    aresponses: ResponsesMockServer,
    snapshot: SnapshotAssertion,
    easyenergy_client: EasyEnergy,
) -> None:
    """Test the gas model - easyEnergy at 15:00:00 CET."""
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
    today = date(2022, 12, 14)
    gas: Gas = await easyenergy_client.gas_prices(
        start_date=today,
        end_date=today,
        vat=VatOption.INCLUDE,
    )
    assert gas == snapshot
    assert isinstance(gas, Gas)

    # Test the gas model
    assert gas.extreme_prices[1] == 1.48534
    assert gas.extreme_prices[0] == 1.4645
    assert gas.average_price == 1.47951
    assert gas.current_price == 1.48534
    assert isinstance(gas.timestamp_prices, list)


@pytest.mark.freeze_time("2022-12-14 04:00:00+01:00")
async def test_gas_morning_model(
    aresponses: ResponsesMockServer,
    snapshot: SnapshotAssertion,
    easyenergy_client: EasyEnergy,
) -> None:
    """Test the gas model in the morning - easyEnergy at 04:00:00 CET."""
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
    today = date(2022, 12, 14)
    gas: Gas = await easyenergy_client.gas_prices(
        start_date=today,
        end_date=today,
        vat=VatOption.INCLUDE,
    )
    assert gas == snapshot
    assert isinstance(gas, Gas)
    assert gas.extreme_prices[1] == 1.48534
    assert gas.extreme_prices[0] == 1.4645
    assert gas.average_price == 1.47951
    assert gas.current_price == 1.4645


async def test_gas_none_data(
    aresponses: ResponsesMockServer,
    snapshot: SnapshotAssertion,
    easyenergy_client: EasyEnergy,
) -> None:
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
    today = date(2022, 12, 14)
    gas: Gas = await easyenergy_client.gas_prices(
        start_date=today,
        end_date=today,
    )
    assert gas == snapshot
    assert isinstance(gas, Gas)
    assert gas.current_price is None
    assert gas.average_price == 1.47951


async def test_no_gas_data(
    aresponses: ResponsesMockServer,
    easyenergy_client: EasyEnergy,
) -> None:
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
    today = date(2022, 12, 16)
    with pytest.raises(EasyEnergyNoDataError):
        await easyenergy_client.gas_prices(start_date=today, end_date=today)

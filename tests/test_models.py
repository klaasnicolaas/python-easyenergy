"""Test the models."""

from datetime import UTC, date, datetime, timedelta

import pytest
from aresponses import ResponsesMockServer
from syrupy.assertion import SnapshotAssertion

from easyenergy import (
    EasyEnergy,
    EasyEnergyNoDataError,
    Electricity,
    ElectricityGranularity,
    Gas,
    PriceInterval,
    VatOption,
)
from easyenergy.models import _normalize_moment, _normalize_timestamp, _parse_timestamp

from . import load_fixtures

API_HOST = "price-graph.acc-mijn.easyenergy.com"


def _electricity_snapshot(energy: Electricity) -> dict[str, object]:
    """Return a stable snapshot view for electricity data."""
    return {
        "intervals": energy.intervals,
        "current": {
            "market_excluding_vat": energy.current_market_price_excluding_vat,
            "market": energy.current_market_price,
            "invoice": energy.current_invoice_price,
            "usage": energy.current_price,
            "return": energy.current_return_price,
        },
        "extremes": {
            "usage": energy.extreme_prices,
            "return": energy.extreme_return_prices,
        },
        "averages": {
            "usage": energy.average_price,
            "return": energy.average_return_price,
        },
        "times": {
            "highest_usage": energy.highest_price_time,
            "lowest_usage": energy.lowest_price_time,
            "highest_return": energy.highest_return_price_time,
            "lowest_return": energy.lowest_return_price_time,
        },
        "series": {
            "usage": energy.timestamp_prices,
            "market_excluding_vat": energy.timestamp_market_prices_excluding_vat,
            "market": energy.timestamp_market_prices,
            "invoice": energy.timestamp_invoice_prices,
            "return": energy.timestamp_return_prices,
        },
    }


def _gas_snapshot(gas: Gas) -> dict[str, object]:
    """Return a stable snapshot view for gas data."""
    return {
        "intervals": gas.intervals,
        "current_price": gas.current_price,
        "extremes": gas.extreme_prices,
        "average_price": gas.average_price,
        "series": gas.timestamp_prices,
    }


@pytest.mark.freeze_time("2026-04-19 15:00:00+02:00")
async def test_electricity_model_usage(
    aresponses: ResponsesMockServer,
    easyenergy_client: EasyEnergy,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the electricity model with hourly prices."""
    aresponses.add(
        API_HOST,
        "/api/prices",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixtures("energy.json"),
        ),
    )
    today = date(2026, 4, 19)
    energy: Electricity = await easyenergy_client.energy_prices(
        start_date=today,
        end_date=today,
        vat=VatOption.INCLUDE,
    )

    assert isinstance(energy, Electricity)
    assert energy.intervals[0] == PriceInterval(
        starts_at=datetime(2026, 4, 18, 22, 0, tzinfo=UTC),
        ends_at=datetime(2026, 4, 18, 23, 0, tzinfo=UTC),
        price=0.11549,
        price_inc_vat=0.13975,
        energy_tax=0.11085,
        purchase_price=0.02178,
        invoice_price=0.27238,
        average=0.0786,
        average_inc=0.09516,
        unit="kWh",
        granularity="hour",
    )
    assert energy.price_at_time(datetime(2026, 4, 19, 14, 0, tzinfo=UTC)) == 0.01631
    assert (
        energy.return_price_at_time(datetime(2026, 4, 19, 14, 0, tzinfo=UTC)) == 0.01631
    )
    assert energy.market_prices == energy.return_prices
    assert energy.periods_priced_equal_or_lower == 2
    assert energy.return_periods_priced_equal_or_higher == 23
    assert _electricity_snapshot(energy) == snapshot


@pytest.mark.freeze_time("2026-04-19 14:37:00+02:00")
async def test_electricity_model_quarter_prices(
    aresponses: ResponsesMockServer,
    easyenergy_client: EasyEnergy,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the electricity model with quarter prices."""
    aresponses.add(
        API_HOST,
        "/api/prices",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixtures("energy_quarter.json"),
        ),
    )
    today = date(2026, 4, 19)
    energy: Electricity = await easyenergy_client.energy_prices(
        start_date=today,
        end_date=today,
        vat=VatOption.INCLUDE,
        granularity=ElectricityGranularity.QUARTER,
    )

    assert isinstance(energy, Electricity)
    assert energy.current_market_price == -0.00304
    assert energy.current_invoice_price == 0.12959
    assert energy.current_price == -0.00304
    assert energy.current_return_price == -0.00304
    assert energy.price_at_time(datetime(2026, 4, 19, 12, 46, tzinfo=UTC)) == -0.00439
    assert energy.timestamp_prices == energy.timestamp_return_prices
    assert _electricity_snapshot(energy) == snapshot


@pytest.mark.freeze_time("2026-04-19 15:00:00+02:00")
async def test_electricity_model_invoice_usage(
    aresponses: ResponsesMockServer,
    easyenergy_client: EasyEnergy,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the electricity model exposes invoice prices alongside market prices."""
    aresponses.add(
        API_HOST,
        "/api/prices",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixtures("energy.json"),
        ),
    )
    today = date(2026, 4, 19)
    energy: Electricity = await easyenergy_client.energy_prices(
        start_date=today,
        end_date=today,
        vat=VatOption.EXCLUDE,
    )

    assert isinstance(energy, Electricity)
    assert energy.current_market_price == -0.00226
    assert energy.current_invoice_price == 0.13037
    assert energy.price_at_time(datetime(2026, 4, 19, 14, 0, tzinfo=UTC)) == 0.01348
    assert (
        energy.return_price_at_time(datetime(2026, 4, 19, 14, 0, tzinfo=UTC)) == 0.01631
    )
    assert energy.timestamp_prices != energy.timestamp_return_prices
    assert _electricity_snapshot(energy) == snapshot


@pytest.mark.freeze_time("2026-04-20 02:00:00+02:00")
async def test_electricity_none_data(
    aresponses: ResponsesMockServer,
    easyenergy_client: EasyEnergy,
) -> None:
    """Test when there is no data for the current datetime."""
    aresponses.add(
        API_HOST,
        "/api/prices",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixtures("energy.json"),
        ),
    )
    today = date(2026, 4, 19)
    energy: Electricity = await easyenergy_client.energy_prices(
        start_date=today,
        end_date=today,
    )

    assert isinstance(energy, Electricity)
    assert energy.current_return_price is None
    assert energy.current_price is None


async def test_no_electricity_data(
    aresponses: ResponsesMockServer,
    easyenergy_client: EasyEnergy,
) -> None:
    """Test when there is no electricity data."""
    aresponses.add(
        API_HOST,
        "/api/prices",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text='{"providedAt":"2026-04-19T22:16:43.9481189Z","prices":[]}',
        ),
    )
    today = date(2026, 4, 19)
    with pytest.raises(EasyEnergyNoDataError):
        await easyenergy_client.energy_prices(start_date=today, end_date=today)


@pytest.mark.freeze_time("2026-04-02 15:00:00+02:00")
async def test_gas_model(
    aresponses: ResponsesMockServer,
    easyenergy_client: EasyEnergy,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the gas model with VAT included."""
    aresponses.add(
        API_HOST,
        "/api/prices",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixtures("gas.json"),
        ),
    )
    today = date(2026, 4, 1)
    gas: Gas = await easyenergy_client.gas_prices(
        start_date=today,
        end_date=date(2026, 4, 2),
        vat=VatOption.INCLUDE,
    )

    assert isinstance(gas, Gas)
    assert gas.extreme_prices == (0.57862, 0.6169)
    assert gas.average_price == 0.59776
    assert gas.current_price == 0.57862
    assert gas.price_at_time(datetime(2026, 4, 1, 23, 0, tzinfo=UTC)) == 0.57862
    assert _gas_snapshot(gas) == snapshot


@pytest.mark.freeze_time("2026-04-02 15:00:00+02:00")
async def test_gas_model_excluding_vat(
    aresponses: ResponsesMockServer,
    easyenergy_client: EasyEnergy,
) -> None:
    """Test the gas model with VAT excluded."""
    aresponses.add(
        API_HOST,
        "/api/prices",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixtures("gas.json"),
        ),
    )
    today = date(2026, 4, 1)
    gas: Gas = await easyenergy_client.gas_prices(
        start_date=today,
        end_date=date(2026, 4, 2),
        vat=VatOption.EXCLUDE,
    )

    assert isinstance(gas, Gas)
    assert gas.current_price == 0.4782
    assert gas.average_price == 0.49401


@pytest.mark.freeze_time("2026-04-03 10:00:00+02:00")
async def test_gas_none_data(
    aresponses: ResponsesMockServer,
    easyenergy_client: EasyEnergy,
) -> None:
    """Test when there is no data for the current datetime."""
    aresponses.add(
        API_HOST,
        "/api/prices",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixtures("gas.json"),
        ),
    )
    today = date(2026, 4, 1)
    gas: Gas = await easyenergy_client.gas_prices(
        start_date=today,
        end_date=date(2026, 4, 2),
    )

    assert isinstance(gas, Gas)
    assert gas.current_price is None


async def test_no_gas_data(
    aresponses: ResponsesMockServer,
    easyenergy_client: EasyEnergy,
) -> None:
    """Test when there is no gas data."""
    aresponses.add(
        API_HOST,
        "/api/prices",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text='{"providedAt":"2026-04-19T22:16:43.4740091Z","prices":[]}',
        ),
    )
    today = date(2026, 4, 1)
    with pytest.raises(EasyEnergyNoDataError):
        await easyenergy_client.gas_prices(start_date=today, end_date=today)


def test_normalize_timestamp_variants() -> None:
    """Test timestamp normalization for all supported API formats."""
    assert _normalize_timestamp("2026-04-19T00:00:00Z") == "2026-04-19T00:00:00+00:00"
    assert _normalize_timestamp("2026-04-19T00:00:00") == "2026-04-19T00:00:00"
    assert (
        _normalize_timestamp("2026-04-19T00:00:00.1234567")
        == "2026-04-19T00:00:00.123456"
    )
    assert (
        _normalize_timestamp("2026-04-19T00:00:00.1234567+02:00")
        == "2026-04-19T00:00:00.123456+02:00"
    )
    assert (
        _normalize_timestamp("2026-04-19T00:00:00.1234567-05:00")
        == "2026-04-19T00:00:00.123456-05:00"
    )


def test_parse_timestamp_and_normalize_moment() -> None:
    """Test timestamp parsing and naive datetime normalization."""
    assert _parse_timestamp("2026-04-19T00:00:00+02:00") == datetime(
        2026,
        4,
        18,
        22,
        0,
        tzinfo=UTC,
    )
    assert _parse_timestamp("2026-04-19T00:00:00") == datetime(
        2026,
        4,
        18,
        22,
        0,
        tzinfo=UTC,
    )
    assert _normalize_moment(datetime(2026, 4, 19, 0, 0)) == datetime(  # noqa: DTZ001
        2026,
        4,
        19,
        0,
        0,
        tzinfo=UTC,
    )


@pytest.mark.freeze_time("2026-04-19 12:30:00+00:00")
def test_electricity_accessors_and_invalid_data_type(
    snapshot: SnapshotAssertion,
) -> None:
    """Test electricity accessors not covered by API fixture tests."""
    start = datetime(2026, 4, 19, 12, 0, tzinfo=UTC)
    middle = start + timedelta(hours=1)
    end = middle + timedelta(hours=1)
    energy = Electricity(
        intervals=(
            PriceInterval(
                starts_at=start,
                ends_at=middle,
                price=0.5,
                price_inc_vat=1.0,
                energy_tax=0.1,
                purchase_price=0.2,
                invoice_price=1.1,
                average=0.75,
                average_inc=1.5,
                unit="kWh",
                granularity="hour",
            ),
            PriceInterval(
                starts_at=middle,
                ends_at=end,
                price=1.0,
                price_inc_vat=2.0,
                energy_tax=0.1,
                purchase_price=0.2,
                invoice_price=2.1,
                average=0.75,
                average_inc=1.5,
                unit="kWh",
                granularity="hour",
            ),
        ),
        prices={start: 1.0, middle: 2.0},
        _return_prices={start: 0.5, middle: 1.0},
        price_ends={start: middle, middle: end},
    )

    assert energy.prices == {start: 1.0, middle: 2.0}
    assert energy.highest_return_price_time == middle
    assert energy.lowest_return_price_time == start
    assert energy.pct_of_max == 50.0
    assert energy.pct_of_max_return == 50.0
    assert energy.periods_priced_equal_or_higher == 2
    assert energy.price_at_time(start - timedelta(minutes=1)) is None
    assert _electricity_snapshot(energy) == snapshot


def test_electricity_from_dict_defaults_return_prices_to_usage_prices() -> None:
    """Test Electricity.from_dict without an explicit return price key."""
    energy = Electricity.from_dict(
        [
            {
                "from": "2026-04-19T12:00:00.0000000",
                "until": "2026-04-19T13:00:00.0000000",
                "price": 0.5,
                "priceIncVat": 0.6,
                "energyTax": 0.1,
                "purchasePrice": 0.2,
                "invoicePrice": 0.8,
                "average": 0.5,
                "averageInc": 0.6,
                "unit": "kWh",
                "granularity": "hour",
            }
        ],
        price_key="price",
    )

    assert energy.intervals[0].invoice_price == 0.8
    assert energy.return_prices == energy.prices


def test_electricity_from_dict_uses_explicit_return_price_key() -> None:
    """Test Electricity.from_dict with an explicit return price key."""
    energy = Electricity.from_dict(
        [
            {
                "from": "2026-04-19T12:00:00.0000000",
                "until": "2026-04-19T13:00:00.0000000",
                "price": 0.5,
                "priceIncVat": 0.6,
                "energyTax": 0.1,
                "purchasePrice": 0.2,
                "invoicePrice": 0.8,
                "average": 0.5,
                "averageInc": 0.6,
                "unit": "kWh",
                "granularity": "hour",
            }
        ],
        price_key="price",
        return_price_key="priceIncVat",
    )

    assert energy.prices != energy.return_prices
    assert energy.prices == {
        datetime(2026, 4, 19, 10, 0, tzinfo=UTC): 0.5,
    }
    assert energy.return_prices == {
        datetime(2026, 4, 19, 10, 0, tzinfo=UTC): 0.6,
    }

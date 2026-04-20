"""Test the easyEnergy CLI."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING

import click
import pytest
from syrupy.assertion import SnapshotAssertion
from typer.testing import CliRunner

from easyenergy import (
    EasyEnergy,
    Electricity,
    ElectricityGranularity,
    ElectricityPriceType,
    Gas,
    VatOption,
)
from easyenergy.cli import (
    _format_entity_value,
    _interval_price,
    _intervals_table,
    _render_interval_rows,
    _selected_prices,
    cli,
    default_request_date,
    format_interval,
    format_local,
    format_period,
    format_price,
    resolve_period,
    run,
)
from easyenergy.exceptions import (
    EasyEnergyConnectionError,
    EasyEnergyError,
    EasyEnergyNoDataError,
)

from . import load_fixtures

if TYPE_CHECKING:
    from collections.abc import Callable


def _normalize_cli_output(output: str) -> str:
    """Normalize Rich CLI output for stable snapshots."""
    lines = [line.rstrip() for line in output.splitlines()]
    return "\n".join(lines).strip("\n") + "\n"


def _load_energy(
    *,
    vat: VatOption = VatOption.INCLUDE,
    granularity: ElectricityGranularity = ElectricityGranularity.HOUR,
) -> Electricity:
    """Create an Electricity model from a fixture."""
    fixture = (
        "energy_quarter.json"
        if granularity == ElectricityGranularity.QUARTER
        else "energy.json"
    )
    price_key = "priceIncVat" if vat == VatOption.INCLUDE else "price"
    return Electricity.from_dict(
        json.loads(load_fixtures(fixture))["prices"],
        price_key=price_key,
        return_price_key="priceIncVat",
    )


def _load_gas(*, vat: VatOption = VatOption.INCLUDE) -> Gas:
    """Create a Gas model from a fixture."""
    price_key = "priceIncVat" if vat == VatOption.INCLUDE else "price"
    return Gas.from_dict(
        json.loads(load_fixtures("gas.json"))["prices"],
        price_key=price_key,
    )


@pytest.mark.freeze_time("2026-04-20 10:00:00+02:00")
def test_cli_helper_functions(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test shared CLI helpers."""
    period = resolve_period()
    explicit_period = resolve_period(date_value="2026-04-19")
    ranged_period = resolve_period(
        start_date="2026-04-19",
        end_date="2026-04-20",
    )
    energy = _load_energy(granularity=ElectricityGranularity.QUARTER)

    class FakeApp:
        """Small callable CLI stub."""

        def __init__(self) -> None:
            self.called = False

        def __call__(self) -> None:
            self.called = True

    fake_app = FakeApp()
    monkeypatch.setattr("easyenergy.cli.cli", fake_app)

    assert default_request_date() == date(2026, 4, 19)
    assert period.start_date == date(2026, 4, 19)
    assert explicit_period.end_date == date(2026, 4, 19)
    assert format_period(ranged_period) == "2026-04-19 -> 2026-04-20"
    assert format_local(datetime(2026, 4, 19, 12, 0, tzinfo=UTC)).endswith("CEST")
    assert format_price(None) == "-"
    assert format_price(0.123456) == "0.12346"
    assert format_interval(energy.intervals[0]).endswith("quarter/kWh")
    assert _interval_price(energy.prices, energy, 999) is None

    run()
    assert fake_app.called is True


def test_cli_resolve_period_errors() -> None:
    """Test invalid period resolution."""
    with pytest.raises(Exception, match="cannot be combined"):
        resolve_period(
            date_value="2026-04-19",
            start_date="2026-04-19",
        )

    with pytest.raises(Exception, match="on or after"):
        resolve_period(
            start_date="2026-04-20",
            end_date="2026-04-19",
        )

    with pytest.raises(Exception, match="Expected YYYY-MM-DD"):
        resolve_period(date_value="2026-99-99")


def test_cli_energy_command(
    monkeypatch: pytest.MonkeyPatch,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the electricity CLI command."""
    runner = CliRunner()

    async def fake_energy_prices(
        self: EasyEnergy,
        start_date: date,
        end_date: date,
        vat: VatOption | None = None,
        granularity: ElectricityGranularity = ElectricityGranularity.HOUR,
    ) -> Electricity:
        assert start_date == date(2026, 4, 19)
        assert end_date == date(2026, 4, 19)
        assert vat is None
        return _load_energy(
            vat=self.vat if vat is None else vat,
            granularity=granularity,
        )

    monkeypatch.setattr(EasyEnergy, "energy_prices", fake_energy_prices)

    result = runner.invoke(
        cli,
        [
            "energy",
            "--date",
            "2026-04-19",
            "--granularity",
            "quarter",
            "--price-type",
            "invoice",
            "--limit",
            "2",
        ],
    )

    assert result.exit_code == 0
    assert _normalize_cli_output(result.output) == snapshot


def test_cli_gas_command(
    monkeypatch: pytest.MonkeyPatch,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the gas CLI command."""
    runner = CliRunner()

    async def fake_gas_prices(
        self: EasyEnergy,
        start_date: date,
        end_date: date,
        vat: VatOption | None = None,
    ) -> Gas:
        assert start_date == date(2026, 4, 1)
        assert end_date == date(2026, 4, 2)
        return _load_gas(vat=self.vat if vat is None else vat)

    monkeypatch.setattr(EasyEnergy, "gas_prices", fake_gas_prices)

    result = runner.invoke(
        cli,
        [
            "gas",
            "--start-date",
            "2026-04-01",
            "--end-date",
            "2026-04-02",
            "--limit",
            "1",
        ],
    )

    assert result.exit_code == 0
    assert _normalize_cli_output(result.output) == snapshot


def test_cli_prices_list_command(
    monkeypatch: pytest.MonkeyPatch,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the raw interval CLI command."""
    runner = CliRunner()

    async def fake_energy_prices(
        self: EasyEnergy,
        start_date: date,
        end_date: date,
        vat: VatOption | None = None,
        granularity: ElectricityGranularity = ElectricityGranularity.HOUR,
    ) -> Electricity:
        assert start_date == date(2026, 4, 19)
        assert end_date == date(2026, 4, 19)
        assert granularity == ElectricityGranularity.QUARTER
        return _load_energy(
            vat=self.vat if vat is None else vat,
            granularity=granularity,
        )

    async def fake_gas_prices(
        self: EasyEnergy,
        start_date: date,
        end_date: date,
        vat: VatOption | None = None,
    ) -> Gas:
        assert start_date == date(2026, 4, 19)
        assert end_date == date(2026, 4, 19)
        return _load_gas(vat=self.vat if vat is None else vat)

    monkeypatch.setattr(EasyEnergy, "energy_prices", fake_energy_prices)
    monkeypatch.setattr(EasyEnergy, "gas_prices", fake_gas_prices)

    result = runner.invoke(
        cli,
        [
            "prices-list",
            "--date",
            "2026-04-19",
            "--price-type",
            "invoice",
            "--limit",
            "2",
        ],
    )

    assert result.exit_code == 0
    assert _normalize_cli_output(result.output) == snapshot


def test_cli_render_interval_rows_without_limit() -> None:
    """Test rendering all interval rows when no limit is provided."""
    energy = _load_energy()
    table = _intervals_table("Returned intervals")

    _render_interval_rows(
        table,
        energy.intervals,
        prices=energy.prices,
        limit=None,
    )

    assert len(table.rows) == len(energy.intervals)


@pytest.mark.freeze_time("2026-04-19 15:00:00+02:00")
def test_cli_selected_prices_helper(snapshot: SnapshotAssertion) -> None:
    """Test CLI price selection helper."""
    energy = _load_energy(vat=VatOption.EXCLUDE)

    include_market = _selected_prices(
        energy, vat=VatOption.INCLUDE, price_type=ElectricityPriceType.MARKET
    )
    exclude_market = _selected_prices(
        energy, vat=VatOption.EXCLUDE, price_type=ElectricityPriceType.MARKET
    )
    invoice = _selected_prices(
        energy, vat=VatOption.INCLUDE, price_type=ElectricityPriceType.INVOICE
    )

    assert {
        "include_market_prices": include_market[0],
        "include_market_current": include_market[1],
        "exclude_market_prices": exclude_market[0],
        "exclude_market_current": exclude_market[1],
        "invoice_prices": invoice[0],
        "invoice_current": invoice[1],
    } == snapshot


def test_cli_invalid_period_command() -> None:
    """Test invalid command line date combinations."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "energy",
            "--date",
            "2026-04-19",
            "--start-date",
            "2026-04-19",
        ],
    )

    assert result.exit_code == 2
    assert "--date cannot be combined" in result.output


def test_cli_no_data_handler(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    snapshot: SnapshotAssertion,
) -> None:
    """Test handled no-data errors."""

    async def fake_energy_prices(
        self: EasyEnergy,
        start_date: date,
        end_date: date,
        vat: VatOption | None = None,
        granularity: ElectricityGranularity = ElectricityGranularity.HOUR,
    ) -> Electricity:
        assert isinstance(self, EasyEnergy)
        assert start_date == date(2026, 4, 19)
        assert end_date == date(2026, 4, 19)
        assert vat is None
        assert granularity == ElectricityGranularity.HOUR
        msg = "No energy prices found for this period."
        raise EasyEnergyNoDataError(msg)

    monkeypatch.setattr(EasyEnergy, "energy_prices", fake_energy_prices)

    result = cli(args=["energy", "--date", "2026-04-19"], prog_name="easyenergy")

    captured = capsys.readouterr()

    assert result == 1
    assert _normalize_cli_output(captured.err) == snapshot


@pytest.mark.parametrize(
    ("handler", "exception"),
    [
        (
            lambda: cli.error_handlers[EasyEnergyConnectionError],
            EasyEnergyConnectionError("Connection failed."),
        ),
        (lambda: cli.error_handlers[EasyEnergyError], EasyEnergyError("API failed.")),
    ],
)
def test_cli_error_handlers(
    handler: Callable[[], Callable[[Exception], None]],
    exception: Exception,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test the Rich-backed error handlers."""
    with pytest.raises(click.exceptions.Exit) as exit_error:
        handler()(exception)

    captured = capsys.readouterr()

    assert exit_error.value.exit_code == 1
    assert str(exception) in captured.err


def test_cli_entities_command(
    monkeypatch: pytest.MonkeyPatch,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the entities overview CLI command."""
    runner = CliRunner()

    async def fake_energy_prices(
        self: EasyEnergy,
        start_date: date,
        end_date: date,
        vat: VatOption | None = None,
        granularity: ElectricityGranularity = ElectricityGranularity.HOUR,
    ) -> Electricity:
        _ = (start_date, end_date, granularity)
        return _load_energy(vat=self.vat if vat is None else vat)

    async def fake_gas_prices(
        self: EasyEnergy,
        start_date: date,
        end_date: date,
        vat: VatOption | None = None,
    ) -> Gas:
        _ = (start_date, end_date)
        return _load_gas(vat=self.vat if vat is None else vat)

    monkeypatch.setattr(EasyEnergy, "energy_prices", fake_energy_prices)
    monkeypatch.setattr(EasyEnergy, "gas_prices", fake_gas_prices)

    result = runner.invoke(
        cli,
        ["entities", "--date", "2026-04-19"],
    )

    assert result.exit_code == 0
    assert _normalize_cli_output(result.output) == snapshot


@pytest.mark.freeze_time("2026-04-19 14:30:00+02:00")
def test_cli_format_entity_value() -> None:
    """Test the entity value formatter."""
    energy = _load_energy()

    assert _format_entity_value(None) == "-"
    assert _format_entity_value(0.12345) == "0.12345"
    assert _format_entity_value(42) == "42"
    assert _format_entity_value((0.1, 0.2)) == "(0.10000, 0.20000)"
    assert _format_entity_value(energy.prices) == f"<{len(energy.prices)} intervals>"
    assert _format_entity_value([1, 2, 3]) == "<3 items>"
    assert _format_entity_value("test") == "test"
    assert "CEST" in _format_entity_value(energy.intervals[0].starts_at)

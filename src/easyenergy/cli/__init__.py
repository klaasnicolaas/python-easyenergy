"""Command line interface for easyEnergy."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING, Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from easyenergy.cli.async_typer import AsyncTyper
from easyenergy.const import (
    MARKET_TIMEZONE,
    ElectricityGranularity,
    ElectricityPriceType,
    VatOption,
)
from easyenergy.easyenergy import EasyEnergy
from easyenergy.exceptions import (
    EasyEnergyConnectionError,
    EasyEnergyError,
    EasyEnergyNoDataError,
)

if TYPE_CHECKING:
    from easyenergy.models import Electricity, Gas, PriceInterval

cli = AsyncTyper(
    help="easyEnergy CLI",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()
error_console = Console(stderr=True)

DateOption = Annotated[
    str | None,
    typer.Option(
        "--date",
        help="Single day to request. Defaults to yesterday in Europe/Amsterdam.",
    ),
]
StartDateOption = Annotated[
    str | None,
    typer.Option(
        "--start-date",
        help="Start date to request. Defaults to yesterday in Europe/Amsterdam.",
    ),
]
EndDateOption = Annotated[
    str | None,
    typer.Option(
        "--end-date",
        help="End date to request. Defaults to the start date.",
    ),
]
VatOptionArg = Annotated[
    VatOption,
    typer.Option("--vat", help="Use VAT included or excluded prices."),
]
GranularityOption = Annotated[
    ElectricityGranularity,
    typer.Option("--granularity", help="Electricity granularity to request."),
]
PriceTypeOption = Annotated[
    ElectricityPriceType,
    typer.Option("--price-type", help="Electricity usage price type to request."),
]
LimitOption = Annotated[
    int | None,
    typer.Option(
        "--limit",
        min=1,
        help="Max intervals to print. Defaults to all returned intervals.",
    ),
]


@dataclass(frozen=True, slots=True)
class RequestPeriod:
    """Requested period for a CLI fetch."""

    start_date: date
    end_date: date


def default_request_date() -> date:
    """Return a stable default date for live CLI requests."""
    return datetime.now(MARKET_TIMEZONE).date() - timedelta(days=1)


def parse_date(value: str) -> date:
    """Parse a CLI date in ISO format."""
    try:
        return date.fromisoformat(value)
    except ValueError as exception:
        msg = f"Invalid date: {value!r}. Expected YYYY-MM-DD."
        raise typer.BadParameter(msg) from exception


def resolve_period(
    *,
    date_value: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> RequestPeriod:
    """Resolve CLI date arguments into a concrete request period."""
    if date_value and (start_date or end_date):
        msg = "--date cannot be combined with --start-date or --end-date"
        raise typer.BadParameter(msg)

    if date_value:
        resolved_date = parse_date(date_value)
        return RequestPeriod(start_date=resolved_date, end_date=resolved_date)

    resolved_start = parse_date(start_date) if start_date else default_request_date()
    resolved_end = parse_date(end_date) if end_date else resolved_start
    if resolved_end < resolved_start:
        msg = "--end-date must be on or after --start-date"
        raise typer.BadParameter(msg)

    return RequestPeriod(start_date=resolved_start, end_date=resolved_end)


def format_local(moment: datetime) -> str:
    """Format a timestamp in the market timezone."""
    return moment.astimezone(MARKET_TIMEZONE).strftime("%Y-%m-%d %H:%M:%S %Z")


def format_period(period: RequestPeriod) -> str:
    """Format a request period for display."""
    if period.start_date == period.end_date:
        return period.start_date.isoformat()
    return f"{period.start_date.isoformat()} -> {period.end_date.isoformat()}"


def format_price(value: float | None) -> str:
    """Format a price value for display."""
    if value is None:
        return "-"
    return f"{value:.5f}"


def format_interval(interval: PriceInterval) -> str:
    """Format a full interval row."""
    return (
        f"{format_local(interval.starts_at)} -> {format_local(interval.ends_at)} | "
        f"market={interval.price:.5f} | inc_vat={interval.price_inc_vat:.5f} | "
        f"tax={interval.energy_tax:.5f} | purchase={interval.purchase_price:.5f} | "
        f"invoice={interval.invoice_price:.5f} | "
        f"{interval.granularity}/{interval.unit}"
    )


def _interval_price(
    prices: dict[datetime, float],
    energy: Electricity,
    index: int,
) -> float | None:
    """Return the selected series value for an interval."""
    if index >= len(energy.intervals):
        return None
    return prices.get(energy.intervals[index].starts_at)


def _summary_table(title: str) -> Table:
    """Create a summary table."""
    table = Table(title=title, show_header=False, header_style="bold cyan")
    table.add_column("Field", style="bold green")
    table.add_column("Value")
    return table


def _intervals_table(title: str, *, selected_label: str = "Selected") -> Table:
    """Create a table for interval rows."""
    table = Table(title=title, header_style="bold cyan")
    table.add_column("Start", style="bold")
    table.add_column("End")
    table.add_column(selected_label, justify="right")
    table.add_column("Market", justify="right")
    table.add_column("Inc VAT", justify="right")
    table.add_column("Tax", justify="right")
    table.add_column("Purchase", justify="right")
    table.add_column("Invoice", justify="right")
    table.add_column("Unit")
    return table


def _render_interval_rows(
    table: Table,
    intervals: tuple[PriceInterval, ...],
    *,
    prices: dict[datetime, float],
    limit: int | None,
) -> None:
    """Populate an interval table."""
    selected_intervals = intervals if limit is None else intervals[:limit]
    for interval in selected_intervals:
        table.add_row(
            format_local(interval.starts_at),
            format_local(interval.ends_at),
            format_price(prices.get(interval.starts_at)),
            format_price(interval.price),
            format_price(interval.price_inc_vat),
            format_price(interval.energy_tax),
            format_price(interval.purchase_price),
            format_price(interval.invoice_price),
            f"{interval.granularity}/{interval.unit}",
        )


def _selected_prices(
    energy: Electricity,
    *,
    vat: VatOption,
    price_type: ElectricityPriceType,
) -> tuple[
    dict[datetime, float], float | None, tuple[float, float], float, datetime, datetime
]:
    """Return price data for the selected usage series.

    Returns (prices, current, extremes, average, lowest_time, highest_time).
    """
    if price_type == ElectricityPriceType.INVOICE:
        prices = energy.invoice_prices
        current = energy.current_invoice_price
    elif vat == VatOption.EXCLUDE:
        prices = energy.market_prices_excluding_vat
        current = energy.current_market_price_excluding_vat
    else:
        prices = energy.market_prices
        current = energy.current_market_price

    values = list(prices.values())
    lowest = round(min(values), 5)
    highest = round(max(values), 5)
    average = round(sum(values) / len(values), 5)
    lowest_time = min(prices, key=prices.__getitem__)
    highest_time = max(prices, key=prices.__getitem__)

    return prices, current, (lowest, highest), average, lowest_time, highest_time


def _print_energy_summary(
    energy: Electricity,
    period: RequestPeriod,
    *,
    vat: VatOption,
    price_type: ElectricityPriceType,
    limit: int | None,
) -> None:
    """Print a readable electricity summary."""
    first_interval = energy.intervals[0]
    prices, current, extremes, average, lowest_time, highest_time = _selected_prices(
        energy, vat=vat, price_type=price_type
    )

    summary = _summary_table("Electricity")
    summary.add_row("Requested period", format_period(period))
    summary.add_row("Returned intervals", str(len(energy.intervals)))
    summary.add_row("Usage price type", price_type.value)
    summary.add_row("Granularity", first_interval.granularity)
    summary.add_row("Unit", first_interval.unit)
    summary.add_row("Current market", format_price(energy.current_market_price))
    summary.add_row("Current invoice", format_price(energy.current_invoice_price))
    summary.add_row("Current selected usage", format_price(current))
    summary.add_row("First usage", format_price(_interval_price(prices, energy, 0)))
    summary.add_row(
        "First return",
        format_price(_interval_price(energy.return_prices, energy, 0)),
    )
    summary.add_row("Average usage", format_price(average))
    summary.add_row("Average return", format_price(energy.average_return_price))
    summary.add_row("Lowest usage", format_price(extremes[0]))
    summary.add_row("Highest usage", format_price(extremes[1]))
    summary.add_row("Lowest usage at", format_local(lowest_time))
    summary.add_row("Highest usage at", format_local(highest_time))
    summary.add_row("Lowest return at", format_local(energy.lowest_return_price_time))
    summary.add_row("Highest return at", format_local(energy.highest_return_price_time))

    intervals = _intervals_table("Returned intervals", selected_label="Usage")
    _render_interval_rows(intervals, energy.intervals, prices=prices, limit=limit)

    console.print(summary)
    console.print(intervals)


def _print_gas_summary(
    gas: Gas,
    period: RequestPeriod,
    *,
    limit: int | None,
) -> None:
    """Print a readable gas summary."""
    interval = gas.intervals[0]

    summary = _summary_table("Gas")
    summary.add_row("Requested period", format_period(period))
    summary.add_row("Returned intervals", str(len(gas.intervals)))
    summary.add_row("Unit", interval.unit)
    summary.add_row("Selected price", format_price(gas.prices[interval.starts_at]))
    summary.add_row("Average price", format_price(gas.average_price))
    summary.add_row("Lowest price", format_price(gas.extreme_prices[0]))
    summary.add_row("Highest price", format_price(gas.extreme_prices[1]))
    summary.add_row("First interval", format_interval(interval))

    intervals = _intervals_table("Returned intervals", selected_label="Price")
    _render_interval_rows(
        intervals,
        gas.intervals,
        prices=gas.prices,
        limit=limit,
    )

    console.print(summary)
    console.print(intervals)


def _handle_cli_exception(exception: Exception) -> None:
    """Render a handled CLI exception."""
    error_console.print(
        Panel.fit(
            str(exception),
            title="easyEnergy",
            border_style="red",
        ),
    )
    raise typer.Exit(code=1)


@cli.error_handler(EasyEnergyConnectionError)
def connection_error_handler(exception: EasyEnergyConnectionError) -> None:
    """Render a handled connection error."""
    _handle_cli_exception(exception)


@cli.error_handler(EasyEnergyError)
def api_error_handler(exception: EasyEnergyError) -> None:
    """Render a handled API error."""
    _handle_cli_exception(exception)


@cli.error_handler(EasyEnergyNoDataError)
def no_data_error_handler(exception: EasyEnergyNoDataError) -> None:
    """Render a handled no-data error."""
    _handle_cli_exception(exception)


@cli.command("energy")
async def command_energy(  # noqa: PLR0913  # pylint: disable=too-many-arguments,too-many-positional-arguments
    date_value: DateOption = None,
    start_date: StartDateOption = None,
    end_date: EndDateOption = None,
    vat: VatOptionArg = VatOption.INCLUDE,
    granularity: GranularityOption = ElectricityGranularity.HOUR,
    price_type: PriceTypeOption = ElectricityPriceType.MARKET,
    limit: LimitOption = None,
) -> None:
    """Fetch electricity prices for a day or date range."""
    period = resolve_period(
        date_value=date_value,
        start_date=start_date,
        end_date=end_date,
    )
    async with EasyEnergy(vat=vat) as client:
        prices = await client.energy_prices(
            start_date=period.start_date,
            end_date=period.end_date,
            granularity=granularity,
        )
    _print_energy_summary(prices, period, vat=vat, price_type=price_type, limit=limit)


@cli.command("gas")
async def command_gas(
    date_value: DateOption = None,
    start_date: StartDateOption = None,
    end_date: EndDateOption = None,
    vat: VatOptionArg = VatOption.INCLUDE,
    limit: LimitOption = None,
) -> None:
    """Fetch gas prices for a day or date range."""
    period = resolve_period(
        date_value=date_value,
        start_date=start_date,
        end_date=end_date,
    )
    async with EasyEnergy(vat=vat) as client:
        prices = await client.gas_prices(
            start_date=period.start_date,
            end_date=period.end_date,
        )
    _print_gas_summary(prices, period, limit=limit)


@cli.command("prices-list")
async def command_prices_list(  # noqa: PLR0913  # pylint: disable=too-many-arguments,too-many-positional-arguments
    date_value: DateOption = None,
    start_date: StartDateOption = None,
    end_date: EndDateOption = None,
    vat: VatOptionArg = VatOption.INCLUDE,
    granularity: GranularityOption = ElectricityGranularity.QUARTER,
    price_type: PriceTypeOption = ElectricityPriceType.MARKET,
    limit: LimitOption = None,
) -> None:
    """Fetch raw electricity and gas interval rows."""
    period = resolve_period(
        date_value=date_value,
        start_date=start_date,
        end_date=end_date,
    )
    async with EasyEnergy(vat=vat) as client:
        energy_prices = await client.energy_prices(
            start_date=period.start_date,
            end_date=period.end_date,
            granularity=granularity,
        )
        gas_prices = await client.gas_prices(
            start_date=period.start_date,
            end_date=period.end_date,
        )

    prices, *_ = _selected_prices(energy_prices, vat=vat, price_type=price_type)
    energy_table = _intervals_table(
        f"Electricity intervals ({format_period(period)})",
        selected_label="Usage",
    )
    _render_interval_rows(
        energy_table,
        energy_prices.intervals,
        prices=prices,
        limit=limit,
    )
    gas_table = _intervals_table(
        f"Gas intervals ({format_period(period)})",
        selected_label="Price",
    )
    _render_interval_rows(
        gas_table,
        gas_prices.intervals,
        prices=gas_prices.prices,
        limit=limit,
    )

    console.print(energy_table)
    console.print(gas_table)


# pylint: disable-next=too-many-return-statements
def _format_entity_value(value: object) -> str:  # noqa: PLR0911
    """Format an entity value for display."""
    if value is None:
        return "-"
    if isinstance(value, datetime):
        return format_local(value)
    if isinstance(value, tuple) and len(value) == 2:
        return f"({value[0]:.5f}, {value[1]:.5f})"
    if isinstance(value, float):
        return format_price(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, dict):
        return f"<{len(value)} intervals>"
    if isinstance(value, list):
        return f"<{len(value)} items>"
    return str(value)


def _entity_table(title: str) -> Table:
    """Create an entity table."""
    table = Table(title=title, header_style="bold cyan")
    table.add_column("Entity", style="bold green")
    table.add_column("Value", justify="right")
    table.add_column("Description")
    return table


def _print_entities(energy: Electricity, gas: Gas) -> None:
    """Print all available entities for Home Assistant."""
    # Electricity Usage entities
    usage_table = _entity_table("Electricity - Usage")
    usage_entities = [
        ("current_price", energy.current_price, "Current usage price"),
        ("current_market_price", energy.current_market_price, "Market price (inc VAT)"),
        (
            "current_market_price_excluding_vat",
            energy.current_market_price_excluding_vat,
            "Market price (exc VAT)",
        ),
        ("current_invoice_price", energy.current_invoice_price, "Invoice price"),
        ("average_price", energy.average_price, "Average price"),
        ("extreme_prices", energy.extreme_prices, "Min/max price (tuple)"),
        ("highest_price_time", energy.highest_price_time, "Time of highest price"),
        ("lowest_price_time", energy.lowest_price_time, "Time of lowest price"),
        ("pct_of_max", energy.pct_of_max, "Current as % of max"),
        (
            "periods_priced_equal_or_lower",
            energy.periods_priced_equal_or_lower,
            "Intervals <= current",
        ),
        (
            "periods_priced_equal_or_higher",
            energy.periods_priced_equal_or_higher,
            "Intervals >= current",
        ),
        ("prices", energy.prices, "Price series"),
        ("market_prices", energy.market_prices, "Market prices (inc VAT)"),
        (
            "market_prices_excluding_vat",
            energy.market_prices_excluding_vat,
            "Market prices (exc VAT)",
        ),
        ("invoice_prices", energy.invoice_prices, "Invoice prices"),
        ("timestamp_prices", energy.timestamp_prices, "Timestamps + prices"),
        (
            "timestamp_market_prices",
            energy.timestamp_market_prices,
            "Timestamps + market",
        ),
        (
            "timestamp_market_prices_excluding_vat",
            energy.timestamp_market_prices_excluding_vat,
            "Timestamps + market (exc VAT)",
        ),
        (
            "timestamp_invoice_prices",
            energy.timestamp_invoice_prices,
            "Timestamps + invoice",
        ),
    ]
    for name, value, desc in usage_entities:
        usage_table.add_row(name, _format_entity_value(value), desc)

    # Electricity Return entities
    return_table = _entity_table("Electricity - Return")
    return_entities = [
        ("current_return_price", energy.current_return_price, "Current return price"),
        ("average_return_price", energy.average_return_price, "Average return price"),
        (
            "extreme_return_prices",
            energy.extreme_return_prices,
            "Min/max return (tuple)",
        ),
        (
            "highest_return_price_time",
            energy.highest_return_price_time,
            "Time of highest",
        ),
        ("lowest_return_price_time", energy.lowest_return_price_time, "Time of lowest"),
        ("pct_of_max_return", energy.pct_of_max_return, "Current as % of max"),
        (
            "return_periods_priced_equal_or_higher",
            energy.return_periods_priced_equal_or_higher,
            "Intervals >= current",
        ),
        ("return_prices", energy.return_prices, "Return price series"),
        (
            "timestamp_return_prices",
            energy.timestamp_return_prices,
            "Timestamps + return",
        ),
    ]
    for name, value, desc in return_entities:
        return_table.add_row(name, _format_entity_value(value), desc)

    # Gas entities
    gas_table = _entity_table("Gas")
    gas_entities = [
        ("current_price", gas.current_price, "Current price"),
        ("average_price", gas.average_price, "Average price"),
        ("extreme_prices", gas.extreme_prices, "Min/max price (tuple)"),
        ("highest_price_time", gas.highest_price_time, "Time of highest"),
        ("lowest_price_time", gas.lowest_price_time, "Time of lowest"),
        ("prices", gas.prices, "Price series"),
        ("timestamp_prices", gas.timestamp_prices, "Timestamps + prices"),
    ]
    for name, value, desc in gas_entities:
        gas_table.add_row(name, _format_entity_value(value), desc)

    console.print(usage_table)
    console.print(return_table)
    console.print(gas_table)


@cli.command("entities")
async def command_entities(
    date_value: DateOption = None,
    start_date: StartDateOption = None,
    end_date: EndDateOption = None,
    vat: VatOptionArg = VatOption.INCLUDE,
) -> None:
    """Show all available entities for Home Assistant integration."""
    period = resolve_period(
        date_value=date_value,
        start_date=start_date,
        end_date=end_date,
    )
    async with EasyEnergy(vat=vat) as client:
        energy = await client.energy_prices(
            start_date=period.start_date,
            end_date=period.end_date,
        )
        gas = await client.gas_prices(
            start_date=period.start_date,
            end_date=period.end_date,
        )

    console.print(f"\n[bold]Entity overview for {format_period(period)}[/bold]\n")
    _print_entities(energy, gas)


def run() -> None:
    """Run the CLI application."""
    cli()


if __name__ == "__main__":
    run()

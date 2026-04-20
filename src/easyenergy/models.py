"""Data models for the easyEnergy API."""

from __future__ import annotations

from abc import ABC
from bisect import bisect_left, bisect_right
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import cached_property
from typing import TYPE_CHECKING, Any, Self

from mashumaro import field_options
from mashumaro.mixins.dict import DataClassDictMixin

from .const import MARKET_TIMEZONE

if TYPE_CHECKING:
    from collections.abc import Mapping

_PRICE_FIELD_MAP: Mapping[str, str] = {
    "price": "price",
    "priceIncVat": "price_inc_vat",
    "energyTax": "energy_tax",
    "purchasePrice": "purchase_price",
    "invoicePrice": "invoice_price",
    "average": "average",
    "averageInc": "average_inc",
}


def _normalize_timestamp(value: str) -> str:
    """Normalize the API timestamp to a Python compatible ISO string."""
    if value.endswith("Z"):
        value = f"{value[:-1]}+00:00"

    if "." not in value:
        return value

    head, rest = value.split(".", maxsplit=1)
    suffix_index = rest.find("+")
    if suffix_index == -1:
        suffix_index = rest.find("-")

    if suffix_index == -1:
        fraction = rest
        suffix = ""
    else:
        fraction = rest[:suffix_index]
        suffix = rest[suffix_index:]

    return f"{head}.{fraction[:6]}{suffix}"


def _parse_timestamp(value: str) -> datetime:
    """Parse an API timestamp and normalize it to UTC."""
    timestamp = datetime.fromisoformat(_normalize_timestamp(value))
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=MARKET_TIMEZONE)
    return timestamp.astimezone(UTC)


def _normalize_moment(moment: datetime) -> datetime:
    """Normalize a provided datetime to UTC."""
    if moment.tzinfo is None:
        return moment.replace(tzinfo=UTC)
    return moment.astimezone(UTC)


def _timed_value(
    moment: datetime,
    prices: dict[datetime, float],
    price_ends: dict[datetime, datetime],
    interval_starts: tuple[datetime, ...],
) -> float | None:
    """Return the value for a specific timestamp."""
    current_moment = _normalize_moment(moment)
    interval_index = bisect_right(interval_starts, current_moment) - 1
    if interval_index < 0:
        return None

    timestamp = interval_starts[interval_index]
    if current_moment < price_ends[timestamp]:
        return round(prices[timestamp], 5)
    return None


@dataclass(frozen=True, slots=True)
class _PriceSeriesAnalysis:
    """Cached derived data for a price series."""

    extreme_prices: tuple[float, float]
    average_price: float
    highest_price_time: datetime
    lowest_price_time: datetime
    timestamp_prices: list[dict[str, float | datetime]]
    sorted_values: tuple[float, ...]

    def count_equal_or_lower(self, price: float) -> int:
        """Return the number of prices equal to or below a value."""
        return bisect_right(self.sorted_values, price)

    def count_equal_or_higher(self, price: float) -> int:
        """Return the number of prices equal to or above a value."""
        return len(self.sorted_values) - bisect_left(self.sorted_values, price)


def _analyze_prices(prices: dict[datetime, float]) -> _PriceSeriesAnalysis:
    """Return cached statistics for a price series."""
    iterator = iter(prices.items())
    first_timestamp, first_price = next(iterator)

    lowest_time = highest_time = first_timestamp
    lowest_price = highest_price = first_price
    total = first_price
    values = [first_price]
    timestamp_prices = [{"timestamp": first_timestamp, "price": round(first_price, 5)}]

    for timestamp, price in iterator:
        total += price
        values.append(price)
        timestamp_prices.append({"timestamp": timestamp, "price": round(price, 5)})

        if price < lowest_price:
            lowest_price = price
            lowest_time = timestamp

        if price > highest_price:
            highest_price = price
            highest_time = timestamp

    return _PriceSeriesAnalysis(
        extreme_prices=(round(lowest_price, 5), round(highest_price, 5)),
        average_price=round(total / len(values), 5),
        highest_price_time=highest_time,
        lowest_price_time=lowest_time,
        timestamp_prices=timestamp_prices,
        sorted_values=tuple(sorted(values)),
    )


def _interval_starts(intervals: tuple[PriceInterval, ...]) -> tuple[datetime, ...]:
    """Return sorted interval start timestamps for fast lookups."""
    return tuple(interval.starts_at for interval in intervals)


@dataclass(frozen=True, slots=True)
class PriceInterval(DataClassDictMixin):  # pylint: disable=too-many-instance-attributes
    """Single interval from the easyEnergy price API."""

    starts_at: datetime = field(
        metadata=field_options(alias="from", deserialize=_parse_timestamp),
    )
    ends_at: datetime = field(
        metadata=field_options(alias="until", deserialize=_parse_timestamp),
    )
    price: float
    price_inc_vat: float = field(metadata=field_options(alias="priceIncVat"))
    energy_tax: float = field(metadata=field_options(alias="energyTax"))
    purchase_price: float = field(metadata=field_options(alias="purchasePrice"))
    invoice_price: float = field(metadata=field_options(alias="invoicePrice"))
    average: float
    average_inc: float = field(metadata=field_options(alias="averageInc"))
    unit: str
    granularity: str

    def value_for(self, price_key: str) -> float:
        """Return the requested price component for this interval."""
        return getattr(self, _PRICE_FIELD_MAP[price_key])


def _parse_price_data(
    data: list[dict[str, Any]],
    *,
    price_key: str,
) -> tuple[tuple[PriceInterval, ...], dict[datetime, float], dict[datetime, datetime]]:
    """Parse price intervals and the selected price series from the new API payload."""
    intervals = tuple(
        sorted(
            (PriceInterval.from_dict(item) for item in data),
            key=lambda interval: interval.starts_at,
        ),
    )
    return (
        intervals,
        {interval.starts_at: interval.value_for(price_key) for interval in intervals},
        {interval.starts_at: interval.ends_at for interval in intervals},
    )


def _series_from_intervals(
    intervals: tuple[PriceInterval, ...],
    *,
    price_key: str,
) -> dict[datetime, float]:
    """Build a price series for a specific interval price component."""
    return {interval.starts_at: interval.value_for(price_key) for interval in intervals}


@dataclass
class EnergyPrices(ABC):
    """Base class for energy price data."""

    intervals: tuple[PriceInterval, ...]
    prices: dict[datetime, float]
    price_ends: dict[datetime, datetime]

    @cached_property
    def _interval_starts(self) -> tuple[datetime, ...]:
        """Return interval starts for fast point-in-time lookups."""
        return _interval_starts(self.intervals)

    @cached_property
    def _price_analysis(self) -> _PriceSeriesAnalysis:
        """Return cached analytics for the primary prices."""
        return _analyze_prices(self.prices)

    @property
    def current_price(self) -> float | None:
        """Return the price for the current interval."""
        return self.price_at_time(datetime.now(UTC))

    @property
    def extreme_prices(self) -> tuple[float, float]:
        """Return the minimum and maximum price."""
        return self._price_analysis.extreme_prices

    @property
    def average_price(self) -> float:
        """Return the average price."""
        return self._price_analysis.average_price

    @property
    def highest_price_time(self) -> datetime:
        """Return the time of the highest price."""
        return self._price_analysis.highest_price_time

    @property
    def lowest_price_time(self) -> datetime:
        """Return the time of the lowest price."""
        return self._price_analysis.lowest_price_time

    @property
    def timestamp_prices(self) -> list[dict[str, float | datetime]]:
        """Return a list of timestamps and prices."""
        return self._price_analysis.timestamp_prices

    def price_at_time(self, moment: datetime) -> float | None:
        """Return the price at a specific time."""
        return _timed_value(moment, self.prices, self.price_ends, self._interval_starts)


@dataclass
class Electricity(EnergyPrices):  # pylint: disable=too-many-public-methods
    """Object representing electricity data."""

    _return_prices: dict[datetime, float] = field(default_factory=dict)

    @cached_property
    def _return_analysis(self) -> _PriceSeriesAnalysis:
        """Return cached analytics for return prices."""
        return _analyze_prices(self.return_prices)

    @cached_property
    def market_prices_excluding_vat(self) -> dict[datetime, float]:
        """Return the market electricity prices without VAT."""
        return _series_from_intervals(self.intervals, price_key="price")

    @cached_property
    def _market_prices_excluding_vat_analysis(self) -> _PriceSeriesAnalysis:
        return _analyze_prices(self.market_prices_excluding_vat)

    @cached_property
    def market_prices_including_vat(self) -> dict[datetime, float]:
        """Return the market electricity prices including VAT."""
        return _series_from_intervals(self.intervals, price_key="priceIncVat")

    @cached_property
    def _market_prices_analysis(self) -> _PriceSeriesAnalysis:
        return _analyze_prices(self.market_prices)

    @property
    def market_prices(self) -> dict[datetime, float]:
        """Return the market electricity prices including VAT."""
        return self.market_prices_including_vat

    @cached_property
    def invoice_prices(self) -> dict[datetime, float]:
        """Return the billed electricity invoice prices."""
        return _series_from_intervals(self.intervals, price_key="invoicePrice")

    @cached_property
    def _invoice_prices_analysis(self) -> _PriceSeriesAnalysis:
        return _analyze_prices(self.invoice_prices)

    @property
    def return_prices(self) -> dict[datetime, float]:
        """Return the electricity return prices (VAT-inclusive)."""
        return self._return_prices

    @property
    def current_market_price_excluding_vat(self) -> float | None:
        """Return the market price without VAT for the current interval."""
        return _timed_value(
            datetime.now(UTC),
            self.market_prices_excluding_vat,
            self.price_ends,
            self._interval_starts,
        )

    @property
    def current_market_price(self) -> float | None:
        """Return the market price including VAT for the current interval."""
        return _timed_value(
            datetime.now(UTC),
            self.market_prices,
            self.price_ends,
            self._interval_starts,
        )

    @property
    def current_invoice_price(self) -> float | None:
        """Return the invoice price for the current interval."""
        return _timed_value(
            datetime.now(UTC),
            self.invoice_prices,
            self.price_ends,
            self._interval_starts,
        )

    @property
    def current_return_price(self) -> float | None:
        """Return the return price for the current interval."""
        return _timed_value(
            datetime.now(UTC),
            self.return_prices,
            self.price_ends,
            self._interval_starts,
        )

    @property
    def extreme_return_prices(self) -> tuple[float, float]:
        """Return the minimum and maximum return price."""
        return self._return_analysis.extreme_prices

    @property
    def average_return_price(self) -> float:
        """Return the average return price."""
        return self._return_analysis.average_price

    @property
    def highest_return_price_time(self) -> datetime:
        """Return the time of the highest return price."""
        return self._return_analysis.highest_price_time

    @property
    def lowest_return_price_time(self) -> datetime:
        """Return the time of the lowest return price."""
        return self._return_analysis.lowest_price_time

    @property
    def pct_of_max(self) -> float:
        """Return the current price as percentage of maximum."""
        current = self.current_price or 0
        return round(current / self.extreme_prices[1] * 100, 2)

    @property
    def pct_of_max_return(self) -> float:
        """Return the current return price as percentage of maximum."""
        current = self.current_return_price or 0
        return round(current / self.extreme_return_prices[1] * 100, 2)

    def return_price_at_time(self, moment: datetime) -> float | None:
        """Return the return price at a specific time."""
        return _timed_value(
            moment, self.return_prices, self.price_ends, self._interval_starts
        )

    @property
    def timestamp_market_prices_excluding_vat(
        self,
    ) -> list[dict[str, float | datetime]]:
        """Return timestamps and market prices without VAT."""
        return self._market_prices_excluding_vat_analysis.timestamp_prices

    @property
    def timestamp_market_prices(self) -> list[dict[str, float | datetime]]:
        """Return timestamps and market prices including VAT."""
        return self._market_prices_analysis.timestamp_prices

    @property
    def timestamp_invoice_prices(self) -> list[dict[str, float | datetime]]:
        """Return timestamps and invoice prices."""
        return self._invoice_prices_analysis.timestamp_prices

    @property
    def timestamp_return_prices(self) -> list[dict[str, float | datetime]]:
        """Return timestamps and return prices."""
        return self._return_analysis.timestamp_prices

    @property
    def periods_priced_equal_or_lower(self) -> int:
        """Return the number of intervals with the current price or lower."""
        current: float = self.current_price or 0
        return self._price_analysis.count_equal_or_lower(current)

    @property
    def periods_priced_equal_or_higher(self) -> int:
        """Return the number of intervals with the current price or higher."""
        current: float = self.current_price or 0
        return self._price_analysis.count_equal_or_higher(current)

    @property
    def return_periods_priced_equal_or_higher(self) -> int:
        """Return the number of intervals with the current return price or higher."""
        current: float = self.current_return_price or 0
        return self._return_analysis.count_equal_or_higher(current)

    @classmethod
    def from_dict(
        cls,
        data: list[dict[str, Any]],
        *,
        price_key: str,
        return_price_key: str | None = None,
    ) -> Self:
        """Create an Electricity object from API data."""
        intervals, prices, price_ends = _parse_price_data(data, price_key=price_key)
        return_prices = prices
        if return_price_key is not None:
            return_prices = {
                interval.starts_at: interval.value_for(return_price_key)
                for interval in intervals
            }
        return cls(
            intervals=intervals,
            prices=prices,
            _return_prices=return_prices,
            price_ends=price_ends,
        )


@dataclass
class Gas(EnergyPrices):
    """Object representing gas data."""

    @classmethod
    def from_dict(
        cls,
        data: list[dict[str, Any]],
        *,
        price_key: str,
    ) -> Self:
        """Create a Gas object from API data."""
        intervals, prices, price_ends = _parse_price_data(data, price_key=price_key)
        return cls(intervals=intervals, prices=prices, price_ends=price_ends)

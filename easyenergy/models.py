"""Data models for the easyEnergy API."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable


def _timed_value(moment: datetime, prices: dict[datetime, float]) -> float | None:
    """Return a function that returns a value at a specific time.

    Args:
        moment: The time to get the value for.
        prices: A dictionary with market prices.

    Returns:
        The value at the specific time.
    """
    value = None
    for timestamp, price in prices.items():
        if timestamp <= moment < (timestamp + timedelta(hours=1)):
            value = round(price, 5)
    return value


def _get_pricetime(
    prices: dict[datetime, float], func: Callable[[dict[datetime, float]], datetime]
) -> datetime:
    """Return the time of the price.

    Args:
        prices: A dictionary with market prices.
        func: A function to get the time.

    Returns:
        The time of the price.
    """
    return func(prices, key=prices.get)  # type: ignore


@dataclass
class Electricity:
    """Object representing electricity data."""

    usage_prices: dict[datetime, float]
    return_prices: dict[datetime, float]

    @property
    def current_usage_price(self) -> float | None:
        """Return the price for the current hour.

        Returns:
            The price for the current hour.
        """
        return self.price_at_time(self.utcnow())

    @property
    def current_return_price(self) -> float | None:
        """Return the price for the current hour.

        Returns:
            The price for the current hour.
        """
        return self.price_at_time(self.utcnow(), data_type="return")

    @property
    def extreme_usage_prices(self) -> tuple[float, float]:
        """Return the minimum and maximum price for usage.

        Returns:
            The minimum and maximum price for usage.
        """
        return round(min(self.usage_prices.values()), 5), round(
            max(self.usage_prices.values()), 5
        )

    @property
    def extreme_return_prices(self) -> tuple[float, float]:
        """Return the minimum and maximum price for return.

        Returns:
            The minimum and maximum price for return.
        """
        return round(min(self.return_prices.values()), 5), round(
            max(self.return_prices.values()), 5
        )

    @property
    def average_usage_price(self) -> float:
        """Return the average price for usage.

        Returns:
            The average price for usage.
        """
        return round(sum(self.usage_prices.values()) / len(self.usage_prices), 5)

    @property
    def average_return_price(self) -> float:
        """Return the average price for return.

        Returns:
            The average price for return.
        """
        return round(sum(self.return_prices.values()) / len(self.return_prices), 5)

    @property
    def highest_usage_price_time(self) -> datetime:
        """Return the time of the highest price for usage.

        Returns:
            The time of the highest price for usage.
        """
        return _get_pricetime(self.usage_prices, max)

    @property
    def highest_return_price_time(self) -> datetime:
        """Return the time of the highest price for return.

        Returns:
            The time of the highest price for return.
        """
        return _get_pricetime(self.return_prices, max)

    @property
    def lowest_usage_price_time(self) -> datetime:
        """Return the time of the lowest price for usage.

        Returns:
            The time of the lowest price for usage.
        """
        return _get_pricetime(self.usage_prices, min)

    @property
    def lowest_return_price_time(self) -> datetime:
        """Return the time of the lowest price for return.

        Returns:
            The time of the lowest price for return.
        """
        return _get_pricetime(self.return_prices, min)

    @property
    def pct_of_max_usage(self) -> float:
        """Return the percentage of the current price for usage.

        Returns:
            The percentage of the current price for usage.
        """
        current = self.current_usage_price or 0
        return round(current / self.extreme_usage_prices[1] * 100, 2)

    @property
    def pct_of_max_return(self) -> float:
        """Return the percentage of the current price for return.

        Returns:
            The percentage of the current price for return.
        """
        current = self.current_return_price or 0
        return round(current / self.extreme_return_prices[1] * 100, 2)

    @property
    def timestamp_usage_prices(self) -> list[dict[str, float | datetime]]:
        """Return a dictionary with the prices for usage.

        Returns:
            A dictionary with the prices for usage.
        """
        return self.generate_timestamp_list(self.usage_prices)

    @property
    def timestamp_return_prices(self) -> list[dict[str, float | datetime]]:
        """Return a dictionary with the prices for return.

        Returns:
            A dictionary with the prices for return.
        """
        return self.generate_timestamp_list(self.return_prices)

    def utcnow(self) -> datetime:
        """Return the current timestamp in the UTC timezone.

        Returns:
            The current timestamp in the UTC timezone.
        """
        return datetime.now(timezone.utc)

    def generate_timestamp_list(
        self, prices: dict[datetime, float]
    ) -> list[dict[str, float | datetime]]:
        """Return a list of dictionaries with the prices and timestamps.

        Args:
            prices: A dictionary with the prices.

        Returns:
            A list of dictionaries with the prices and timestamps.
        """
        timestamp_prices: list[dict[str, float | datetime]] = []
        for timestamp, price in prices.items():
            timestamp_prices.append({"timestamp": timestamp, "price": round(price, 5)})
        return timestamp_prices

    def price_at_time(self, moment: datetime, data_type: str = "usage") -> float | None:
        """Return the price at a specific time.

        Args:
            moment: The time to get the price for.
            data_type: The type of data to get the price for.
                Can be "usage" (default) or "return".

        Returns:
            The price at the specified time.
        """
        # Set the correct data list
        if data_type == "return":
            data_list = self.return_prices
        else:
            data_list = self.usage_prices

        # Get the price at the specified time
        value = _timed_value(moment, data_list)
        if value is not None or value == 0:
            return value
        return None

    @classmethod
    def from_dict(cls, data: list[dict[str, Any]]) -> Electricity:
        """Create an Electricity object from a dictionary.

        Args:
            data: A dictionary with the data from the API.

        Returns:
            An Electricity object.
        """

        usage_prices: dict[datetime, float] = {}
        return_prices: dict[datetime, float] = {}
        for item in data:
            usage_prices[
                datetime.strptime(item["Timestamp"], "%Y-%m-%dT%H:%M:%S%z")
            ] = item["TariffUsage"]
            return_prices[
                datetime.strptime(item["Timestamp"], "%Y-%m-%dT%H:%M:%S%z")
            ] = item["TariffReturn"]
        return cls(
            usage_prices=usage_prices,
            return_prices=return_prices,
        )


@dataclass
class Gas:
    """Object representing gas data."""

    prices: dict[datetime, float]

    @property
    def current_price(self) -> float | None:
        """Return the current gas price.

        Returns:
            The current gas price.
        """
        return self.price_at_time(self.utcnow())

    @property
    def extreme_prices(self) -> tuple[float, float]:
        """Return the minimum and maximum price for gas.

        Returns:
            The minimum and maximum price for gas.
        """
        return round(min(self.prices.values()), 5), round(max(self.prices.values()), 5)

    @property
    def average_price(self) -> float:
        """Return the average price for gas.

        Returns:
            The average price for gas.
        """
        return round(sum(self.prices.values()) / len(self.prices), 5)

    def utcnow(self) -> datetime:
        """Return the current timestamp in the UTC timezone.

        Returns:
            The current timestamp in the UTC timezone.
        """
        return datetime.now(timezone.utc)

    def price_at_time(self, moment: datetime) -> float | None:
        """Return the price at a specific time.

        Args:
            moment: The time to get the price for.

        Returns:
            The price at the specified time.
        """
        value = _timed_value(moment, self.prices)
        if value is not None or value == 0:
            return value
        return None

    @classmethod
    def from_dict(cls, data: list[dict[str, Any]]) -> Gas:
        """Create a Gas object from a dictionary.

        Args:
            data: A dictionary with the data from the API.

        Returns:
            A Gas object.
        """

        prices: dict[datetime, float] = {}
        for item in data:
            prices[datetime.strptime(item["Timestamp"], "%Y-%m-%dT%H:%M:%S%z")] = item[
                "TariffUsage"
            ]

        return cls(
            prices=prices,
        )

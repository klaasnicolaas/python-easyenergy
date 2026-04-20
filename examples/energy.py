"""Asynchronous Python client for the easyEnergy API."""

import asyncio
from datetime import date
from zoneinfo import ZoneInfo

from easyenergy import (
    EasyEnergy,
    ElectricityGranularity,
    VatOption,
)

LOCAL_TIMEZONE = ZoneInfo("Europe/Amsterdam")
REQUEST_DAY = date(2026, 4, 19)


async def main() -> None:
    """Show example on fetching the energy prices from easyEnergy."""
    async with EasyEnergy(vat=VatOption.INCLUDE) as client:
        energy_hour = await client.energy_prices(
            start_date=REQUEST_DAY,
            end_date=REQUEST_DAY,
            granularity=ElectricityGranularity.HOUR,
        )
        energy_quarter = await client.energy_prices(
            start_date=REQUEST_DAY,
            end_date=REQUEST_DAY,
            granularity=ElectricityGranularity.QUARTER,
        )

    print("--- ENERGY / HOUR ---")
    print(f"Requested day: {REQUEST_DAY.isoformat()}")
    print(f"Current market price: {energy_hour.current_market_price}")
    print(f"Current invoice price: {energy_hour.current_invoice_price}")
    print(f"Average price: {energy_hour.average_price}")
    print(f"Average return price: {energy_hour.average_return_price}")
    print(f"Extreme prices: {energy_hour.extreme_prices}")
    print(f"Extreme return prices: {energy_hour.extreme_return_prices}")
    print(
        "Lowest price time: "
        f"{energy_hour.lowest_price_time.astimezone(LOCAL_TIMEZONE)}",
    )
    print(
        "Highest price time: "
        f"{energy_hour.highest_price_time.astimezone(LOCAL_TIMEZONE)}",
    )
    print()
    print("--- ENERGY / QUARTER ---")
    print(f"Returned intervals: {len(energy_quarter.intervals)}")
    print(f"First interval: {energy_quarter.intervals[0]}")
    print(f"First usage row: {energy_quarter.timestamp_prices[0]}")
    print(f"First return row: {energy_quarter.timestamp_return_prices[0]}")


if __name__ == "__main__":
    asyncio.run(main())

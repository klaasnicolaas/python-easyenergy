"""Asynchronous Python client for the easyEnergy API."""

import asyncio
from datetime import date

from easyenergy import EasyEnergy, VatOption

START_DAY = date(2026, 4, 1)
END_DAY = date(2026, 4, 2)


async def main() -> None:
    """Show example on fetching the gas prices from easyEnergy."""
    async with EasyEnergy(vat=VatOption.INCLUDE) as client:
        gas_prices = await client.gas_prices(start_date=START_DAY, end_date=END_DAY)

    print("--- GAS ---")
    print(f"Requested period: {START_DAY.isoformat()} -> {END_DAY.isoformat()}")
    print(f"Average price: {gas_prices.average_price}")
    print(f"Extremas prices: {gas_prices.extreme_prices}")
    print(f"First interval: {gas_prices.intervals[0]}")
    print(f"Timestamp rows: {gas_prices.timestamp_prices}")


if __name__ == "__main__":
    asyncio.run(main())

"""Asynchronous Python client for the easyEnergy API."""

import asyncio
from datetime import datetime, timedelta

from easyenergy import EasyEnergy


async def main() -> None:
    """Show example on fetching the gas prices from easyEnergy."""
    async with EasyEnergy() as client:
        today = datetime.strptime("2022-12-14", "%Y-%m-%d")

        gas_today = await client.gas_prices(start_date=today, end_date=today)
        next_hour = gas_today.utcnow() + timedelta(hours=1)

        print("--- GAS TODAY ---")
        print(f"Extremas prices: {gas_today.extreme_prices}")
        print(f"Average price: {gas_today.average_price}")
        print()
        print(f"Current hourprice: {gas_today.current_price}")
        print(f"Next hourprice: {gas_today.price_at_time(next_hour)}")


if __name__ == "__main__":
    asyncio.run(main())

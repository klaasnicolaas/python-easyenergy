"""Asynchronous Python client for the easyEnergy API."""

import asyncio
from datetime import date

from easyenergy import EasyEnergy, VatOption


async def main() -> None:
    """Show example on fetching the timestamp lists from easyEnergy."""
    async with EasyEnergy(vat=VatOption.INCLUDE) as client:
        today = date(2023, 12, 5)
        energy = await client.energy_prices(start_date=today, end_date=today)
        gas = await client.gas_prices(start_date=today, end_date=today)

        print("--- ENERGY / Usage ---")
        print(energy.timestamp_usage_prices)
        print()

        print("--- ENERGY / Return ---")
        print(energy.timestamp_return_prices)
        print()

        print("--- GAS ---")
        print(gas.timestamp_prices)


if __name__ == "__main__":
    asyncio.run(main())

"""Asynchronous Python client for the easyEnergy API."""

import asyncio
from datetime import date

from easyenergy import EasyEnergy, ElectricityGranularity, VatOption

REQUEST_DAY = date(2026, 4, 19)


async def main() -> None:
    """Show example on fetching the timestamp lists from easyEnergy."""
    async with EasyEnergy(vat=VatOption.INCLUDE) as client:
        energy = await client.energy_prices(
            start_date=REQUEST_DAY,
            end_date=REQUEST_DAY,
            granularity=ElectricityGranularity.QUARTER,
        )
        gas = await client.gas_prices(start_date=REQUEST_DAY, end_date=REQUEST_DAY)

        print("--- ENERGY / Usage ---")
        print(energy.timestamp_prices)
        print()

        print("--- ENERGY / Return ---")
        print(energy.timestamp_return_prices)
        print()

        print("--- GAS ---")
        print(gas.timestamp_prices)


if __name__ == "__main__":
    asyncio.run(main())

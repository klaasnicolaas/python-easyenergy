"""Asynchronous Python client for the easyEnergy API."""

import asyncio
from datetime import datetime, timedelta

import pytz

from easyenergy import EasyEnergy


async def main() -> None:
    """Show example on fetching the energy prices from easyEnergy."""
    async with EasyEnergy() as client:
        local = pytz.timezone("Europe/Amsterdam")
        today = datetime.strptime("2022-12-14", "%Y-%m-%d")
        tomorrow = datetime.strptime("2022-12-14", "%Y-%m-%d")

        # Select your test readings
        energy_reading: bool = True
        gas_reading: bool = True

        if energy_reading:
            energy_today = await client.energy_prices(start_date=today, end_date=today)
            energy_tomorrow = await client.energy_prices(
                start_date=tomorrow, end_date=tomorrow
            )
            next_hour = energy_today.utcnow() + timedelta(hours=1)

            print("--- ENERGY TODAY ---")
            print(f"Extremas usage price: {energy_today.extreme_usage_prices}")
            print(f"Extremas return price: {energy_today.extreme_return_prices}")
            print(f"Average usage price: {energy_today.average_usage_price}")
            print(f"Average return price: {energy_today.average_return_price}")
            print(f"Percentage max - Usage: {energy_today.pct_of_max_usage}%")
            print(f"Percentage max - Return: {energy_today.pct_of_max_return}%")
            print()
            highest_time_usage = energy_today.highest_usage_price_time.astimezone(local)
            print(f"Highest price time - Usage: {highest_time_usage}")
            lowest_time_usage = energy_today.lowest_usage_price_time.astimezone(local)
            print(f"Lowest price time - Usage: {lowest_time_usage}")
            print()
            print(f"Current usage price: {energy_today.current_usage_price}")
            print(f"Current return price: {energy_today.current_return_price}")
            print(f"Next hourprice: {energy_today.price_at_time(next_hour)}")

            print()
            print("--- ENERGY TOMORROW ---")
            print(f"Extremas usage price: {energy_tomorrow.extreme_usage_prices}")
            print(f"Extremas return price: {energy_tomorrow.extreme_return_prices}")
            print(f"Average usage price: {energy_tomorrow.average_usage_price}")
            print(f"Average return price: {energy_tomorrow.average_return_price}")
            print()
            highest_time = energy_tomorrow.highest_usage_price_time.astimezone(local)
            print(f"Highest price time - Usage: {highest_time}")
            lowest_time = energy_tomorrow.lowest_usage_price_time.astimezone(local)
            print(f"Lowest price time - Usage: {lowest_time}")

        if gas_reading:
            gas_today = await client.gas_prices(start_date=today, end_date=today)
            print()
            print("--- GAS TODAY ---")
            print(f"Extremas prices: {gas_today.extreme_prices}")
            print(f"Average price: {gas_today.average_price}")
            print()
            print(f"Current hourprice: {gas_today.current_price}")
            next_hour_gas = gas_today.utcnow() + timedelta(hours=1)
            print(f"Next hourprice: {gas_today.price_at_time(next_hour_gas)}")


if __name__ == "__main__":
    asyncio.run(main())

<!-- Header -->
![alt Header of the easyEnergy package](https://raw.githubusercontent.com/klaasnicolaas/python-easyenergy/main/assets/header_easyenergy-min.png)

<!-- PROJECT SHIELDS -->
[![GitHub Release][releases-shield]][releases]
[![Python Versions][python-versions-shield]][pypi]
![Project Stage][project-stage-shield]
![Project Maintenance][maintenance-shield]
[![License][license-shield]](LICENSE)

[![GitHub Activity][commits-shield]][commits-url]
[![PyPi Downloads][downloads-shield]][downloads-url]
[![GitHub Last Commit][last-commit-shield]][commits-url]
[![Open in Dev Containers][devcontainer-shield]][devcontainer]

[![Build Status][build-shield]][build-url]
[![Typing Status][typing-shield]][typing-url]
[![Code Coverage][codecov-shield]][codecov-url]

Asynchronous Python client for the easyEnergy price API.

## About

A Python package for retrieving dynamic electricity and gas prices from [easyEnergy][easyenergy]. The package uses the current price-graph API and supports both hourly and quarter-hour electricity prices.

## Installation

```bash
pip install easyenergy
```

To use the CLI as well:

```bash
pip install "easyenergy[cli]"
```

## Data

> [!NOTE]
> The bundled example scripts are plain Python usage examples. They intentionally use fixed request dates so you can test a known day; adjust those dates when you want to inspect another period.

You can read the following datasets with this package:

### Electricity prices

> [!IMPORTANT]
> The new easyEnergy price API exposes multiple electricity price components per interval. For electricity usage you can select either the market price (`price` / `priceIncVat`) or the billed invoice price (`invoicePrice`). Return to grid is mapped to the VAT-inclusive return price field (`priceIncVat`).

> [!TIP]
> A single `energy_prices(...)` fetch exposes both `current_market_price` and `current_invoice_price`, plus `market_prices` and `invoice_prices`. That makes it straightforward to create separate Home Assistant price entities for the Energy dashboard without extra API calls.

Electricity prices can be requested per hour or per quarter. This package defaults to hourly data for backwards compatibility, but quarter prices are also supported through `ElectricityGranularity.QUARTER`.

**Usage properties:**

| Property | Type | Description |
| :------- | :--- | :---------- |
| `current_price` | float | Current usage price for the active interval |
| `current_market_price` | float | Current market price (including VAT) |
| `current_market_price_excluding_vat` | float | Current market price (excluding VAT) |
| `current_invoice_price` | float | Current invoice/billed price |
| `average_price` | float | Average price over all intervals |
| `extreme_prices` | tuple | Minimum and maximum price (min, max) |
| `highest_price_time` | datetime | Timestamp of the highest price |
| `lowest_price_time` | datetime | Timestamp of the lowest price |
| `pct_of_max` | float | Current price as percentage of maximum |
| `periods_priced_equal_or_lower` | int | Number of intervals with current price or lower |
| `periods_priced_equal_or_higher` | int | Number of intervals with current price or higher |
| `prices` | dict | Usage price series (datetime → price) |
| `market_prices` | dict | Market prices including VAT |
| `market_prices_excluding_vat` | dict | Market prices excluding VAT |
| `invoice_prices` | dict | Invoice/billed prices |

**Return properties:**

| Property | Type | Description |
| :------- | :--- | :---------- |
| `current_return_price` | float | Current return/feed-in price |
| `average_return_price` | float | Average return price |
| `extreme_return_prices` | tuple | Minimum and maximum return price |
| `highest_return_price_time` | datetime | Timestamp of highest return price |
| `lowest_return_price_time` | datetime | Timestamp of lowest return price |
| `pct_of_max_return` | float | Current return as percentage of maximum |
| `return_periods_priced_equal_or_higher` | int | Return intervals with current price or higher |
| `return_prices` | dict | Return price series (datetime → price) |

**Interval data:**

Full interval rows via `energy.intervals`, each containing: `price`, `price_inc_vat`, `energy_tax`, `purchase_price`, `invoice_price`, `average`, `average_inc`, `unit`, and `granularity`.

### Gas prices

The gas prices are fixed per day in the new price API.

| Property | Type | Description |
| :------- | :--- | :---------- |
| `current_price` | float | Current gas price |
| `average_price` | float | Average gas price |
| `extreme_prices` | tuple | Minimum and maximum price (min, max) |
| `highest_price_time` | datetime | Timestamp of the highest price |
| `lowest_price_time` | datetime | Timestamp of the lowest price |
| `prices` | dict | Gas price series (datetime → price) |

Full interval rows available via `gas.intervals`.

## Example

```python
import asyncio

from datetime import date
from easyenergy import (
    EasyEnergy,
    ElectricityGranularity,
    VatOption,
)


async def main() -> None:
    """Fetch electricity and gas prices from easyEnergy."""
    async with EasyEnergy(vat=VatOption.INCLUDE) as client:
        start_date = date(2026, 4, 19)
        end_date = date(2026, 4, 19)

        energy = await client.energy_prices(
            start_date,
            end_date,
            granularity=ElectricityGranularity.QUARTER,
        )
        gas = await client.gas_prices(start_date, end_date)

    print(f"Quarter intervals: {len(energy.intervals)}")
    print(f"Current market price: {energy.current_market_price}")
    print(f"Current invoice price: {energy.current_invoice_price}")
    print(f"Average price: {energy.average_price}")
    print(f"Average return price: {energy.average_return_price}")
    print(f"First electricity interval: {energy.intervals[0]}")
    print(f"Average gas price: {gas.average_price}")
    print(f"First gas interval: {gas.intervals[0]}")


if __name__ == "__main__":
    asyncio.run(main())
```

### Examples

The repository ships plain usage examples under [`examples/`](examples):

```bash
poetry run python ./examples/energy.py
poetry run python ./examples/gas.py
poetry run python ./examples/prices_list.py
```

Those files are intentionally simple and meant as package-usage references, not as a full CLI. Update the fixed request date constants in the files when you want to inspect another day.

### CLI Tool

The package also ships a Rich/Typer-based CLI under [`src/easyenergy/cli`](src/easyenergy/cli):

```bash
poetry run easyenergy energy --date 2026-04-19
poetry run easyenergy energy --date 2026-04-19 --price-type invoice
poetry run easyenergy gas --start-date 2026-04-01 --end-date 2026-04-02
poetry run easyenergy prices-list --date 2026-04-19 --granularity quarter
poetry run easyenergy entities --date 2026-04-19
```

The `entities` command shows all available properties for Home Assistant integration, grouped by usage, return, and gas.

Useful CLI options:

- `--date YYYY-MM-DD` for a single day
- `--start-date YYYY-MM-DD --end-date YYYY-MM-DD` for a range
- `--vat include|exclude` to switch between market prices with or without VAT
- `--price-type market|invoice` to choose between market and billed electricity usage prices
- `--granularity hour|quarter` for electricity commands
- `--limit N` to limit the number of printed intervals; without it, all returned intervals are shown

### Class Parameters

| Parameter | value Type | Description |
| :-------- | :--------- | :---------- |
| `vat` | enum (default: **VatOption.INCLUDE**) | Include or exclude VAT on class level |

### Function Parameters

| Parameter | value Type | Description |
| :-------- | :--------- | :---------- |
| `start_date` | date | The start date of the selected period |
| `end_date` | date | The end date of the selected period |
| `vat` | enum (default: class value) | Include or exclude VAT (**VatOption.INCLUDE** or **VatOption.EXCLUDE**) |
| `granularity` | enum (electricity only) | Electricity granularity (**ElectricityGranularity.HOUR** or **ElectricityGranularity.QUARTER**) |

## Contributing

This is an active open-source project. We are always open to people who want to
use the code or contribute to it.

We've set up a separate document for our
[contribution guidelines](CONTRIBUTING.md).

Thank you for being involved! :heart_eyes:

## Setting up development environment

The simplest way to begin is by utilizing the [Dev Container][devcontainer]
feature of Visual Studio Code or by opening a CodeSpace directly on GitHub.
By clicking the button below you immediately start a Dev Container in Visual Studio Code.

[![Open in Dev Containers][devcontainer-shield]][devcontainer]

This Python project relies on [Poetry][poetry] as its dependency manager,
providing comprehensive management and control over project dependencies.

You need at least:

- Python 3.12+
- [Poetry][poetry-install]

### Installation

Install all packages, including all development requirements:

```bash
poetry install
```

_Poetry creates by default an virtual environment where it installs all
necessary pip packages_.

### Prek

This repository uses the [prek][prek] framework, all changes
are linted and tested with each commit. To setup the prek check, run:

```bash
poetry run prek install
```

And to run all checks and tests manually, use the following command:

```bash
poetry run prek run --all-files
```

### Testing

It uses [pytest](https://docs.pytest.org/en/stable/) as the test framework. To run the tests:

```bash
poetry run pytest
```

To update the [syrupy](https://github.com/tophat/syrupy) snapshot tests:

```bash
poetry run pytest --snapshot-update
```

## License

MIT License

Copyright (c) 2022-2026 Klaas Schoute

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

[easyenergy]: https://www.easyenergy.com

<!-- MARKDOWN LINKS & IMAGES -->
[build-shield]: https://github.com/klaasnicolaas/python-easyenergy/actions/workflows/tests.yaml/badge.svg
[build-url]: https://github.com/klaasnicolaas/python-easyenergy/actions/workflows/tests.yaml
[commits-shield]: https://img.shields.io/github/commit-activity/y/klaasnicolaas/python-easyenergy.svg
[commits-url]: https://github.com/klaasnicolaas/python-easyenergy/commits/main
[codecov-shield]: https://codecov.io/gh/klaasnicolaas/python-easyenergy/branch/main/graph/badge.svg?token=RYhiDUamT6
[codecov-url]: https://codecov.io/gh/klaasnicolaas/python-easyenergy
[devcontainer-shield]: https://img.shields.io/static/v1?label=Dev%20Containers&message=Open&color=blue&logo=visualstudiocode
[devcontainer]: https://vscode.dev/redirect?url=vscode://ms-vscode-remote.remote-containers/cloneInVolume?url=https://github.com/klaasnicolaas/python-easyenergy
[downloads-shield]: https://img.shields.io/pypi/dm/easyenergy
[downloads-url]: https://pypistats.org/packages/easyenergy
[license-shield]: https://img.shields.io/github/license/klaasnicolaas/python-easyenergy.svg
[last-commit-shield]: https://img.shields.io/github/last-commit/klaasnicolaas/python-easyenergy.svg
[maintenance-shield]: https://img.shields.io/maintenance/yes/2026.svg
[project-stage-shield]: https://img.shields.io/badge/project%20stage-production%20ready-brightgreen.svg
[pypi]: https://pypi.org/project/easyenergy/
[python-versions-shield]: https://img.shields.io/pypi/pyversions/easyenergy
[typing-shield]: https://github.com/klaasnicolaas/python-easyenergy/actions/workflows/typing.yaml/badge.svg
[typing-url]: https://github.com/klaasnicolaas/python-easyenergy/actions/workflows/typing.yaml
[releases-shield]: https://img.shields.io/github/release/klaasnicolaas/python-easyenergy.svg
[releases]: https://github.com/klaasnicolaas/python-easyenergy/releases

[poetry-install]: https://python-poetry.org/docs/#installation
[poetry]: https://python-poetry.org
[prek]: https://github.com/j178/prek

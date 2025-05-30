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

Asynchronous Python client for the easyEnergy API.

## About

A python package with which you can retrieve the dynamic energy/gas prices from [easyEnergy][easyenergy]. Third parties who purchase their energy via easyEnergy (as far as is known):

- [NieuweStroom](https://nieuwestroom.nl)

## Installation

```bash
pip install easyenergy
```

## Data

**note**: Currently only tested for day/tomorrow prices

You can read the following datasets with this package:

### Electricity prices

**note**: easyEnergy has separate prices for usage and return to grid, which also differ per hour.

The energy prices are different every hour, after 15:00 (more usually already at 14:00) the prices for the next day are published and it is therefore possible to retrieve these data.


- Current/Next[x] hour electricity market price (float)
- Lowest energy price (float)
- Highest energy price (float)
- Average electricity price (float)
- Time of highest price (datetime)
- Time of lowest price (datetime)
- Percentage of the current price compared to the maximum price
- Number of hours with the current price or better (int)

### Gas prices

The gas prices do not change per hour, but are fixed for 24 hours. Which means that from 06:00 in the morning the new rate for that day will be used.

- Current/Next[x] hour gas market price (float)
- Lowest gas price (float)
- Highest gas price (float)
- Average gas price (float)

## Example

```python
import asyncio

from datetime import date
from easyenergy import EasyEnergy, VatOption


async def main() -> None:
    """Show example on fetching the energy prices from easyEnergy."""
    async with EasyEnergy(vat=VatOption.INCLUDE) as client:
        start_date = date(2022, 12, 7)
        end_date = date(2022, 12, 7)

        energy = await client.energy_prices(start_date, end_date)
        gas = await client.gas_prices(start_date, end_date)


if __name__ == "__main__":
    asyncio.run(main())
```

### Class Parameters

| Parameter | value Type | Description |
| :-------- | :--------- | :---------- |
| `vat` | enum (default: **VatOption.INCLUDE**) | Include or exclude VAT on class level |

### Function Parameters

| Parameter | value Type | Description |
| :-------- | :--------- | :---------- |
| `start_date` | datetime | The start date of the selected period |
| `end_date` | datetime | The end date of the selected period |
| `vat` | enum (default: class value) | Include or exclude VAT (**VatOption.INCLUDE** or **VatOption.EXCLUDE**) |

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

- Python 3.11+
- [Poetry][poetry-install]

### Installation

Install all packages, including all development requirements:

```bash
poetry install
```

_Poetry creates by default an virtual environment where it installs all
necessary pip packages_.

### Pre-commit

This repository uses the [pre-commit][pre-commit] framework, all changes
are linted and tested with each commit. To setup the pre-commit check, run:

```bash
poetry run pre-commit install
```

And to run all checks and tests manually, use the following command:

```bash
poetry run pre-commit run --all-files
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

Copyright (c) 2022-2025 Klaas Schoute

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
[maintenance-shield]: https://img.shields.io/maintenance/yes/2025.svg
[project-stage-shield]: https://img.shields.io/badge/project%20stage-production%20ready-brightgreen.svg
[pypi]: https://pypi.org/project/easyenergy/
[python-versions-shield]: https://img.shields.io/pypi/pyversions/easyenergy
[typing-shield]: https://github.com/klaasnicolaas/python-easyenergy/actions/workflows/typing.yaml/badge.svg
[typing-url]: https://github.com/klaasnicolaas/python-easyenergy/actions/workflows/typing.yaml
[releases-shield]: https://img.shields.io/github/release/klaasnicolaas/python-easyenergy.svg
[releases]: https://github.com/klaasnicolaas/python-easyenergy/releases

[poetry-install]: https://python-poetry.org/docs/#installation
[poetry]: https://python-poetry.org
[pre-commit]: https://pre-commit.com

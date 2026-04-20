"""Constants for EasyEnergy API client."""

from __future__ import annotations

from enum import StrEnum
from typing import Final
from zoneinfo import ZoneInfo

API_HOST: Final = "price-graph.acc-mijn.easyenergy.com"
API_PATH: Final = "/api/"
MARKET_TIMEZONE: Final = ZoneInfo("Europe/Amsterdam")


class VatOption(StrEnum):
    """Enum representing whether to include VAT or not."""

    INCLUDE = "true"
    EXCLUDE = "false"


class ElectricityGranularity(StrEnum):
    """Enum representing the supported electricity granularities."""

    HOUR = "hour"
    QUARTER = "quarter"


class ElectricityPriceType(StrEnum):
    """Enum representing the supported electricity usage price types."""

    MARKET = "market"
    INVOICE = "invoice"

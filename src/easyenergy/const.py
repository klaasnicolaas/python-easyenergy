"""Constants for EasyEnergy API client."""

from __future__ import annotations

from enum import Enum
from typing import Final

API_HOST: Final = "mijn.easyenergy.com"


class VatOption(str, Enum):
    """Enum representing whether to include VAT or not."""

    INCLUDE = "true"
    EXCLUDE = "false"

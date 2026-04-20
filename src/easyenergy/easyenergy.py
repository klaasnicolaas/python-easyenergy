"""Asynchronous Python client for the easyEnergy API."""

from __future__ import annotations

import asyncio
import socket
from dataclasses import dataclass
from datetime import date, timedelta
from importlib import metadata
from typing import Any, Self

from aiohttp.client import ClientError, ClientSession
from aiohttp.hdrs import METH_GET
from yarl import URL

from .const import (
    API_HOST,
    API_PATH,
    ElectricityGranularity,
    VatOption,
)
from .exceptions import (
    EasyEnergyConnectionError,
    EasyEnergyError,
    EasyEnergyNoDataError,
)
from .models import Electricity, Gas

VERSION: str = metadata.version(__package__)  # ty:ignore[invalid-argument-type]


@dataclass
class EasyEnergy:
    """Main class for handling data fetching from easyEnergy."""

    vat: VatOption = VatOption.INCLUDE
    request_timeout: float = 10.0
    session: ClientSession | None = None

    _close_session: bool = False
    _base_url = URL.build(scheme="https", host=API_HOST, path=API_PATH)

    async def _request(
        self,
        uri: str,
        *,
        method: str = METH_GET,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """Handle a request to the API of easyEnergy.

        Args:
        ----
            uri: Request URI, without '/', for example, 'status'
            method: HTTP method to use, for example, 'GET'
            params: Extra options to improve or limit the response.

        Returns:
        -------
            A Python dictionary (json) with the response from easyEnergy.

        Raises:
        ------
            EasyEnergyConnectionError: An error occurred while
                communicating with the API.
            EasyEnergyError: Received an unexpected response from
                the API.

        """
        url = self._base_url.join(URL(uri))

        headers = {
            "Accept": "application/json",
            "User-Agent": f"PythonEasyEnergy/{VERSION}",
        }

        if self.session is None:
            self.session = ClientSession()
            self._close_session = True

        try:
            async with asyncio.timeout(self.request_timeout):
                response = await self.session.request(
                    method,
                    url,
                    params=params,
                    headers=headers,
                )
                response.raise_for_status()
        except TimeoutError as exception:
            msg = "Timeout occurred while connecting to the API."
            raise EasyEnergyConnectionError(msg) from exception
        except (ClientError, socket.gaierror) as exception:
            msg = "Error occurred while communicating with the API."
            raise EasyEnergyConnectionError(msg) from exception

        content_type = response.headers.get("Content-Type", "")
        if "application/json" not in content_type:
            text = await response.text()
            msg = "Unexpected content type response from the easyEnergy API"
            raise EasyEnergyError(
                msg,
                {"Content-Type": content_type, "response": text},
            )

        return await response.json()

    def _price_key(self, vat: VatOption | None) -> str:
        """Return the response field matching the VAT preference."""
        vat_option = vat if vat is not None else self.vat
        return "priceIncVat" if vat_option == VatOption.INCLUDE else "price"

    async def _prices(
        self,
        *,
        start_date: date,
        end_date: date,
        commodity_type: str,
        granularity: str,
    ) -> list[dict[str, Any]]:
        """Fetch prices from the new price graph API."""
        data = await self._request(
            "prices",
            params={
                "start": start_date.isoformat(),
                "end": (end_date + timedelta(days=1)).isoformat(),
                "type": commodity_type,
                "granularity": granularity,
            },
        )

        if not isinstance(data, dict) or not isinstance(data.get("prices"), list):
            msg = "Unexpected response structure from the easyEnergy API"
            raise EasyEnergyError(msg, data)
        return data["prices"]

    async def gas_prices(
        self,
        start_date: date,
        end_date: date,
        vat: VatOption | None = None,
    ) -> Gas:
        """Get gas prices for a given period.

        Args:
        ----
            start_date: Start date of the period.
            end_date: End date of the period.
            vat: Include or exclude VAT from the prices.

        Returns:
        -------
            A Python dictionary with the response from easyEnergy.

        Raises:
        ------
            EasyEnergyNoDataError: No gas prices found for this period.

        """
        data = await self._prices(
            start_date=start_date,
            end_date=end_date,
            commodity_type="gas",
            granularity="day",
        )

        if len(data) == 0:
            msg = "No gas prices found for this period."
            raise EasyEnergyNoDataError(msg)
        return Gas.from_dict(data, price_key=self._price_key(vat))

    async def energy_prices(
        self,
        start_date: date,
        end_date: date,
        vat: VatOption | None = None,
        granularity: ElectricityGranularity = ElectricityGranularity.HOUR,
    ) -> Electricity:
        """Get energy prices for a given period.

        Args:
        ----
            start_date: Start date of the period.
            end_date: End date of the period.
            vat: Include or exclude VAT from the prices.
            granularity: The electricity price granularity to request.

        Returns:
        -------
            A Python dictionary with the response from easyEnergy.

        Raises:
        ------
            EasyEnergyNoDataError: No energy prices found for this period.

        """
        data = await self._prices(
            start_date=start_date,
            end_date=end_date,
            commodity_type="electricity",
            granularity=granularity.value,
        )

        if len(data) == 0:
            msg = "No energy prices found for this period."
            raise EasyEnergyNoDataError(msg)
        return Electricity.from_dict(
            data,
            price_key=self._price_key(vat),
            return_price_key="priceIncVat",
        )

    async def close(self) -> None:
        """Close open client session."""
        if self.session and self._close_session:
            await self.session.close()

    async def __aenter__(self) -> Self:
        """Async enter.

        Returns
        -------
            The EasyEnergy object.

        """
        return self

    async def __aexit__(self, *_exc_info: object) -> None:
        """Async exit.

        Args:
        ----
            _exc_info: Exec type.

        """
        await self.close()

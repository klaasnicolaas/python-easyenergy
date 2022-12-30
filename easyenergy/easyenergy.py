"""Asynchronous Python client for the easyEnergy API."""
from __future__ import annotations

import asyncio
import socket
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from importlib import metadata
from typing import Any

import aiohttp
import async_timeout
from aiohttp import hdrs
from yarl import URL

from .exceptions import (
    EasyEnergyConnectionError,
    EasyEnergyError,
    EasyEnergyNoDataError,
)
from .models import Electricity, Gas


@dataclass
class EasyEnergy:
    """Main class for handling data fetching from easyEnergy."""

    incl_vat: str = "true"
    request_timeout: float = 10.0
    session: aiohttp.client.ClientSession | None = None

    _close_session: bool = False

    async def _request(
        self,
        uri: str,
        *,
        method: str = hdrs.METH_GET,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """Handle a request to the API of easyEnergy.

        Args:
            uri: Request URI, without '/', for example, 'status'
            method: HTTP method to use, for example, 'GET'
            params: Extra options to improve or limit the response.

        Returns:
            A Python dictionary (json) with the response from easyEnergy.

        Raises:
            EasyEnergyConnectionError: An error occurred while
                communicating with the API.
            EasyEnergyError: Received an unexpected response from
                the API.
        """
        version = metadata.version(__package__)
        url = URL.build(
            scheme="https", host="mijn.easyenergy.com", path="/nl/api/tariff/"
        ).join(URL(uri))

        headers = {
            "Accept": "application/json, text/plain",
            "User-Agent": f"PythonEasyEnergy/{version}",
        }

        if self.session is None:
            self.session = aiohttp.ClientSession()
            self._close_session = True

        try:
            async with async_timeout.timeout(self.request_timeout):
                response = await self.session.request(
                    method,
                    url,
                    params=params,
                    headers=headers,
                    ssl=True,
                )
                response.raise_for_status()
        except asyncio.TimeoutError as exception:
            raise EasyEnergyConnectionError(
                "Timeout occurred while connecting to the API."
            ) from exception
        except (aiohttp.ClientError, socket.gaierror) as exception:
            raise EasyEnergyConnectionError(
                "Error occurred while communicating with the API."
            ) from exception

        content_type = response.headers.get("Content-Type", "")
        if "application/json" not in content_type:
            text = await response.text()
            raise EasyEnergyError(
                "Unexpected content type response from the easyEnergy API",
                {"Content-Type": content_type, "response": text},
            )

        return await response.json()

    async def gas_prices(self, start_date: date, end_date: date) -> Gas:
        """Get gas prices for a given period.

        Args:
            start_date: Start date of the period.
            end_date: End date of the period.

        Returns:
            A Python dictionary with the response from easyEnergy.

        Raises:
            EasyEnergyNoDataError: No gas prices found for this period.
        """
        start_date_utc: datetime
        end_date_utc: datetime
        utcnow: datetime = datetime.now(timezone.utc)
        if utcnow.hour >= 5 and utcnow.hour <= 22:
            # Set start_date to 05:00:00 and the end_date to 05:00:00 UTC next day
            start_date_utc = datetime(
                start_date.year, start_date.month, start_date.day, 5, 0, 0
            )
            end_date_utc = datetime(
                end_date.year, end_date.month, end_date.day, 5, 0, 0
            ) + timedelta(days=1)
        else:
            # Set start_date to 05:00:00 prev day and the end_date to 05:00:00 UTC
            start_date_utc = datetime(
                start_date.year, start_date.month, start_date.day, 5, 0, 0
            ) - timedelta(days=1)
            end_date_utc = datetime(
                end_date.year, end_date.month, end_date.day, 5, 0, 0
            )

        data = await self._request(
            "getlebatariffs",
            params={
                "startTimestamp": start_date_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                "endTimestamp": end_date_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                "includeVat": self.incl_vat.lower(),
            },
        )

        if len(data) == 0:
            raise EasyEnergyNoDataError("No gas prices found for this period.")
        return Gas.from_dict(data)

    async def energy_prices(self, start_date: date, end_date: date) -> Electricity:
        """Get energy prices for a given period.

        Args:
            start_date: Start date of the period.
            end_date: End date of the period.

        Returns:
            A Python dictionary with the response from easyEnergy.

        Raises:
            EasyEnergyNoDataError: No energy prices found for this period.
        """
        # Set the start date to 23:00:00 previous day and the end date to 23:00:00 UTC
        start_date_utc: datetime = datetime(
            start_date.year, start_date.month, start_date.day, 0, 0, 0
        ) - timedelta(hours=1)
        end_date_utc: datetime = datetime(
            end_date.year, end_date.month, end_date.day, 23, 0, 0
        )
        data = await self._request(
            "getapxtariffs",
            params={
                "startTimestamp": start_date_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                "endTimestamp": end_date_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                "includeVat": self.incl_vat.lower(),
            },
        )

        if len(data) == 0:
            raise EasyEnergyNoDataError("No energy prices found for this period.")
        return Electricity.from_dict(data)

    async def close(self) -> None:
        """Close open client session."""
        if self.session and self._close_session:
            await self.session.close()

    async def __aenter__(self) -> EasyEnergy:
        """Async enter.

        Returns:
            The EasyEnergy object.
        """
        return self

    async def __aexit__(self, *_exc_info: Any) -> None:
        """Async exit.

        Args:
            _exc_info: Exec type.
        """
        await self.close()

"""Asynchronous Python client for the easyEnergy API."""

from __future__ import annotations

import asyncio
import socket
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from importlib import metadata
from typing import Any, Self, cast

from aiodns import DNSResolver
from aiodns.error import DNSError
from aiohttp.client import ClientError, ClientSession
from aiohttp.hdrs import METH_GET
from yarl import URL

from .const import API_HOST, VatOption
from .exceptions import (
    EasyEnergyConnectionError,
    EasyEnergyError,
    EasyEnergyNoDataError,
)
from .models import Electricity, Gas

VERSION = metadata.version(__package__)


@dataclass
class EasyEnergy:
    """Main class for handling data fetching from easyEnergy."""

    vat: VatOption = VatOption.INCLUDE
    request_timeout: float = 10.0
    session: ClientSession | None = None

    _close_session: bool = False

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
        # EasyEnergy is experiencing IPv6 connection issues.
        # DNS returns an AAAA record with an IPv6 address, but
        # there doesn't appear to be something listening at that.
        # Workaround is to resolve the IPv4 address and use that.
        dns = DNSResolver()
        try:
            result = await dns.query(API_HOST, "A")
        except DNSError as err:
            msg = "Error while resolving EasyEnergy API IPv4 address"
            raise EasyEnergyConnectionError(msg) from err

        if not result:
            msg = "Could not resolve EasyEnergy IPv4 address"
            raise EasyEnergyConnectionError(msg)

        url = URL.build(
            scheme="https",
            host=result[0].host,
            path="/nl/api/tariff/",
        ).join(URL(uri))

        headers = {
            "Accept": "application/json, text/plain",
            "User-Agent": f"PythonEasyEnergy/{VERSION}",
            "Host": API_HOST,
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
                    ssl=False,
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

        return cast(dict[str, Any], await response.json())

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
        local_tz = datetime.now(UTC).astimezone().tzinfo
        now: datetime = datetime.now(tz=local_tz)

        if now.hour >= 6 and now.hour <= 23:
            # Set start_date to 06:00:00 and the end_date to 06:00:00 next day
            # Convert to UTC time 04:00:00 and 04:00:00 next day
            utc_start_date = datetime(
                start_date.year,
                start_date.month,
                start_date.day,
                6,
                0,
                0,
                tzinfo=local_tz,
            ).astimezone(UTC)
            utc_end_date = datetime(
                end_date.year,
                end_date.month,
                end_date.day,
                6,
                0,
                0,
                tzinfo=local_tz,
            ).astimezone(UTC) + timedelta(days=1)
        else:
            # Set start_date to 06:00:00 prev day and the end_date to 06:00:00
            # Convert to UTC time 04:00:00 prev day and 04:00:00 current day
            utc_start_date = datetime(
                start_date.year,
                start_date.month,
                start_date.day,
                6,
                0,
                0,
                tzinfo=local_tz,
            ).astimezone(UTC) - timedelta(days=1)
            utc_end_date = datetime(
                end_date.year,
                end_date.month,
                end_date.day,
                6,
                0,
                0,
                tzinfo=local_tz,
            ).astimezone(UTC)
        data = await self._request(
            "getlebatariffs",
            params={
                "startTimestamp": utc_start_date.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                "endTimestamp": utc_end_date.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                "includeVat": vat.value if vat is not None else self.vat.value,
            },
        )

        if len(data) == 0:
            msg = "No gas prices found for this period."
            raise EasyEnergyNoDataError(msg)
        return Gas.from_dict(data)

    async def energy_prices(
        self,
        start_date: date,
        end_date: date,
        vat: VatOption | None = None,
    ) -> Electricity:
        """Get energy prices for a given period.

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
            EasyEnergyNoDataError: No energy prices found for this period.

        """
        local_tz = datetime.now(UTC).astimezone().tzinfo
        # Set start_date to 00:00:00 and the end_date to 00:00:00 and convert to UTC
        utc_start_date: datetime = datetime(
            start_date.year,
            start_date.month,
            start_date.day,
            0,
            0,
            0,
            tzinfo=local_tz,
        ).astimezone(UTC)
        utc_end_date: datetime = datetime(
            end_date.year,
            end_date.month,
            end_date.day,
            0,
            0,
            0,
            tzinfo=local_tz,
        ).astimezone(UTC) + timedelta(days=1)
        data = await self._request(
            "getapxtariffs",
            params={
                "startTimestamp": utc_start_date.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                "endTimestamp": utc_end_date.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                "includeVat": vat.value if vat is not None else self.vat.value,
            },
        )

        if len(data) == 0:
            msg = "No energy prices found for this period."
            raise EasyEnergyNoDataError(msg)
        return Electricity.from_dict(data)

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

from __future__ import annotations

from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import AuraApi, AuraApiError
from .const import DOMAIN


class AuraCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.api = AuraApi(
            async_get_clientsession(hass),
            entry.data["email"],
            entry.data["password"],
        )
        self.entry = entry
        super().__init__(
            hass,
            logger=hass.logger,
            name=DOMAIN,
            update_interval=timedelta(minutes=5),
        )

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        try:
            await self.api.login()
            frames = await self.api.frames()
            data: dict[str, dict[str, Any]] = {}
            for frame in frames:
                frame_id = frame["id"]
                assets = await self.api.assets(frame_id)
                frame["recent_assets"] = assets
                data[frame_id] = frame
            return data
        except AuraApiError as err:
            raise UpdateFailed(str(err)) from err

    async def async_close(self) -> None:
        return None


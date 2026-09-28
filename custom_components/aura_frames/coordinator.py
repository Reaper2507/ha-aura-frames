from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import AuraApi, AuraApiError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


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
            logger=_LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=5),
        )

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        try:
            if not self.api.authenticated:
                await self.api.login()
            frames = await self.api.frames()
            data: dict[str, dict[str, Any]] = {}
            for frame in frames:
                frame_id = frame["id"]
                try:
                    details = await self.api.frame(frame_id)
                except AuraApiError as err:
                    _LOGGER.warning("Aura frame detail unavailable for %s; using frames.json data: %s", frame_id, err)
                    details = {}
                merged = {**frame, **details}
                assets = await self.api.assets(frame_id)
                merged["all_assets"] = assets
                merged["recent_assets"] = assets[:3]
                merged["current_asset"] = self._current_asset(merged, assets)
                data[frame_id] = merged
            return data
        except AuraApiError as err:
            raise UpdateFailed(str(err)) from err

    @staticmethod
    def _current_asset(frame: dict[str, Any], assets: list[dict[str, Any]]) -> dict[str, Any]:
        impression = frame.get("last_impression") or {}
        impression_asset = impression.get("asset") if isinstance(impression, dict) else None
        if isinstance(impression_asset, dict) and impression_asset.get("id"):
            return impression_asset
        current_id = impression.get("asset_id") if isinstance(impression, dict) else None
        current_id = current_id or frame.get("representative_asset_id")
        if current_id:
            for asset in assets:
                if asset.get("id") == current_id:
                    return asset
        return assets[0] if assets else {}

    async def navigate(self, frame_id: str, direction: int) -> None:
        frame = self.data.get(frame_id, {})
        assets = frame.get("all_assets") or []
        current = frame.get("current_asset") or {}
        if not assets or not current.get("id"):
            raise AuraApiError("No current Aura asset available")
        ids = [asset.get("id") for asset in assets]
        try:
            index = ids.index(current["id"])
        except ValueError:
            index = 0
        target = assets[(index + direction) % len(assets)]
        await self.api.show_now(frame_id, target["id"])
        await self.async_request_refresh()
        # The frames endpoint can lag behind a successful goto request.
        # Keep the coordinator's navigation cursor aligned with the write.
        self.data[frame_id]["current_asset"] = target

    async def async_close(self) -> None:
        return None



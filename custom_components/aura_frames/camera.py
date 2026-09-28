from __future__ import annotations

from homeassistant.components.camera import Camera
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AuraCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: AuraCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([AuraFrameCamera(coordinator, frame_id) for frame_id in coordinator.data])


class AuraFrameCamera(CoordinatorEntity[AuraCoordinator], Camera):
    _attr_icon = "mdi:image-frame"
    def __init__(self, coordinator: AuraCoordinator, frame_id: str) -> None:
        CoordinatorEntity.__init__(self, coordinator)
        Camera.__init__(self)
        self._frame_id = frame_id
        self._attr_unique_id = f"{frame_id}_camera"
        self._session = async_get_clientsession(coordinator.hass)

    @property
    def _frame(self):
        return self.coordinator.data.get(self._frame_id, {})

    @property
    def _asset_url(self) -> str | None:
        asset = self._frame.get("current_asset") or {}
        url = next((asset.get(key) for key in ("image_url", "landscape_url", "portrait_url", "thumbnail_url") if asset.get(key)), None)
        # Aura's CDN can serve JPEG bytes from a .heic URL. The URL is opaque;
        # changing its extension produces a different, often nonexistent asset.
        return url

    @property
    def name(self) -> str:
        return f"{self._frame.get('name', 'Aura Frame')} Camera"

    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, self._frame_id)}, "name": self._frame.get("name", "Aura Frame"), "manufacturer": "Aura", "model": self._frame.get("frame_type") or "Aura Frame"}

    async def async_camera_image(self, width: int | None = None, height: int | None = None) -> bytes | None:
        url = self._asset_url
        if not url:
            return None
        async with self._session.get(url) as response:
            if response.status != 200:
                return None
            return await response.read()


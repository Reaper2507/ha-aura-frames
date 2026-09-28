from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AuraCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: AuraCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for frame_id in coordinator.data:
        entities.extend((AuraFrameSensor(coordinator, frame_id), AuraFramePhotoSensor(coordinator, frame_id)))
    async_add_entities(entities)


class AuraFrameSensor(CoordinatorEntity[AuraCoordinator], SensorEntity):
    _attr_icon = "mdi:picture-frame"

    def __init__(self, coordinator: AuraCoordinator, frame_id: str) -> None:
        super().__init__(coordinator)
        self._frame_id = frame_id
        self._attr_unique_id = f"{frame_id}_status"

    @property
    def _frame(self):
        return self.coordinator.data.get(self._frame_id, {})

    @property
    def name(self) -> str:
        return f"{self._frame.get('name', 'Aura Frame')} Status"

    @property
    def native_value(self):
        return self._frame.get("name")

    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, self._frame_id)}, "name": self._frame.get("name", "Aura Frame"), "manufacturer": "Aura", "model": self._frame.get("frame_type") or "Aura Frame"}

    @property
    def extra_state_attributes(self):
        f = self._frame
        return {k: f.get(k) for k in ("display_aspect_ratio", "num_assets", "brightness", "auto_brightness", "slideshow_auto", "slideshow_interval", "sort_mode", "scheduled_display_sleep", "gestures_on", "live_photos_on", "sense_motion", "volume", "software_version", "build_version", "hw_android_version", "time_zone", "features")}


class AuraFramePhotoSensor(CoordinatorEntity[AuraCoordinator], SensorEntity):
    _attr_icon = "mdi:image-frame"

    def __init__(self, coordinator: AuraCoordinator, frame_id: str) -> None:
        super().__init__(coordinator)
        self._frame_id = frame_id
        self._attr_unique_id = f"{frame_id}_photo"

    @property
    def _frame(self):
        return self.coordinator.data.get(self._frame_id, {})

    @property
    def _asset(self):
        assets = self._frame.get("recent_assets") or []
        return assets[0] if assets else {}

    @property
    def name(self) -> str:
        return f"{self._frame.get('name', 'Aura Frame')} Photo"

    @property
    def native_value(self):
        asset = self._asset
        return next((asset.get(key) for key in ("image_url", "landscape_url", "portrait_url", "thumbnail_url") if asset.get(key)), None)

    @property
    def entity_picture(self) -> str | None:
        return self.native_value

    @property
    def extra_state_attributes(self):
        asset = self._asset
        return {"asset_id": asset.get("id"), "file_name": asset.get("file_name"), "image_url": self.native_value}


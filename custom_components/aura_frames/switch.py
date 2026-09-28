from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .control_entities import AuraFrameEntity
from .coordinator import AuraCoordinator

SWITCHES = (("auto_brightness", "Auto brightness"), ("slideshow_auto", "Slideshow"), ("scheduled_display_sleep", "Scheduled sleep"), ("gestures_on", "Gestures"), ("live_photos_on", "Live photos"), ("sense_motion", "Motion sensing"))


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: AuraCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([AuraFrameSwitch(coordinator, frame_id, *definition) for frame_id in coordinator.data for definition in SWITCHES])


class AuraFrameSwitch(AuraFrameEntity, SwitchEntity):
    def __init__(self, coordinator: AuraCoordinator, frame_id: str, field: str, name: str) -> None:
        AuraFrameEntity.__init__(self, coordinator, frame_id, field)
        self._field = field
        self._attr_name = name
        self._attr_icon = "mdi:toggle-switch"

    @property
    def is_on(self) -> bool:
        return bool(self.frame.get(self._field))

    async def async_turn_on(self, **kwargs) -> None:
        await self.async_update_frame({self._field: True})

    async def async_turn_off(self, **kwargs) -> None:
        await self.async_update_frame({self._field: False})

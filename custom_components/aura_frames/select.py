from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .control_entities import AuraFrameEntity
from .coordinator import AuraCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: AuraCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([AuraFrameSelect(coordinator, frame_id) for frame_id in coordinator.data if coordinator.data[frame_id].get("sort_mode") in ("chronological", "random")])


class AuraFrameSelect(AuraFrameEntity, SelectEntity):
    _attr_name = "Sort mode"
    _attr_icon = "mdi:sort"
    _attr_options = ["chronological", "random"]

    def __init__(self, coordinator: AuraCoordinator, frame_id: str) -> None:
        AuraFrameEntity.__init__(self, coordinator, frame_id, "sort_mode")

    @property
    def current_option(self) -> str | None:
        value = self.frame.get("sort_mode")
        return value if value in self.options else None

    async def async_select_option(self, option: str) -> None:
        await self.async_update_frame({"sort_mode": option})

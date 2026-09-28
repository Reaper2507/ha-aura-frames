from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .control_entities import AuraFrameEntity
from .coordinator import AuraCoordinator

BUTTONS = (("next", "Next", "mdi:skip-next"), ("previous", "Previous", "mdi:skip-previous"), ("show_now", "Show now", "mdi:play-box"), ("refresh", "Refresh", "mdi:refresh"))


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: AuraCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([AuraFrameButton(coordinator, frame_id, *definition) for frame_id in coordinator.data for definition in BUTTONS])


class AuraFrameButton(AuraFrameEntity, ButtonEntity):
    def __init__(self, coordinator: AuraCoordinator, frame_id: str, action: str, name: str, icon: str) -> None:
        AuraFrameEntity.__init__(self, coordinator, frame_id, action)
        self._action = action
        self._attr_name = name
        self._attr_icon = icon

    async def async_press(self) -> None:
        data = {"frame_id": self.frame_id}
        if self._action == "show_now":
            data["asset_id"] = (self.frame.get("current_asset") or {}).get("id")
        await self.hass.services.async_call(DOMAIN, self._action, data, blocking=True)


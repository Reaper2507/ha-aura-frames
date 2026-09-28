from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .control_entities import AuraFrameEntity
from .coordinator import AuraCoordinator

NUMBERS = (("brightness", "Brightness", 0, 100, 1), ("slideshow_interval", "Slideshow interval", 5, 3600, 5), ("volume", "Volume", 0, 100, 1))


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: AuraCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([AuraFrameNumber(coordinator, frame_id, *definition) for frame_id in coordinator.data for definition in NUMBERS])


class AuraFrameNumber(AuraFrameEntity, NumberEntity):
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator: AuraCoordinator, frame_id: str, field: str, name: str, minimum: float, maximum: float, step: float) -> None:
        AuraFrameEntity.__init__(self, coordinator, frame_id, field)
        self._field = field
        self._attr_name = name
        self._attr_native_min_value = minimum
        self._attr_native_max_value = maximum
        self._attr_native_step = step

    @property
    def native_value(self) -> float | None:
        value = self.frame.get(self._field)
        return float(value) if value is not None else None

    async def async_set_native_value(self, value: float) -> None:
        await self.async_update_frame({self._field: int(value)})

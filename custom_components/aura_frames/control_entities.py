from __future__ import annotations

from typing import Any

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import AuraCoordinator


class AuraFrameEntity(CoordinatorEntity[AuraCoordinator]):
    def __init__(self, coordinator: AuraCoordinator, frame_id: str, suffix: str) -> None:
        super().__init__(coordinator)
        self.frame_id = frame_id
        self._attr_unique_id = f"{frame_id}_{suffix}"

    @property
    def frame(self) -> dict[str, Any]:
        return self.coordinator.data.get(self.frame_id, {})

    @property
    def device_info(self):
        return {"identifiers": {("aura_frames", self.frame_id)}, "name": self.frame.get("name", "Aura Frame"), "manufacturer": "Aura", "model": self.frame.get("frame_type") or "Aura Frame"}

    async def async_update_frame(self, changes: dict[str, Any]) -> None:
        await self.coordinator.api.update_frame(self.frame_id, changes)
        await self.coordinator.async_request_refresh()

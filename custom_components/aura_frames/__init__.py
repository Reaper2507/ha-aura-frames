from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import AuraApi, AuraApiError
from .const import (
    DOMAIN,
    PLATFORMS,
    SERVICE_NEXT,
    SERVICE_PREVIOUS,
    SERVICE_REFRESH,
    SERVICE_SHOW_NOW,
)
from .coordinator import AuraCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = AuraCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    async def handle_frame_action(call: ServiceCall) -> None:
        frame_id = call.data["frame_id"]
        frame = coordinator.data.get(frame_id)
        if not frame:
            raise AuraApiError("Unknown Aura frame")
        action = call.service
        if action == SERVICE_SHOW_NOW:
            asset_id = call.data.get("asset_id")
            if not asset_id:
                assets = frame.get("recent_assets") or []
                asset_id = (assets[0] if assets else {}).get("id")
            if not asset_id:
                raise AuraApiError("No asset available for frame")
            await coordinator.api.show_now(frame_id, asset_id)
        elif action == SERVICE_REFRESH:
            await coordinator.async_request_refresh()
        elif action == SERVICE_NEXT:
            await coordinator.navigate(frame_id, 1)
        elif action == SERVICE_PREVIOUS:
            await coordinator.navigate(frame_id, -1)
        elif action == "exclude_asset":
            await coordinator.api.exclude_asset(frame_id, call.data["asset_id"])
        elif action == "include_asset":
            await coordinator.api.select_asset(frame_id, call.data["asset_id"])
        elif action == "remove_asset":
            await coordinator.api.remove_asset(frame_id, call.data["asset_id"])
        elif action == "delete_asset":
            await coordinator.api.delete_asset(call.data["asset_id"])
        await coordinator.async_request_refresh()

    for service in (SERVICE_SHOW_NOW, SERVICE_NEXT, SERVICE_PREVIOUS, SERVICE_REFRESH, "exclude_asset", "include_asset", "remove_asset", "delete_asset"):
        if not hass.services.has_service(DOMAIN, service):
            hass.services.async_register(DOMAIN, service, handle_frame_action)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    coordinator = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    if coordinator:
        await coordinator.async_close()
    return unloaded


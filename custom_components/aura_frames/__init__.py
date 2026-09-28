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
    SERVICE_SLEEP,
    SERVICE_WAKE,
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
        else:
            changes = {SERVICE_SLEEP: {"scheduled_display_sleep": True}, SERVICE_WAKE: {"scheduled_display_sleep": False}}.get(action)
            if changes:
                await coordinator.api.update_frame(frame_id, changes)
            elif action in (SERVICE_NEXT, SERVICE_PREVIOUS):
                assets = frame.get("recent_assets") or []
                if assets:
                    await coordinator.api.show_now(frame_id, assets[0]["id"])
        await coordinator.async_request_refresh()

    for service in (SERVICE_SHOW_NOW, SERVICE_NEXT, SERVICE_PREVIOUS, SERVICE_SLEEP, SERVICE_WAKE, SERVICE_REFRESH):
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


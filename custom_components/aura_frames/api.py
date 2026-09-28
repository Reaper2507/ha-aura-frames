from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from aiohttp import ClientSession

from .const import API_BASE


class AuraApiError(Exception):
    pass


class AuraApi:
    def __init__(self, session: ClientSession, email: str, password: str) -> None:
        self._session = session
        self._email = email
        self._password = password
        self._token: str | None = None
        self._user_id: str | None = None

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        headers = {
            "accept-language": "en-US",
            "cache-control": "no-cache",
            "user-agent": "Aura/4.7.790 (Android 30; Client)",
            "content-type": "application/json; charset=utf-8",
        }
        if self._token and self._user_id:
            headers.update({"x-token-auth": self._token, "x-user-id": self._user_id})
        async with self._session.request(method, f"{API_BASE}{path}", headers=headers, **kwargs) as response:
            payload = await response.json(content_type=None)
            if response.status >= 400 or payload.get("error"):
                raise AuraApiError(f"Aura API HTTP {response.status}")
            return payload

    async def login(self) -> None:
        payload = {
            "user": {"email": self._email, "password": self._password},
            "locale": "en-US",
            "app_identifier": "com.pushd.client",
            "identifier_for_vendor": "0000000000000000",
            "client_device_id": "0000000000000000",
        }
        response = await self._request("POST", "/login.json", json=payload)
        user = response.get("result", {}).get("current_user") or {}
        if not user.get("auth_token") or not user.get("id"):
            raise AuraApiError("Aura API login returned no session")
        self._token = user["auth_token"]
        self._user_id = str(user["id"])

    async def frames(self) -> list[dict[str, Any]]:
        response = await self._request("GET", "/frames.json")
        return response.get("frames") or []

    async def assets(self, frame_id: str, limit: int = 3) -> list[dict[str, Any]]:
        response = await self._request("GET", f"/frames/{frame_id}/assets.json", params={"limit": limit})
        return response.get("assets") or []

    async def show_now(self, frame_id: str, asset_id: str) -> dict[str, Any]:
        return await self._request(
            "POST",
            f"/frames/{frame_id}/goto.json",
            json={
                "asset_id": asset_id,
                "frame_id": frame_id,
                "goto_time": datetime.now(timezone.utc).isoformat(),
                "swipe_direction": 0,
                "select_asset": True,
            },
        )

    async def update_frame(self, frame_id: str, changes: dict[str, Any]) -> dict[str, Any]:
        return await self._request("PUT", f"/frames/{frame_id}.json", json={"frame": changes})


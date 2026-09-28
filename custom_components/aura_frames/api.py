from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import httpx

from .const import API_BASE


class AuraApiError(Exception):
    pass


class AuraApi:
    def __init__(self, session: object, email: str, password: str) -> None:
        self._email = email
        self._password = password
        self._token: str | None = None
        self._user_id: str | None = None
        # Aura's maintained reverse-engineered client uses HTTP/2 for the
        # pushd API. The write endpoints are not reliable over HTTP/1.1.
        self._client = httpx.AsyncClient(
            http2=True,
            headers={
                "accept-language": "en-US",
                "cache-control": "no-cache",
                "user-agent": "Aura/4.7.790 (Android 30; Client)",
                "content-type": "application/json; charset=utf-8",
                "x-device-identifier": "0000000000000000",
                "x-client-device-id": "0000000000000000",
            },
            timeout=20.0,
        )

    @property
    def authenticated(self) -> bool:
        return bool(self._token and self._user_id)

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        retry_auth = kwargs.pop("_retry_auth", True)
        headers: dict[str, str] = {}
        if self._token and self._user_id:
            headers.update({"x-token-auth": self._token, "x-user-id": self._user_id})
        response = await self._client.request(method, f"{API_BASE}{path}", headers=headers, **kwargs)
        try:
            payload = response.json()
            if response.status_code == 401 and path != "/login.json":
                self._token = None
                self._user_id = None
                if retry_auth:
                    await response.aclose()
                    await self.login()
                    return await self._request(method, path, _retry_auth=False, **kwargs)
            if response.status_code >= 400 or payload.get("error"):
                detail = payload.get("error") or payload.get("message") or ""
                raise AuraApiError(f"Aura API HTTP {response.status_code} for {method} {path}: {detail}")
            return payload
        finally:
            await response.aclose()

    async def close(self) -> None:
        await self._client.aclose()

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

    async def frame(self, frame_id: str) -> dict[str, Any]:
        response = await self._request("GET", f"/frames/{frame_id}.json")
        return response.get("frame") or {}

    async def assets_page(self, frame_id: str, limit: int = 1000, cursor: str | None = None) -> tuple[list[dict[str, Any]], str | None]:
        params: dict[str, Any] = {"limit": limit}
        if cursor:
            params["cursor"] = cursor
        response = await self._request("GET", f"/frames/{frame_id}/assets.json", params=params)
        return response.get("assets") or [], response.get("next_page_cursor")

    async def assets(self, frame_id: str, limit: int = 1000) -> list[dict[str, Any]]:
        assets: list[dict[str, Any]] = []
        cursor: str | None = None
        while True:
            page, cursor = await self.assets_page(frame_id, limit, cursor)
            assets.extend(page)
            if not cursor or not page:
                return assets

    async def show_now(self, frame_id: str, asset_id: str) -> dict[str, Any]:
        return await self._request(
            "POST",
            f"/frames/{frame_id}/goto.json",
            json={
                "asset_id": asset_id,
                "frame_id": frame_id,
                "goto_time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "swipe_direction": 0,
                "impression_id": str(uuid4()),
                "select_asset": True,
            },
        )

    async def select_asset(self, frame_id: str, asset_id: str) -> dict[str, Any]:
        return await self._request("POST", f"/frames/{frame_id}/select_asset.json", json={"assets": [{"asset_id": asset_id}]})

    async def select_local_asset(self, frame_id: str, local_identifier: str) -> dict[str, Any]:
        return await self._request("POST", f"/frames/{frame_id}/select_asset.json", json={"assets": [{"asset_local_identifier": local_identifier}]})

    async def batch_update_asset(self, metadata: dict[str, Any]) -> dict[str, Any]:
        return await self._request("PUT", "/assets/batch_update.json", json={"assets": [metadata]})

    async def asset_by_local_identifier(self, local_identifier: str) -> dict[str, Any]:
        return await self._request("GET", "/assets/asset_for_local_identifier.json", params={"local_identifier": local_identifier})

    async def exclude_asset(self, frame_id: str, asset_id: str) -> dict[str, Any]:
        return await self._request("POST", f"/frames/{frame_id}/exclude_asset", json={"assets": [{"asset_id": asset_id}]})

    async def remove_asset(self, frame_id: str, asset_id: str) -> dict[str, Any]:
        return await self._request("POST", f"/frames/{frame_id}/remove_asset.json", json={"assets": [{"asset_id": asset_id}]})

    async def delete_asset(self, asset_id: str) -> dict[str, Any]:
        return await self._request("DELETE", f"/assets/{asset_id}.json")

    async def update_frame(self, frame_id: str, changes: dict[str, Any]) -> dict[str, Any]:
        return await self._request("PUT", f"/frames/{frame_id}.json", json={"frame": changes})


"""Authenticated Aura upload command for the dashboard card."""

from __future__ import annotations

import asyncio
import base64
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from uuid import uuid4

import boto3
from PIL import Image
import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .api import AuraApiError
from .const import DOMAIN

_MAX_IMAGE_BYTES = 8 * 1024 * 1024
_COGNITO_POOL = "us-east-1:b92826c0-8274-43db-abff-136977c13598"
_BUCKET = "images.senseapp.co"


def _verify_jpeg(data: bytes) -> tuple[int, int]:
    if len(data) > _MAX_IMAGE_BYTES or len(data) < 4 or not data.startswith(b"\xff\xd8\xff"):
        raise ValueError("Bitte ein JPEG-Bild unter 8 MB auswählen")
    with Image.open(BytesIO(data)) as image:
        image.verify()
    with Image.open(BytesIO(data)) as image:
        if image.format != "JPEG" or image.width < 1 or image.height < 1:
            raise ValueError("Ungültiges JPEG-Bild")
        return image.size


def _upload_to_s3(data: bytes, key: str) -> str:
    """Use Aura's documented mobile upload identity in an executor thread."""
    import hashlib

    cognito = boto3.client("cognito-identity", region_name="us-east-1")
    identity = cognito.get_id(IdentityPoolId=_COGNITO_POOL)["IdentityId"]
    credentials = cognito.get_credentials_for_identity(IdentityId=identity)["Credentials"]
    s3 = boto3.client(
        "s3", region_name="us-east-1",
        aws_access_key_id=credentials["AccessKeyId"],
        aws_secret_access_key=credentials["SecretKey"],
        aws_session_token=credentials["SessionToken"],
    )
    s3.put_object(Body=data, Bucket=_BUCKET, Key=key, ContentType="image/jpeg")
    return base64.b64encode(hashlib.md5(data).digest()).decode("ascii")


@websocket_api.websocket_command({
    vol.Required("type"): "aura_frames/upload",
    vol.Required("frame_id"): str,
    vol.Required("content"): str,
})
@websocket_api.async_response
async def _ws_upload(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    coordinator = next(
        (item for item in hass.data.get(DOMAIN, {}).values() if msg["frame_id"] in item.data),
        None,
    )
    if coordinator is None:
        connection.send_error(msg["id"], "unknown_frame", "Aura-Rahmen nicht gefunden")
        return
    try:
        if len(msg["content"]) > (_MAX_IMAGE_BYTES * 4 // 3 + 8):
            raise ValueError("Bild ist zu groß")
        data = base64.b64decode(msg["content"], validate=True)
        width, height = await hass.async_add_executor_job(_verify_jpeg, data)
        local_id = str(uuid4())
        key = f"{uuid4()}.jpg"
        association = await coordinator.api.select_local_asset(msg["frame_id"], local_id)
        if association.get("number_failed", 0):
            raise AuraApiError("Aura hat die Rahmenzuordnung abgelehnt")
        md5_hash = await hass.async_add_executor_job(_upload_to_s3, data, key)
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        metadata = {
            "data_uti": "public.jpeg", "favorite": False,
            "file_name": key, "height": height, "width": width,
            "local_identifier": local_id, "location": None,
            "md5_hash": md5_hash, "modified_at": timestamp,
            "orientation": 1, "selected": True, "taken_at": timestamp,
            "upload_priority": 0,
        }
        result = await coordinator.api.batch_update_asset(metadata)
        ids = result.get("ids") or []
        asset_id = ids[0] if ids else None
        if isinstance(asset_id, dict):
            asset_id = asset_id.get("id")
        if not asset_id:
            for attempt in range(3):
                lookup = await coordinator.api.asset_by_local_identifier(local_id)
                asset_id = (lookup.get("asset") or {}).get("id")
                if asset_id:
                    break
                await asyncio.sleep(2)
        if not asset_id:
            raise AuraApiError("Upload abgeschlossen, Aura lieferte noch keine Bild-ID")
        await coordinator.api.show_now(msg["frame_id"], asset_id)
        coordinator._assets_cache.pop(msg["frame_id"], None)
        await coordinator.async_request_refresh()
        connection.send_result(msg["id"], {"asset_id": asset_id, "frame_id": msg["frame_id"]})
    except (AuraApiError, ValueError) as err:
        connection.send_error(msg["id"], "upload_failed", str(err))
    except Exception:
        connection.send_error(msg["id"], "upload_failed", "Upload fehlgeschlagen; bitte Home-Assistant-Protokoll prüfen")


async def async_register_upload(hass: HomeAssistant) -> None:
    key = f"{DOMAIN}_upload_registered"
    if hass.data.get(key):
        return
    path = Path(__file__).parent / "aura-upload-card.js"
    await hass.http.async_register_static_paths([
        StaticPathConfig("/aura_frames/aura-upload-card.js", str(path), False)
    ])
    websocket_api.async_register_command(hass, _ws_upload)
    hass.data[key] = True

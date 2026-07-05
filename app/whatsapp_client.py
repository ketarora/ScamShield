"""
Thin wrapper around the WhatsApp Cloud API: parsing incoming webhook
payloads, downloading media, and sending replies.
"""
import logging

import httpx

from app.config import get_settings

logger = logging.getLogger("scamshield.whatsapp")
settings = get_settings()

GRAPH_API_BASE = "https://graph.facebook.com/v20.0"


def verify_webhook(mode: str | None, token: str | None, challenge: str | None) -> str | None:
    """Handles Meta's GET /webhook verification handshake, done once when
    you register the webhook URL in the Meta dashboard."""
    if mode == "subscribe" and token == settings.whatsapp_verify_token:
        return challenge
    return None


def extract_message(payload: dict) -> dict | None:
    """
    Pulls the first inbound message out of WhatsApp's (deeply nested)
    webhook payload. Returns None for non-message events (delivery
    receipts, read receipts, etc.) which we just ignore.
    """
    try:
        entry = payload["entry"][0]
        change = entry["changes"][0]["value"]
        messages = change.get("messages")
        if not messages:
            return None
        message = messages[0]
        return {
            "from": message["from"],
            "type": message["type"],  # 'text' | 'image' | etc.
            "text": message.get("text", {}).get("body"),
            "image_id": message.get("image", {}).get("id"),
        }
    except (KeyError, IndexError):
        logger.warning("Unrecognized webhook payload shape: %s", payload)
        return None


async def download_media(media_id: str) -> bytes:
    """WhatsApp media downloads are two-step: get a signed URL, then fetch it."""
    headers = {"Authorization": f"Bearer {settings.whatsapp_token}"}
    async with httpx.AsyncClient(timeout=20) as client:
        meta_resp = await client.get(f"{GRAPH_API_BASE}/{media_id}", headers=headers)
        meta_resp.raise_for_status()
        media_url = meta_resp.json()["url"]

        file_resp = await client.get(media_url, headers=headers)
        file_resp.raise_for_status()
        return file_resp.content


async def send_text_message(to: str, body: str) -> None:
    """Sends a plain-text WhatsApp message back to the user."""
    url = f"{GRAPH_API_BASE}/{settings.whatsapp_phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {settings.whatsapp_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": body, "preview_url": False},
    }
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(url, headers=headers, json=payload)
        if resp.status_code >= 400:
            logger.error("Failed to send WhatsApp message: %s %s", resp.status_code, resp.text)
        resp.raise_for_status()

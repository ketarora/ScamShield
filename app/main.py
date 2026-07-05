"""
ScamShield -- FastAPI webhook server for the WhatsApp scam-detection bot.

Flow per incoming message:
  WhatsApp webhook POST -> verify signature -> ack immediately (200) ->
  process in background (OCR if needed -> LLM classify -> reply -> log)

We ack fast and process in the background because WhatsApp expects a
quick 2xx response to every webhook call -- doing the LLM call inline
risks Meta retrying or timing out the webhook on a slow response.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, FastAPI, Request, Response

from app.classifier import classify_message
from app.config import get_settings
from app.db import CheckRecord, SessionLocal, init_db
from app.formatting import format_reply
from app.ocr import extract_text_from_image
from app.security import hash_content, hash_phone, verify_whatsapp_signature
from app.whatsapp_client import download_media, extract_message, send_text_message, verify_webhook

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("scamshield.main")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="ScamShield", lifespan=lifespan)


@app.get("/webhook")
def webhook_verification(request: Request):
    """Meta calls this once when you register the webhook URL."""
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    result = verify_webhook(mode, token, challenge)
    if result is not None:
        return Response(content=result, media_type="text/plain")
    return Response(status_code=403)


@app.post("/webhook")
async def webhook_receive(request: Request, background_tasks: BackgroundTasks):
    raw_body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")
    if not verify_whatsapp_signature(settings.whatsapp_app_secret, raw_body, signature):
        logger.warning("Rejected webhook with invalid signature")
        return Response(status_code=403)

    payload = await request.json()
    message = extract_message(payload)
    if message is not None:
        background_tasks.add_task(process_message, message)

    return Response(status_code=200)


async def process_message(message: dict) -> None:
    sender = message["from"]
    phone_hash = hash_phone(sender)

    if message["type"] == "image" and message.get("image_id"):
        image_bytes = await download_media(message["image_id"])
        text = extract_text_from_image(image_bytes)
        input_type = "image"
    else:
        text = message.get("text") or ""
        input_type = "text"

    if not text.strip():
        await send_text_message(
            sender,
            "I couldn't read any text from that message. Try forwarding the "
            "original text, or a clearer screenshot.",
        )
        return

    result = await classify_message(text)
    reply = format_reply(result)
    await send_text_message(sender, reply)

    db = SessionLocal()
    try:
        record = CheckRecord(
            user_phone_hash=phone_hash,
            input_type=input_type,
            content_hash=hash_content(text),
            extracted_text=text[:2000],  # truncated; consider purging after a retention window
            verdict=result.verdict,
            reasoning=result.reasoning,
            confidence=result.confidence,
        )
        db.add(record)
        db.commit()
    finally:
        db.close()


@app.get("/health")
def health():
    return {"status": "ok"}

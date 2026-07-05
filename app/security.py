"""
Hashing helpers. We never store raw phone numbers long-term, and we
verify that incoming webhooks actually came from WhatsApp/Meta and not
some random script hitting our public endpoint. See PRD section 7
(Privacy) for the reasoning.
"""
import hashlib
import hmac


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def hash_phone(phone_number: str) -> str:
    return sha256_hex(phone_number)


def hash_content(text: str) -> str:
    return sha256_hex(text.strip().lower())


def verify_whatsapp_signature(app_secret: str, payload_body: bytes, signature_header: str | None) -> bool:
    """
    Verify the X-Hub-Signature-256 header Meta sends with every webhook
    POST. Without this check, anyone who finds your webhook URL could
    send fake messages and trigger LLM calls on your bill.
    """
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(app_secret.encode("utf-8"), payload_body, hashlib.sha256).hexdigest()
    received = signature_header.split("sha256=", 1)[1]
    return hmac.compare_digest(expected, received)

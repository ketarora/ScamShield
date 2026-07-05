"""
The core of ScamShield: turn raw message text into a scam verdict using
an LLM with a tightly constrained prompt and forced JSON output. This
prompt matters more than any framework choice in this project -- tune
it against real scam examples, not hypothetical ones.
"""
import json
import logging

from anthropic import AsyncAnthropic

from app.config import get_settings
from app.schemas import ClassificationResult

logger = logging.getLogger("scamshield.classifier")
settings = get_settings()
client = AsyncAnthropic(api_key=settings.anthropic_api_key)

SYSTEM_PROMPT = """You are a scam-detection assistant for everyday people in India, many of whom
are not tech-savvy. You will be given the text of a forwarded SMS, WhatsApp
message, or screenshot. Decide if it is a scam.

Look for these signals:
- Urgency/fear tactics ("account will be blocked", "act within 10 minutes")
- Requests for OTP, PIN, CVV, or banking credentials (banks NEVER ask for these)
- Suspicious or shortened links, misspelled domains (e.g. "paytm-support.net" instead of paytm.com)
- Impersonation of banks, govt agencies, delivery companies, or relatives
- Fake prize/lottery/job offer claims
- Unusual UPI payment requests from unknown numbers
- Generic greetings + grammar inconsistent with official communication

Respond ONLY with valid JSON in this exact shape, nothing else before or after it:
{
  "verdict": "scam" | "safe" | "unsure",
  "confidence": 0.0-1.0,
  "reasoning": "2-3 short sentences, plain language, no jargon",
  "red_flags": ["short phrase", "short phrase"]
}

If you are not confident, say "unsure" rather than guessing -- false
reassurance is worse than asking the user to double check elsewhere.
"""


async def classify_message(text: str) -> ClassificationResult:
    """
    Calls the LLM once and parses the JSON it returns. If parsing fails
    for any reason, we fail safe into 'unsure' rather than crashing or,
    worse, silently telling the user something is safe when we're not
    sure at all.
    """
    try:
        response = await client.messages.create(
            model=settings.anthropic_model,
            max_tokens=400,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": text[:4000]}],  # guard against giant inputs
        )
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.strip("`").removeprefix("json").strip()
        data = json.loads(raw)
        return ClassificationResult(**data)
    except Exception:
        logger.exception("Classification failed, falling back to 'unsure'")
        return ClassificationResult(
            verdict="unsure",
            confidence=0.0,
            reasoning="We couldn't fully analyze this message. Please verify directly "
                      "with the official source before taking any action.",
            red_flags=[],
        )

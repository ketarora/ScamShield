"""
Turns a ClassificationResult into a WhatsApp-formatted reply message.
WhatsApp supports *bold*, _italic_, and plain emoji -- no HTML/Markdown.
"""
from app.schemas import ClassificationResult

VERDICT_HEADERS = {
    "scam": "🚨 *LIKELY SCAM*",
    "safe": "✅ *LIKELY SAFE*",
    "unsure": "🤔 *NOT SURE*",
}


def format_reply(result: ClassificationResult) -> str:
    header = VERDICT_HEADERS[result.verdict]
    lines = [header, ""]

    if result.verdict == "scam":
        lines.append("⚠️ *ScamShield has analyzed this message:*")
        lines.append("")
        for flag in result.red_flags:
            lines.append(f"• {flag}")
        if result.red_flags:
            lines.append("")
        lines.append(result.reasoning)
        lines.append("")
        lines.append("🛑 *Do not click any links.* Block the sender.")
        lines.append("")
        lines.append("💬 Forward this check to someone who might need it.")
    elif result.verdict == "safe":
        lines.append(result.reasoning)
        lines.append("")
        lines.append("_Note: ScamShield isn't perfect. If anything feels off, "
                      "verify directly with the official source._")
    else:  # unsure
        lines.append(result.reasoning)
        lines.append("")
        lines.append("Please verify directly with the bank/company through "
                      "their official app or website before taking any action.")

    return "\n".join(lines)

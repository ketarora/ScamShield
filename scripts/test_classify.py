"""
Quick manual test for the classifier without needing the full WhatsApp
pipeline running. Useful while you're tuning the prompt against real
scam examples.

Usage:
    python scripts/test_classify.py "Paytm: Rs. 15,000 received. But PAYMENT IS FAILED. Click to confirm http://paytm-support.net within 10 min otherwise reverse."
"""
import asyncio
import sys

sys.path.append(".")

from app.classifier import classify_message  # noqa: E402


async def main():
    if len(sys.argv) < 2:
        print('Usage: python scripts/test_classify.py "<message text>"')
        return
    text = sys.argv[1]
    result = await classify_message(text)
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())

# ScamShield

A WhatsApp bot that lets anyone forward a suspicious message or screenshot and
get an instant scam verdict. See `ScamShield_PRD.md` (separate file) for the
full product spec — this README is the "how do I actually run this" doc.

**Status: tested, not yet deployed.** Every module has automated tests
covering the webhook handshake, signature verification, the full
message-processing flow, failure modes (malformed LLM output, corrupted
images), and privacy behavior (phone numbers are hashed, never stored raw).
What's left is connecting it to a real WhatsApp number and a real database —
that's on you, and it's mostly account setup, not code.

## How it actually works

There's no website and no UI to build — WhatsApp is the entire interface.
Meta's WhatsApp Cloud API sends your FastAPI server a webhook (an HTTP POST)
every time someone messages your bot's number. Your server processes it and
calls the same API to send a reply, which shows up as a normal WhatsApp
message in the user's chat.

## Project structure
```
app/
  main.py             FastAPI app, webhook routes, message processing
  config.py           Settings loaded from .env
  db.py               SQLAlchemy models + session
  schemas.py          Pydantic schema for the LLM's structured output
  classifier.py       LLM call + the scam-detection prompt
  whatsapp_client.py  WhatsApp Cloud API calls (parse, download, send)
  ocr.py              Screenshot -> text extraction (Tesseract)
  formatting.py       Turns a verdict into a WhatsApp reply message
  security.py         Phone/content hashing + webhook signature check
scripts/
  test_classify.py    Test the LLM prompt directly, no WhatsApp needed
```

## 1. Set up WhatsApp Cloud API (do this first — it's the slow part)

1. Go to [Meta for Developers](https://developers.facebook.com/) and create
   an app of type "Business".
2. Add the **WhatsApp** product to the app.
3. Under WhatsApp > API Setup you'll get a **temporary access token** and a
   **phone number ID** for testing — copy these into `.env`.
4. Under App Settings > Basic, copy the **App Secret** into `.env`.
5. Pick any random string yourself for `WHATSAPP_VERIFY_TOKEN` — you'll enter
   this same value in the Meta dashboard when you register the webhook.

The temporary access token expires in 24 hours — fine for local testing, but
generate a permanent token (System User token, under Business Settings) before
you deploy for real use.

## 2. Local setup

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # then fill in real values
```

You also need Tesseract installed on your machine (the binary, not just the
Python wrapper already in requirements.txt):
- macOS: `brew install tesseract`
- Ubuntu/Debian: `sudo apt install tesseract-ocr`
- Windows: install from the [Tesseract releases page](https://github.com/UB-Mannheim/tesseract/wiki)

Create a free Postgres database — Supabase or Neon both hand you a connection
string immediately on signup, no local Postgres install needed. Paste it into
`DATABASE_URL`.

Get an Anthropic API key from the [Anthropic Console](https://console.anthropic.com/)
and paste it into `ANTHROPIC_API_KEY`.

Run the server:
```bash
uvicorn app.main:app --reload --port 8000
```
Tables are created automatically on startup.

## 3. Test the classifier directly (before touching WhatsApp at all)

This is the fastest way to tune the prompt — no webhook, no ngrok, just the
LLM call:
```bash
python scripts/test_classify.py "Paytm: Rs. 15,000 received. But PAYMENT IS FAILED. Click to confirm http://paytm-support.net within 10 min otherwise reverse."
```
You should get back JSON with `"verdict": "scam"` and red flags called out.
Run it against a handful of real scam texts and a handful of legit ones
before moving on — this is your actual accuracy check.

## 4. Expose your local server to the internet

Meta needs to reach your webhook over HTTPS. For local testing use ngrok:
```bash
ngrok http 8000
```
Copy the `https://...ngrok-free.app` URL it gives you.

## 5. Register the webhook with Meta

In your app's WhatsApp > Configuration settings:
- **Callback URL**: `https://<your-ngrok-or-real-domain>/webhook`
- **Verify Token**: the same string you put in `WHATSAPP_VERIFY_TOKEN`
- Subscribe to the `messages` webhook field.

Meta calls your `GET /webhook` once to verify — if `uvicorn` is running, this
should just succeed.

## 6. Test it for real

Add your own WhatsApp number as a test recipient in the Meta dashboard
(required for unverified apps), then message your bot's test number with a
sample scam SMS or a screenshot. Watch your `uvicorn` terminal logs as it
comes in.

## 7. Deploy for real

Push this repo to Render or Railway, set the same environment variables in
their dashboard, point the Meta webhook URL at your real deployed domain
instead of the ngrok URL, and swap the temporary WhatsApp token for a
permanent System User token (otherwise it dies after 24 hours in production).

## Notes worth keeping in mind

- Phone numbers are hashed before storage and message text is truncated at
  2000 characters — see PRD section 7 for why. Don't quietly remove that.
- Tables auto-create via `Base.metadata.create_all` on startup — fine for an
  MVP. Move to Alembic migrations once the schema needs to change without
  risking existing data.
- The classifier defaults to a small/fast model
  (`claude-haiku-4-5-20251001`) since this task needs consistent JSON output
  and pattern-matching, not frontier reasoning — keep it that way unless your
  accuracy testing in step 3 tells you otherwise.
- If accuracy on real forwarded scam screenshots is poor, the OCR step
  (Tesseract) is the most likely first suspect, not the LLM — check what text
  it's actually extracting before assuming the classifier is wrong.

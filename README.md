# Contacts Echo Telegram Bot (Webhook, Cloud Run compatible)

This repository contains a minimal, modern Telegram echo bot using:
- aiogram v3 (async, modern Telegram bot framework)
- FastAPI (ASGI web framework)
- Webhook delivery (suitable for Google Cloud Run)

The bot simply echoes any text messages it receives.

## Environment variables

Set the following environment variables:

- `TELEGRAM_TOKEN` (required): Your bot token from BotFather.
- `WEBHOOK_URL` (recommended in production): Your public HTTPS base URL (e.g., your Cloud Run service URL). The bot appends `/telegram/webhook` to this base. When set, the app will call `setWebhook` on startup.
- `WEBHOOK_SECRET` (recommended): A secret string used to verify incoming updates via the `X-Telegram-Bot-Api-Secret-Token` header.
- `PORT` (optional): Port for the web server. Default is `8080`. Cloud Run will set this automatically.

The webhook path is fixed as `/telegram/webhook`.

## Local development

1. Create a virtual environment and install dependencies:

```bash
python -m venv .venv
. .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

2. Export environment variables and run the server:

```bash
export TELEGRAM_TOKEN=123456:ABC...
export WEBHOOK_SECRET=some-long-random-string
# If you have a public URL (like from ngrok), set it so the app registers the webhook on startup
export WEBHOOK_URL=https://your-public-url.example

python -m uvicorn main:app --host 0.0.0.0 --port 8080
```

3. If you are using a local tunnel (ngrok, cloudflared, etc.), ensure it forwards HTTPS to `http://localhost:8080` and set `WEBHOOK_URL` to the public tunnel URL. Telegram requires HTTPS.

> Note: If you don't set `WEBHOOK_URL`, the application will not call `setWebhook` automatically. You can set it manually via Telegram API if desired.

## Docker

Build and run locally with Docker:

```bash
docker build -t contacts-echo-bot .
# Replace the env vars below
docker run --rm -p 8080:8080 \
  -e TELEGRAM_TOKEN=123456:ABC... \
  -e WEBHOOK_SECRET=some-long-random-string \
  -e WEBHOOK_URL=https://your-public-url.example \
  contacts-echo-bot
```

## Deploy to Google Cloud Run

Prerequisites:
- A Google Cloud project
- gcloud CLI authenticated and configured
- Artifact Registry enabled (optional, if pushing images)

### Option A: Build and deploy from source (recommended for simplicity)

```bash
gcloud run deploy contacts-echo-bot \
  --source . \
  --region YOUR_REGION \
  --allow-unauthenticated \
  --set-env-vars TELEGRAM_TOKEN=123456:ABC...,WEBHOOK_SECRET=some-long-random-string,WEBHOOK_URL=https://YOUR_SERVICE_URL
```

After deployment, update `WEBHOOK_URL` to your new service URL and redeploy or update the service configuration. The app sets the webhook automatically on startup.

### Option B: Build Docker image and deploy

```bash
# Build and push image
gcloud builds submit --tag gcr.io/$(gcloud config get-value project)/contacts-echo-bot:latest .

# Deploy image
gcloud run deploy contacts-echo-bot \
  --image gcr.io/$(gcloud config get-value project)/contacts-echo-bot:latest \
  --region YOUR_REGION \
  --allow-unauthenticated \
  --set-env-vars TELEGRAM_TOKEN=123456:ABC...,WEBHOOK_SECRET=some-long-random-string,WEBHOOK_URL=https://YOUR_SERVICE_URL
```

## Endpoints

- `GET /` → simple status check
- `GET /healthz` → health check
- `POST /telegram/webhook` → Telegram webhook receiver (expects `X-Telegram-Bot-Api-Secret-Token` header when `WEBHOOK_SECRET` is set)

## Notes

- The bot registers only `message` updates to keep it minimal.
- For production, always set `WEBHOOK_SECRET` and use HTTPS.
- Cloud Run automatically provides HTTPS; use the service URL as `WEBHOOK_URL`.

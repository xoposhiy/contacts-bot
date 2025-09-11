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

## Requirements and Design docs

Are located in the [docs](./docs) folder.
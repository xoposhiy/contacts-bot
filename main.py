import os
import logging
from fastapi import FastAPI, Request, HTTPException
from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import Message, Update
from aiogram.client.default import DefaultBotProperties

# Configure logging
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s - %(name)s: %(message)s")
logger = logging.getLogger("contacts-bot")

# Environment configuration
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise RuntimeError("Environment variable TELEGRAM_TOKEN is required.")

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")  # Optional but recommended for security
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")  # Public base URL for your Cloud Run service, e.g. https://your-service-abcde.a.run.app
WEBHOOK_PATH = "/telegram/webhook"
PORT = int(os.getenv("PORT", "8080"))

# Initialize bot and dispatcher (aiogram v3)
bot = Bot(token=TELEGRAM_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()
router = Router()


@router.message(F.text)
async def echo_text(message: Message):
    """Echo any received text message back to the user."""
    await message.reply(message.text)


# Register router
dp.include_router(router)

# Create FastAPI app
app = FastAPI(title="Contacts Echo Bot", version="1.0.0")


@app.on_event("startup")
async def on_startup():
    # Set webhook on startup if WEBHOOK_URL is provided
    if not WEBHOOK_SECRET:
        logger.warning("WEBHOOK_SECRET is not set; requests won't be verified via Telegram secret token header.")
    if WEBHOOK_URL:
        full_url = WEBHOOK_URL.rstrip("/") + WEBHOOK_PATH
        await bot.set_webhook(
            url=full_url,
            secret_token=(WEBHOOK_SECRET or None),
            drop_pending_updates=True,
            allowed_updates=["message"],
        )
        logger.info(f"Webhook set to {full_url}")
    else:
        logger.warning("WEBHOOK_URL not set, skipping set_webhook(). Set it to your Cloud Run HTTPS URL to receive updates.")


@app.on_event("shutdown")
async def on_shutdown():
    # Optional cleanup
    try:
        await bot.delete_webhook(drop_pending_updates=False)
    except Exception as e:
        logger.exception("Failed to delete webhook: %s", e)
    await bot.session.close()


@app.get("/")
async def root():
    return {"status": "ok"}


@app.get("/healthz")
async def healthz():
    return {"status": "healthy"}


@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    # Verify Telegram's secret token header when configured
    if WEBHOOK_SECRET:
        header_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if header_secret != WEBHOOK_SECRET:
            raise HTTPException(status_code=403, detail="Invalid secret token")

    data = await request.json()
    update = Update.model_validate(data)
    await dp.feed_update(bot, update)
    return {"ok": True}


if __name__ == "__main__":
    # Local dev server startup (Cloud Run will use the container CMD)
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=PORT, log_level="info")

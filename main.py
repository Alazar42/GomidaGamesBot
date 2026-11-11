from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import os
import asyncio
import logging
import json
from telegram import Update
from contextlib import asynccontextmanager

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

print("🚀 Initializing Gomida Games Bot...")

application = None
BOT_TOKEN = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and Shutdown logic for FastAPI."""
    global application, BOT_TOKEN

    from bot_setup import application as bot_app, BOT_TOKEN as token
    application = bot_app
    BOT_TOKEN = token

    webhook_url = os.getenv("WEBHOOK_URL", "").strip()
    if not webhook_url:
        render_url = os.getenv("RENDER_EXTERNAL_URL", "").strip().rstrip("/")
        if render_url:
            webhook_url = f"{render_url}/webhook"
    if not webhook_url:
        raise RuntimeError("Set WEBHOOK_URL or run as a Render web service")

    await application.initialize()
    try:
        await application.bot.set_webhook(webhook_url)
        logger.info("Telegram webhook registered at %s", webhook_url)
        await application.start()
        try:
            yield
        finally:
            await application.stop()
    finally:
        await application.shutdown()


app = FastAPI(title="Gomida Games Bot", lifespan=lifespan)


@app.post("/webhook")
async def telegram_webhook(request: Request):
    if not application:
        return JSONResponse({"error": "Application not initialized"}, status_code=500)

    try:
        body = await request.body()
        data = json.loads(body)

        update = Update.de_json(data, application.bot)
        await application.process_update(update)

        return JSONResponse({"status": "ok"})

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/")
async def home():
    return {
        "service": "Gomida Games Telegram Bot",
        "status": "running",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "webhook": os.getenv("WEBHOOK_URL"),
        "bot_token": bool(os.getenv("BOT_TOKEN")),
        "ready": application is not None
    }


@app.get("/info")
async def info():
    if not application:
        return {"error": "Bot not initialized"}

    try:
        bot = await application.bot.get_me()
        webhook = await application.bot.get_webhook_info()
        return {
            "bot": {
                "id": bot.id,
                "username": bot.username,
                "name": bot.first_name,
            },
            "webhook": {
                "url": webhook.url,
                "pending": webhook.pending_update_count
            }
        }
    except Exception as e:
        return {"error": str(e), "type": type(e).__name__}

# LOCAL DEVELOPMENT (polling)
if __name__ == "__main__":
    import uvicorn

    if os.getenv("RENDER_SERVICE_TYPE") == "web" or os.getenv("WEBHOOK_URL") or os.getenv("ENVIRONMENT") == "production":
        uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "10000")))
    else:
        print("🚀 DEVELOPMENT MODE — USING POLLING (no webhook)")
        from bot_setup import application as bot_app
        bot_app.run_polling()



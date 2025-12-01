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

    webhook_url = os.getenv("WEBHOOK_URL", "")
    is_production = os.getenv("ENVIRONMENT", "development") == "production"

    print(f"🔧 Environment: {os.getenv('ENVIRONMENT')}  Webhook: {webhook_url}")

    if is_production and webhook_url:
        try:
            print("🔄 Removing old webhook...")
            await application.bot.delete_webhook()

            print("🔄 Setting new webhook...")
            await application.bot.set_webhook(webhook_url)

            info = await application.bot.get_webhook_info()
            print(f"✅ Webhook set to: {info.url}")

        except Exception as e:
            print(f"❌ Webhook setup failed: {e}")

    # 🔥 START THE BOT (THIS WAS MISSING)
    print("🚀 Starting Telegram bot (webhook mode)...")
    await application.initialize()
    await application.start()
    print("✅ Bot is running and accepting updates!")

    yield

    # 🔥 CLEAN SHUTDOWN
    print("🛑 Stopping bot gracefully...")
    try:
        await application.stop()
        await application.shutdown()
        print("✅ Bot stopped cleanly")
    except Exception as e:
        print(f"❌ Error during shutdown: {e}")


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
    import os
    import uvicorn

    os.environ["ENVIRONMENT"] = "development"
    print("🚀 DEVELOPMENT MODE — USING POLLING (no webhook)")

    # Import bot_setup manually (creates application)
    from bot_setup import application as bot_app

    # Start polling directly (no initialize(), no async)
    bot_app.run_polling()



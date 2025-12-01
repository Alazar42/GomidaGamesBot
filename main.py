from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import os
import logging
import asyncio
from telegram import Update
from contextlib import asynccontextmanager

from bot_setup import application, BOT_TOKEN

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Store the polling task
polling_task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI (replaces on_event)"""
    global polling_task
    
    # Startup
    try:
        # For local development, use polling
        # For production, use webhook
        
        webhook_url = os.getenv("WEBHOOK_URL")
        is_production = os.getenv("ENVIRONMENT") == "production"
        
        if is_production and webhook_url:
            # Production with webhook
            await application.bot.set_webhook(webhook_url)
            logger.info(f"Webhook set to: {webhook_url}")
        else:
            # Local development with polling
            logger.info("Starting bot with polling...")
            await application.initialize()
            await application.start()
            
            # Start polling in background task
            polling_task = asyncio.create_task(application.updater.start_polling())
            logger.info("Bot started with polling mode")
            
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
    
    yield  # App runs here
    
    # Shutdown
    try:
        if polling_task:
            polling_task.cancel()
            try:
                await polling_task
            except asyncio.CancelledError:
                pass
        
        await application.stop()
        await application.shutdown()
        logger.info("Bot stopped")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

app = FastAPI(title="Gomida Games Bot", lifespan=lifespan)

@app.post("/webhook")
async def webhook(request: Request):
    """Handle Telegram webhook updates (for production)"""
    try:
        # Get the update from Telegram
        data = await request.json()
        update = Update.de_json(data, application.bot)
        
        # Process the update
        await application.process_update(update)
        return JSONResponse(content={"status": "ok"})
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/")
async def read_root():
    """Health check endpoint"""
    is_production = os.getenv("ENVIRONMENT") == "production"
    mode = "webhook" if is_production else "polling"
    
    return {
        "message": f"Gomida Games Telegram Bot is running in {mode} mode!",
        "status": "active",
        "mode": mode,
        "endpoints": {
            "webhook": "POST /webhook",
            "health": "GET /",
            "info": "GET /info"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "gomida-games-bot"}

@app.get("/info")
async def bot_info():
    """Get bot information"""
    try:
        bot_info = await application.bot.get_me()
        return {
            "bot_username": bot_info.username,
            "bot_name": bot_info.first_name,
            "mode": "webhook" if application.updater is None else "polling",
            "is_running": True
        }
    except Exception as e:
        return {"error": str(e)}

# For local development
if __name__ == "__main__":
    import uvicorn
    
    # For local development, ensure we use polling
    os.environ["ENVIRONMENT"] = "development"
    
    print("🚀 Starting Gomida Games Bot in LOCAL DEVELOPMENT mode...")
    print("📱 Bot will use POLLING (no webhook required)")
    print("🌐 API server running at: http://localhost:8000")
    print("📊 Check status at: http://localhost:8000/")
    print("ℹ️  Bot info at: http://localhost:8000/info")
    print("\n⚠️  IMPORTANT: Make sure your .env file has BOT_TOKEN set!")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
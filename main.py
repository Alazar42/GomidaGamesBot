from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import os
import logging
import asyncio
from telegram import Update
from contextlib import asynccontextmanager
import json

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

print("🚀 Initializing Gomida Games Bot...")

# We'll import bot_setup inside lifespan to avoid circular imports
application = None
BOT_TOKEN = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI"""
    global application, BOT_TOKEN
    
    # Import here to avoid circular imports
    from bot_setup import application as app_instance, BOT_TOKEN as token
    application = app_instance
    BOT_TOKEN = token
    
    # Startup
    webhook_url = os.getenv("WEBHOOK_URL", "")
    is_production = os.getenv("ENVIRONMENT", "development") == "production"
    
    print(f"🔧 Startup - Production: {is_production}, Webhook URL: {webhook_url}")
    
    if is_production and webhook_url:
        try:
            print("🔄 Setting up webhook...")
            # Remove any existing webhook first
            await application.bot.delete_webhook()
            print("✅ Old webhook removed")
            
            # Set new webhook
            result = await application.bot.set_webhook(webhook_url)
            print(f"✅ Webhook set: {result}")
            
            # Verify webhook info
            webhook_info = await application.bot.get_webhook_info()
            print(f"📊 Webhook info: {webhook_info.url}")
            print(f"📊 Webhook pending updates: {webhook_info.pending_update_count}")
            
        except Exception as e:
            print(f"❌ Error setting webhook: {e}")
            logger.error(f"Webhook setup failed: {e}")
    else:
        print("📡 Running in development mode (no webhook)")
    
    yield  # App runs here
    
    # Shutdown
    print("🛑 Shutting down...")
    try:
        if is_production and application:
            await application.bot.delete_webhook()
            print("✅ Webhook removed")
    except Exception as e:
        print(f"❌ Error during shutdown: {e}")

app = FastAPI(title="Gomida Games Bot", lifespan=lifespan)

@app.post("/webhook")
async def webhook(request: Request):
    """Handle Telegram webhook updates"""
    if not application:
        return JSONResponse({"error": "Application not initialized"}, status_code=500)
    
    try:
        # Get the raw body for debugging
        body = await request.body()
        print(f"📨 Received webhook request, body length: {len(body)} bytes")
        
        # Parse JSON
        data = json.loads(body)
        
        # Log the update type for debugging
        if 'message' in data:
            msg = data['message']
            chat_id = msg.get('chat', {}).get('id')
            text = msg.get('text', '')
            print(f"💬 Message from chat {chat_id}: {text[:50]}")
        elif 'callback_query' in data:
            print(f"🔄 Callback query received")
        
        # Process the update
        update = Update.de_json(data, application.bot)
        await application.process_update(update)
        
        return JSONResponse(content={"status": "ok", "processed": True})
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON decode error: {e}")
        logger.error(f"JSON decode error: {e}")
        return JSONResponse(content={"error": "Invalid JSON"}, status_code=400)
    except Exception as e:
        print(f"❌ Error processing webhook: {e}")
        logger.error(f"Webhook processing error: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/")
async def read_root():
    """Health check endpoint"""
    webhook_url = os.getenv("WEBHOOK_URL", "")
    bot_token_exists = bool(os.getenv("BOT_TOKEN"))
    
    return {
        "service": "Gomida Games Telegram Bot",
        "status": "running",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "webhook_url": webhook_url,
        "bot_token_set": bot_token_exists,
        "application_ready": application is not None
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "application_ready": application is not None}

@app.get("/info")
async def bot_info():
    """Get bot information"""
    if not application:
        return {"error": "Application not initialized"}
    
    try:
        # Try to get bot info
        bot = await application.bot.get_me()
        webhook_info = await application.bot.get_webhook_info()
        
        return {
            "bot": {
                "username": bot.username,
                "name": bot.first_name,
                "id": bot.id
            },
            "webhook": {
                "url": webhook_info.url,
                "pending_updates": webhook_info.pending_update_count
            }
        }
    except Exception as e:
        return {"error": str(e), "type": type(e).__name__}

# For local development
if __name__ == "__main__":
    import uvicorn
    
    # For local development, ensure we use polling
    os.environ["ENVIRONMENT"] = "development"
    
    print("🚀 Starting Gomida Games Bot in LOCAL DEVELOPMENT mode...")
    print("📱 Bot will use POLLING (no webhook required)")
    print("🌐 API server running at: http://localhost:8000")
    print("📊 Check status at: http://localhost:8000/")
    print("ℹ️  Info at: http://localhost:8000/info")
    print("\n⚠️  IMPORTANT: Make sure your .env file has BOT_TOKEN set!")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
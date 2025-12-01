from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
import os
import logging
import asyncio
from telegram import Update
from contextlib import asynccontextmanager
import json

from bot_setup import application, BOT_TOKEN

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

print("🚀 Initializing Gomida Games Bot...")
print(f"📁 Current directory: {os.getcwd()}")
print(f"📦 Python version: {os.sys.version}")
print(f"🌍 Environment: {os.getenv('ENVIRONMENT', 'development')}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI"""
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
        if is_production:
            await application.bot.delete_webhook()
            print("✅ Webhook removed")
    except Exception as e:
        print(f"❌ Error during shutdown: {e}")

app = FastAPI(title="Gomida Games Bot", lifespan=lifespan)

@app.post("/webhook")
async def webhook(request: Request):
    """Handle Telegram webhook updates"""
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
        "endpoints": {
            "webhook": "POST /webhook",
            "health": "GET /health",
            "info": "GET /info",
            "setwebhook": "GET /setwebhook",
            "deletewebhook": "GET /deletewebhook"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

@app.get("/info")
async def bot_info():
    """Get bot information"""
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
                "pending_updates": webhook_info.pending_update_count,
                "has_custom_certificate": webhook_info.has_custom_certificate
            },
            "timestamp": os.getenv("VERCEL_REGION", "local")
        }
    except Exception as e:
        return {"error": str(e), "type": type(e).__name__}

@app.get("/setwebhook")
async def set_webhook_endpoint():
    """Manually set webhook (for debugging)"""
    try:
        webhook_url = os.getenv("WEBHOOK_URL", "")
        if not webhook_url:
            return {"error": "WEBHOOK_URL not set"}
        
        result = await application.bot.set_webhook(webhook_url)
        webhook_info = await application.bot.get_webhook_info()
        
        return {
            "success": True,
            "result": result,
            "webhook_url": webhook_info.url,
            "pending_updates": webhook_info.pending_update_count
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/deletewebhook")
async def delete_webhook_endpoint():
    """Delete webhook (for debugging)"""
    try:
        result = await application.bot.delete_webhook()
        return {"success": True, "result": result}
    except Exception as e:
        return {"error": str(e)}

@app.get("/test")
async def test_endpoint():
    """Test if bot can send messages"""
    try:
        # Try to send a test message to yourself
        test_chat_id = os.getenv("TEST_CHAT_ID")
        if test_chat_id:
            await application.bot.send_message(
                chat_id=test_chat_id,
                text="✅ Bot is working on Vercel!"
            )
            return {"success": True, "message": "Test message sent"}
        else:
            return {"success": False, "message": "TEST_CHAT_ID not set"}
    except Exception as e:
        return {"error": str(e)}

# Add a catch-all route for debugging
@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def catch_all(path: str, request: Request):
    """Catch-all route for debugging"""
    method = request.method
    print(f"🌐 {method} request to /{path}")
    
    return {
        "path": f"/{path}",
        "method": method,
        "message": "Route not specifically handled"
    }

# No need for __main__ block since Vercel imports the app directly
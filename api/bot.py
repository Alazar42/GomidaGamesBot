from fastapi import FastAPI, Request, Response
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
    ConversationHandler
)
from bot.commands import start, stop
from bot.callbacks import (
    handle_message_response, 
    handle_contact_shared, 
    handle_callback_query
)
import os
import logging
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="Gomida Games Bot")

# Global variable to store the application
bot_application = None

def create_application():
    """Create and configure the Telegram bot application"""
    # Get bot token from environment
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN environment variable is not set")
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Set up handlers
    response_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message_response)
    contact_handler = MessageHandler(filters.CONTACT, handle_contact_shared)
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={},
        fallbacks=[CommandHandler("stop", stop)],
    )
    
    # Add handlers
    application.add_handler(conv_handler)
    application.add_handler(response_handler)
    application.add_handler(contact_handler)
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    application.add_handler(CommandHandler("start", start))
    
    # Initialize application
    application.initialize()
    
    return application

@app.on_event("startup")
async def on_startup():
    """Initialize bot on startup"""
    global bot_application
    logger.info("Starting Gomida Games Bot...")
    
    # Get webhook URL from environment
    WEBHOOK_URL = os.getenv("WEBHOOK_URL")
    if not WEBHOOK_URL:
        raise ValueError("WEBHOOK_URL environment variable is not set")
    
    # Create and configure application
    bot_application = create_application()
    
    # Get bot info
    bot = await bot_application.bot.get_me()
    logger.info(f"Bot started: @{bot.username}")
    
    # Set webhook
    webhook_url = f"{WEBHOOK_URL}/webhook"
    await bot_application.bot.set_webhook(webhook_url)
    logger.info(f"Webhook set to: {webhook_url}")

@app.on_event("shutdown")
async def on_shutdown():
    """Clean up on shutdown"""
    global bot_application
    if bot_application:
        logger.info("Shutting down bot...")
        await bot_application.shutdown()
        bot_application = None
        logger.info("Bot shut down")

@app.post("/webhook")
async def webhook(request: Request):
    """Handle Telegram webhook updates"""
    global bot_application
    
    if not bot_application:
        return Response(content="Bot not initialized", status_code=500)
    
    try:
        # Parse the update
        body = await request.body()
        data = json.loads(body.decode('utf-8'))
        update = Update.de_json(data, bot_application.bot)
        
        # Process the update
        await bot_application.process_update(update)
        
        return Response(content="OK", status_code=200)
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return Response(content="Error", status_code=500)

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "service": "Gomida Games Bot",
        "message": "Bot is running on FastAPI"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
#!/usr/bin/env python3
"""
Run bot in polling mode for local testing
"""
import os
import sys
import asyncio

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler
)

from bot.commands import start, stop
from bot.callbacks import (
    handle_message_response,
    handle_contact_shared,
    handle_callback_query
)

async def main():
    """Run bot in polling mode"""
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    if not BOT_TOKEN:
        print("❌ ERROR: BOT_TOKEN not found")
        print("Create .env file with: BOT_TOKEN=your_token_here")
        return
    
    # Create application
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # IMPORTANT: Delete any existing webhook first
    await app.bot.delete_webhook()
    print("✅ Webhook removed - now using polling")
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message_response))
    app.add_handler(MessageHandler(filters.CONTACT, handle_contact_shared))
    app.add_handler(CallbackQueryHandler(handle_callback_query))
    
    print("🚀 Gomida Games Bot Started!")
    print("📱 Go to Telegram and send /start to @adwa1888bot")
    print("⏳ Polling for updates...")
    
    # Run polling
    await app.run_polling()

if __name__ == "__main__":
    # Windows compatibility
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot stopped")
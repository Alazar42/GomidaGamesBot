#!/usr/bin/env python3
"""
Local development script for running the bot with polling.
For production on Vercel, use the FastAPI version in api/bot.py
"""
import os
import asyncio
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    CallbackQueryHandler
)
from .commands import start, stop
from .callbacks import (
    handle_message_response,
    handle_contact_shared,
    handle_callback_query
)
from dotenv import load_dotenv

load_dotenv()

async def main():
    """Run the bot in polling mode for local development"""
    # Get bot token
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    if not BOT_TOKEN:
        raise ValueError("Please set BOT_TOKEN in your .env file")
    
    # Create application
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
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
    
    # Run the bot
    print("Gomida Games Bot is Running ✔ (Polling Mode)")
    await application.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
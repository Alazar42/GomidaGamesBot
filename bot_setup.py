import os
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ConversationHandler
from dotenv import load_dotenv
from commands import start, stop
from callbacks import handle_message_response, handle_contact_shared, handle_callback_query

# Load environment variables
load_dotenv()

# Get bot token
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set")

# Create application
application = Application.builder().token(BOT_TOKEN).build()

# Add handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("stop", stop))

# Add conversation handler
conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={},
    fallbacks=[CommandHandler("stop", stop)],
)
application.add_handler(conv_handler)

# Add message handlers
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message_response))
application.add_handler(MessageHandler(filters.CONTACT, handle_contact_shared))

# Add callback query handler
application.add_handler(CallbackQueryHandler(handle_callback_query))

print("✅ Gomida Games Bot setup complete!")
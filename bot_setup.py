import os
import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ConversationHandler
from dotenv import load_dotenv
from commands import start, stop
from callbacks import handle_message_response, handle_contact_shared, handle_callback_query

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get bot token
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN environment variable is not set")

print(f"✅ Bot token loaded: {BOT_TOKEN[:10]}...")

# Create application
try:
    application = Application.builder().token(BOT_TOKEN).build()
    print("✅ Application created successfully")
except Exception as e:
    print(f"❌ Failed to create application: {e}")
    raise

# Add handlers
try:
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
    
    print("✅ All handlers added successfully")
except Exception as e:
    print(f"❌ Error adding handlers: {e}")
    raise

print("✅ Gomida Games Bot setup complete!")
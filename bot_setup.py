# bot_setup.py
import os
import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ConversationHandler
from dotenv import load_dotenv
from commands import groupid, notify_test, start, stop, refresh, WAITING_MESSAGE, notify_start, notifynew_start, notifyall_start, notify_receive, notify_cancel, notify_confirm_callback
from callbacks import handle_message_response, handle_contact_shared, handle_callback_query

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN environment variable is not set")

print(f"✅ Bot token loaded: {BOT_TOKEN[:10]}...")

# Create Telegram application
application = Application.builder().token(BOT_TOKEN).build()

# Conversation for admin /notify command
notify_conv = ConversationHandler(
    entry_points=[
        CommandHandler("notify", notify_start),
        CommandHandler("notifynew", notifynew_start),
        CommandHandler("notifyall", notifyall_start),
    ],
    states={
        WAITING_MESSAGE: [
            # Accept text or photo
            MessageHandler((filters.TEXT & ~filters.COMMAND) | filters.PHOTO, notify_receive)
        ]
    },
    fallbacks=[CommandHandler("cancel", notify_cancel), CommandHandler("stop", stop)],
)
application.add_handler(notify_conv)

# Add conversation handler for /start
conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={},
    fallbacks=[CommandHandler("stop", stop)],
)
application.add_handler(conv_handler)

# Add command handlers
application.add_handler(CommandHandler("stop", stop))
application.add_handler(CommandHandler("refresh", refresh))
application.add_handler(CommandHandler("notifytest", notify_test))

# Add callback query handlers (specific patterns first)
application.add_handler(CallbackQueryHandler(notify_confirm_callback, pattern=r"^notify_confirm_"))
application.add_handler(CallbackQueryHandler(handle_callback_query))

# Add message handlers (least specific - last)
application.add_handler(MessageHandler(filters.CONTACT, handle_contact_shared))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message_response))

print("✅ Gomida Games Bot setup complete!")
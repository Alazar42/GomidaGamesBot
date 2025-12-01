from telegram.ext import Updater, ApplicationBuilder, CommandHandler, filters, MessageHandler, ConversationHandler, CallbackQueryHandler
from dotenv import load_dotenv
from os import getenv
from commands import start, stop
from callbacks import handle_callback_query, handle_message_response, handle_contact_shared

load_dotenv()

TOKEN = str(getenv("BOT_TOKEN"))

app = ApplicationBuilder().token(TOKEN).build()
# Other handlers
response_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message_response)
contact_handler = MessageHandler(filters.CONTACT, handle_contact_shared)

conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={},
        fallbacks=[CommandHandler("stop", stop)],
    )
    
# Adding handlers
app.add_handler(response_handler)
app.add_handler(contact_handler)
app.add_handler(conv_handler)
app.add_handler(CallbackQueryHandler(handle_callback_query))

app.add_handler(CommandHandler("start", start))

print("Gomida Games Bot is Running ✔")
app.run_polling()
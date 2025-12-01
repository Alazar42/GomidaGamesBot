from telegram import Update
from telegram.ext import ContextTypes, CallbackContext, ConversationHandler
from .buttons import initial_menu_markup, unlocked_menu_markup
from .callbacks import handle_message_response

async def start(update: Update, context: CallbackContext) -> None:
    # Clear any existing contact status when starting
    context.user_data.clear()
    
    # Check if user already shared contact
    if context.user_data.get('contact_shared'):
        await update.message.reply_text(
            "Welcome back to Gomida Games! 🎮", 
            reply_markup=unlocked_menu_markup
        )
    else:
        await update.message.reply_text(
            "Welcome to Gomida Games! 📱\n\n"
            "To unlock games, please share your contact:",
            reply_markup=initial_menu_markup
        )

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Clear all stored user data
    context.user_data.clear()
    
    # Optionally send a farewell message
    await update.message.reply_text("Gomida Games has been stopped! To start again, type /start.")
    
    # If using ConversationHandler, end the conversation
    return ConversationHandler.END
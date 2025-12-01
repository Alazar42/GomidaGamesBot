# commands.py
from telegram import Update
from telegram.ext import ContextTypes, CallbackContext, ConversationHandler
from buttons import regular_menu_markup, unlocked_menu_markup, initial_menu_markup
from api_client import create_user, get_user_by_tg_id
import logging

logger = logging.getLogger(__name__)

async def start(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    
    try:
        # Check if user already exists in our system
        existing_user = await get_user_by_tg_id(user.id)
        
        if existing_user:
            logger.info(f"✅ Existing user found: {user.id} - {user.username}")
            # User exists, check if they have phone
            if existing_user.get('phone'):
                context.user_data['api_user'] = existing_user
                context.user_data['contact_shared'] = True
                await update.message.reply_text(
                    "Welcome back to Gomida Games! 🎮", 
                    reply_markup=unlocked_menu_markup
                )
            else:
                context.user_data['api_user'] = existing_user
                context.user_data['contact_shared'] = False
                await update.message.reply_text(
                    f"Welcome back {user.first_name}! 👋\n\n"
                    "Would you like to share your contact for a better experience?",
                    reply_markup=initial_menu_markup
                )
        else:
            # Create new user without phone
            logger.info(f"🆕 Creating new user: {user.id} - {user.username}")
            user_data = {
                "id": user.id,  # Using Telegram ID as user ID
                "username": user.username or f"user_{user.id}",
                "phone": "",  # Empty phone initially
                "score": 0,
                "flags_level": 1,
                "maps_level": 1,
                "attires_level": 1,
                "flags_stars": {},
                "maps_stars": {},
                "attires_stars": {}
            }
            
            # Create user via API
            api_response = await create_user(user_data)
            
            if api_response:
                context.user_data['api_user'] = api_response
                context.user_data['contact_shared'] = False
                await update.message.reply_text(
                    f"Welcome to Gomida Games, {user.first_name}! 🎉\n\n"
                    "Would you like to share your contact for a better experience?",
                    reply_markup=initial_menu_markup
                )
            else:
                # Fallback if API fails - use local storage only
                logger.warning(f"⚠️ API failed for user {user.id}, using local storage")
                context.user_data['api_user'] = user_data
                context.user_data['contact_shared'] = False
                await update.message.reply_text(
                    f"Welcome to Gomida Games, {user.first_name}! 🎮\n\n"
                    "Note: Some features might be limited due to server connection.",
                    reply_markup=regular_menu_markup
                )
                
    except Exception as e:
        logger.error(f"❌ Error in start command for user {user.id}: {e}")
        await update.message.reply_text(
            "Welcome to Gomida Games! 🎮\n\n"
            "There was an issue connecting to our servers.\n"
            "You can still use basic features.",
            reply_markup=regular_menu_markup
        )

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    context.user_data.clear()
    logger.info(f"🛑 User {user_id} stopped the bot")
    await update.message.reply_text(
        "Gomida Games has been stopped! To start again, type /start."
    )
    return ConversationHandler.END

async def refresh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Refresh user data from backend"""
    user = update.effective_user
    
    try:
        existing_user = await get_user_by_tg_id(user.id)
        
        if existing_user:
            context.user_data['api_user'] = existing_user
            context.user_data['contact_shared'] = bool(existing_user.get('phone'))
            await update.message.reply_text(
                "✅ Your data has been refreshed from the server!"
            )
        else:
            await update.message.reply_text(
                "❌ User not found in server. Please use /start to create an account."
            )
    except Exception as e:
        logger.error(f"❌ Error refreshing user {user.id}: {e}")
        await update.message.reply_text(
            "❌ Could not refresh data. Please try again later."
        )
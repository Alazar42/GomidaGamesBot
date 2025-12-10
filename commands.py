# commands.py
from telegram import Update
from telegram.ext import ContextTypes, CallbackContext, ConversationHandler
from buttons import regular_menu_markup, unlocked_menu_markup, initial_menu_markup
from api_client import create_user, get_user_by_tg_id, update_user
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)

# Get admin Telegram Group ID from environment
def get_admin_group_id():
    """Get admin Telegram Group ID from environment variable"""
    group_id_str = os.getenv("ADMIN_GROUP_ID", "")
    if group_id_str:
        try:
            return int(group_id_str.strip())
        except ValueError as e:
            logger.error(f"❌ Invalid admin group ID: {e}")
            return None
    return None

async def send_registration_notification(bot, new_user: dict, context: dict = None):
    """
    Send registration notifications to admin Telegram group
    
    Args:
        bot: Telegram Bot instance
        new_user: Complete user dictionary from API
        context: Optional context dict with additional info
    """
    admin_group_id = get_admin_group_id()
    
    if not admin_group_id:
        logger.warning("⚠️ No admin group ID configured for notifications")
        return
    
    # Extract user information
    user_id = new_user.get('id', 'N/A')
    username = new_user.get('username', '')
    phone = new_user.get('phone', '')
    
    
    # Get username for display
    display_username = f"@{username}" if username else "No username"
    
    # Determine if this is a new registration or contact update
    event_type = "New Registration"
    if context and context.get('contact_shared'):
        event_type = "Contact Shared"
    if context and context.get('returning_user'):
        event_type = "Returning User"
    if context and context.get('test'):
        event_type = "TEST - " + event_type
    
    # Current time
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Format the notification message for Telegram group
    message = (
        f"🎮 *{event_type.upper()}!*\n\n"
        f"👤 *User Information:*\n"
        f"• *ID:* `{user_id}`\n"
        f"• *Username:* {display_username}\n"
        f"• *Phone:* `{phone if phone else 'Not shared yet'}`\n"
        f"• *Event:* {event_type}\n"
        f"• *Time:* {current_time}\n\n"
    )
    
    # Add additional context if available
    if context:
        if context.get('contact_shared'):
            message += "✅ *Contact has been shared!*\n"
        if context.get('api_response'):
            message += "📊 *User saved to database*\n"
        if context.get('returning_user'):
            message += "↩️ *Returning user*\n"
    
    message += "\n#NewUser #Registration #GomidaGames"
    
    try:
        # Send message to admin group
        sent_message = await bot.send_message(
            chat_id=admin_group_id,
            text=message,
            parse_mode='Markdown'
        )
        logger.info(f"✅ Notification sent to admin group ID: {admin_group_id}")
        
        # Also send a separate message with user details for easy copying
        user_details = (
            f"📋 *User Details for Records:*\n\n"
            f"```\n"
            f"User ID: {user_id}\n"
            f"Username: {username or 'No username'}\n"
            f"Phone: {phone if phone else 'Not shared'}\n"
            f"Registered: {current_time}\n"
            f"Event: {event_type}\n"
            f"```\n\n"
            f"#UserID{user_id}"
        )
        
        await bot.send_message(
            chat_id=admin_group_id,
            text=user_details,
            parse_mode='Markdown'
        )
        
        return sent_message
        
    except Exception as e:
        logger.error(f"❌ Failed to send notification to group {admin_group_id}: {e}")
        # Fallback: log the notification
        logger.info(f"📨 Would have sent to group {admin_group_id}: {message}")
        return None

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
                
                # Update user with current Telegram info (in case username changed)
                update_data = {
                    "id": user.id,
                    "username": user.username or f"user_{user.id}",
                    "phone": existing_user.get('phone', ''),
                    "score": existing_user.get('score', 0),
                    "flags_level": existing_user.get('flags_level', 1),
                    "maps_level": existing_user.get('maps_level', 1),
                    "attires_level": existing_user.get('attires_level', 1),
                    "flags_stars": existing_user.get('flags_stars', {}),
                    "maps_stars": existing_user.get('maps_stars', {}),
                    "attires_stars": existing_user.get('attires_stars', {})
                }
                
                # Update user in backend
                updated_user = await update_user(user.id, update_data)
                if updated_user:
                    context.user_data['api_user'] = updated_user
                
                # Notify group about returning user
                await send_registration_notification(
                    bot=context.bot,
                    new_user=context.user_data['api_user'],
                    context={'contact_shared': True, 'returning_user': True, 'api_response': True}
                )
                
                await update.message.reply_text(
                    "Welcome back to Gomida Games! 🎮", 
                    reply_markup=unlocked_menu_markup
                )
            else:
                context.user_data['api_user'] = existing_user
                context.user_data['contact_shared'] = False
                await update.message.reply_text(
                    f"Welcome back {user.username or 'there'}! 👋\n\n"
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
            api_success = bool(api_response)
            
            if api_response:
                context.user_data['api_user'] = api_response
                context.user_data['contact_shared'] = False
                
                # ✅ Send registration notification to admin group
                await send_registration_notification(
                    bot=context.bot,
                    new_user=api_response,
                    context={'contact_shared': False, 'api_response': True}
                )
                
                welcome_message = f"Welcome to Gomida Games"
                if user.username:
                    welcome_message += f", {user.username}"
                welcome_message += "! 🎉\n\nWould you like to share your contact for a better experience?"
                
                await update.message.reply_text(
                    welcome_message,
                    reply_markup=initial_menu_markup
                )
            else:
                # Fallback if API fails - use local storage only
                logger.warning(f"⚠️ API failed for user {user.id}, using local storage")
                context.user_data['api_user'] = user_data
                context.user_data['contact_shared'] = False
                
                # ✅ Still send notification even if API fails
                await send_registration_notification(
                    bot=context.bot,
                    new_user=user_data,
                    context={'contact_shared': False, 'api_response': False}
                )
                
                welcome_message = f"Welcome to Gomida Games"
                if user.username:
                    welcome_message += f", {user.username}"
                welcome_message += "! 🎮\n\nNote: Some features might be limited due to server connection."
                
                await update.message.reply_text(
                    welcome_message,
                    reply_markup=regular_menu_markup
                )
                
    except Exception as e:
        logger.error(f"❌ Error in start command for user {user.id}: {e}")
        welcome_message = "Welcome to Gomida Games! 🎮\n\nThere was an issue connecting to our servers.\nYou can still use basic features."
        
        await update.message.reply_text(
            welcome_message,
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
            
            # Notify about refresh (optional)
            # await send_registration_notification(
            #     bot=context.bot,
            #     new_user=existing_user,
            #     context={'contact_shared': bool(existing_user.get('phone')), 'refresh': True}
            # )
            
        else:
            await update.message.reply_text(
                "❌ User not found in server. Please use /start to create an account."
            )
    except Exception as e:
        logger.error(f"❌ Error refreshing user {user.id}: {e}")
        await update.message.reply_text(
            "❌ Could not refresh data. Please try again later."
        )

# New command for admins to test group notifications
async def notify_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Test notification system in admin group"""
    user = update.effective_user
    admin_group_id = get_admin_group_id()
    
    if not admin_group_id:
        await update.message.reply_text("❌ No admin group ID configured. Set ADMIN_GROUP_ID in .env")
        return
    
    # Create test user data with different scenarios
    test_scenarios = [
        {
            "name": "Full info user",
            "data": {
                "id": 999999991,
                "username": "test_user_full",
                "phone": "+251911223344",
                "score": 1000,
                "flags_level": 5,
                "maps_level": 3,
                "attires_level": 2
            }
        },
        {
            "name": "First name only",
            "data": {
                "id": 999999992,
                "username": "test_firstname",
                "phone": "",
                "score": 500,
                "flags_level": 2,
                "maps_level": 1,
                "attires_level": 1
            }
        },
        {
            "name": "No name user",
            "data": {
                "id": 999999993,
                "username": "test_noname",
                "phone": "+251955667788",
                "score": 250,
                "flags_level": 1,
                "maps_level": 1,
                "attires_level": 1
            }
        }
    ]
    
    await update.message.reply_text(
        f"📱 Testing group notification system...\n"
        f"• Admin Group ID: {admin_group_id}\n"
        f"• Test user: @{user.username or 'No Username'}\n\n"
        "Sending test notifications to admin group..."
    )
    
    # Send test notifications
    for i, scenario in enumerate(test_scenarios, 1):
        await send_registration_notification(
            bot=context.bot,
            new_user=scenario['data'],
            context={'contact_shared': bool(scenario['data']['phone']), 'api_response': True, 'test': True}
        )
        logger.info(f"✅ Test scenario {i} sent: {scenario['name']}")
    
    await update.message.reply_text("✅ All test notifications sent to admin group!")

# Command to get group ID
async def groupid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get the current group ID (useful for setting up admin group)"""
    chat = update.effective_chat
    
    if chat.type in ['group', 'supergroup']:
        message = (
            f"📋 *Group Information:*\n\n"
            f"• *Group ID:* `{chat.id}`\n"
            f"• *Group Title:* {chat.title}\n"
            f"• *Group Type:* {chat.type}\n\n"
            f"🔧 *Add this ID to ADMIN_GROUP_ID in .env:*\n"
            f"`ADMIN_GROUP_ID={chat.id}`"
        )
        await update.message.reply_text(message, parse_mode='Markdown')
    else:
        await update.message.reply_text(
            "⚠️ This command only works in groups or supergroups.\n\n"
            "To set up admin notifications:\n"
            "1. Add the bot to your admin group\n"
            "2. Make the bot an admin in the group\n"
            "3. Run /groupid in the group to get the ID\n"
            "4. Add that ID to ADMIN_GROUP_ID in .env file"
        )

# Command to get user ID
async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the user's Telegram ID"""
    user = update.effective_user
    
    # Get current user's data from context
    api_user = context.user_data.get('api_user', {})
    phone = api_user.get('phone', 'Not shared')
    
    
    message = (
        f"👤 *Your Telegram Info:*\n\n"
        f"• *ID:* `{user.id}`\n"
        f"• *Username:* @{user.username if user.username else 'No username'}\n"
        f"• *Phone:* `{phone}`\n\n"
        f"🔧 *This ID can be added to ADMIN_USER_IDS if needed*"
    )
    
    await update.message.reply_text(message, parse_mode='Markdown')
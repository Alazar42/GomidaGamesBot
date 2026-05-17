# commands.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ContextTypes, CallbackContext, ConversationHandler
from buttons import regular_menu_markup, unlocked_menu_markup, initial_menu_markup
from api_client import create_user, get_user_by_tg_id, update_user
from games import games
from urllib.parse import quote
from functools import wraps
import html
import logging
import os
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from notifications import add_subscriber, remove_subscriber, broadcast_notification
import html

logger = logging.getLogger(__name__)


async def ensure_user_registered_silently(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ensure a Telegram user exists in DB and subscribers without sending chat noise."""
    user = update.effective_user
    if not user:
        return None

    try:
        existing_user = context.user_data.get('api_user') if context and context.user_data else None
    except Exception:
        existing_user = None

    try:
        if not existing_user:
            existing_user = await get_user_by_tg_id(user.id)

        if not existing_user:
            user_data = {
                "id": user.id,
                "username": user.username or f"user_{user.id}",
                "phone": "",
            }
            created_user = await create_user(user_data)
            existing_user = created_user or user_data

        context.user_data['api_user'] = existing_user
        context.user_data['contact_shared'] = bool(existing_user.get('phone'))
    except Exception:
        # Keep command execution resilient even if backend is temporarily unavailable.
        logger.exception("Silent registration check failed for user %s", user.id)

    try:
        add_subscriber(user.id)
    except Exception:
        logger.exception("Failed to add subscriber during silent registration")

    return context.user_data.get('api_user')


def require_silent_registration(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        await ensure_user_registered_silently(update, context)
        return await func(update, context, *args, **kwargs)

    return wrapper

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

    # Capture the start payload from "https://t.me/<bot>?start=ref_<inviter_id>".
    # Unity's TelegramManager builds invite URLs with "ref_<telegram_user_id>"; we
    # forward the value to the game URL as ?startapp=ref_<inviter_id> so Unity's
    # WebGL bridge can read it from window.location.search and register the invite
    # in Supabase. Emit a Play button with the ref baked in BEFORE any other reply
    # so we don't depend on in-memory user_data surviving across webhook requests
    # (Vercel serverless can cold-start between /start and the user tapping Play).
    invite_ref = None
    if context.args:
        raw_payload = context.args[0].strip() if context.args[0] else ""
        if raw_payload.lower().startswith("ref_"):
            inviter_id = raw_payload[4:].strip()
            if inviter_id and inviter_id != str(user.id):
                invite_ref = f"ref_{inviter_id}"
                logger.info(f"📨 Captured invite ref for user {user.id}: {invite_ref}")

    if invite_ref:
        try:
            for game in games:
                game_url = game["url"]
                separator = "&" if "?" in game_url else "?"
                game_url = f"{game_url}{separator}startapp={quote(invite_ref)}"

                title = game.get("title") or game["name"]
                description = game.get("description") or "Play now inside Telegram."
                button_text = game.get("button_text") or f"Play {game['name']}"
                caption = (
                    "🎉 <b>You were invited to play!</b>\n\n"
                    f"<b>{html.escape(title)}</b>\n"
                    f"{html.escape(description)}\n\n"
                    "Tap the button below to launch the game and credit your inviter."
                )
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton(button_text, web_app=WebAppInfo(url=game_url))]
                ])
                await update.message.reply_html(caption, reply_markup=keyboard)
        except Exception as e:
            logger.error(f"❌ Failed to send invite play button: {e}")

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
                try:
                    add_subscriber(user.id)
                except Exception:
                    logger.exception("Failed to add subscriber on start")
            else:
                context.user_data['api_user'] = existing_user
                context.user_data['contact_shared'] = False
                await update.message.reply_text(
                    f"Welcome back {user.username or 'there'}! 👋\n\n"
                    "Would you like to share your contact for a better experience?",
                    reply_markup=initial_menu_markup
                )
                try:
                    add_subscriber(user.id)
                except Exception:
                    logger.exception("Failed to add subscriber on start")
        else:
            # Create new user without phone
            logger.info(f"🆕 Creating new user: {user.id} - {user.username}")
            user_data = {
                "id": user.id,  # Using Telegram ID as user ID
                "username": user.username or f"user_{user.id}",
                "phone": "",  # Empty phone initially
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
                try:
                    add_subscriber(user.id)
                except Exception:
                    logger.exception("Failed to add subscriber on start")
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
                try:
                    add_subscriber(user.id)
                except Exception:
                    logger.exception("Failed to add subscriber on start")
                
    except Exception as e:
        logger.error(f"❌ Error in start command for user {user.id}: {e}")
        welcome_message = "Welcome to Gomida Games! 🎮\n\nThere was an issue connecting to our servers.\nYou can still use basic features."
        
        await update.message.reply_text(
            welcome_message,
            reply_markup=regular_menu_markup
        )

@require_silent_registration
async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"🛑 User {user_id} stopped the bot")
    try:
        remove_subscriber(user_id)
    except Exception:
        logger.exception("Failed to remove subscriber on stop")
    context.user_data.clear()
    await update.message.reply_text(
        "Gomida Games has been stopped! To start again, type /start."
    )
    return ConversationHandler.END

@require_silent_registration
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
@require_silent_registration
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
@require_silent_registration
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
@require_silent_registration
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

# Notify conversation states
WAITING_MESSAGE = 1

@require_silent_registration
async def notify_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    # Only allow specific username
    if not user.username or user.username.lower() != 'gomidasolutions':
        await update.message.reply_text("❌ You are not authorized to use /notify.")
        return ConversationHandler.END

    context.user_data['notify_draft'] = {}
    await update.message.reply_text(
        "✉️ Send the notification message you want to broadcast.\n"
        "You may send plain text or send a photo with a caption.\n"
        "Send /cancel to abort."
    )
    return WAITING_MESSAGE

async def notify_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Accept text or photo with caption
    draft = {'text': '', 'photo': None}
    if update.message.photo:
        # Get highest resolution
        file_id = update.message.photo[-1].file_id
        draft['photo'] = file_id
        draft['text'] = update.message.caption or ''
    else:
        draft['text'] = update.message.text or ''

    context.user_data['notify_draft'] = draft

    # Prepare confirmation buttons
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Yes ✅", callback_data="notify_confirm_yes"),
         InlineKeyboardButton("No ❌", callback_data="notify_confirm_no")]
    ])

    # Send preview with buttons
    if draft['photo']:
        await update.message.reply_photo(photo=draft['photo'], caption=f"Preview:\n\n{draft['text']}", reply_markup=keyboard)
    else:
        await update.message.reply_text(f"Preview:\n\n{draft['text']}", reply_markup=keyboard)

    return ConversationHandler.END

@require_silent_registration
async def notify_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Notification cancelled.")
    context.user_data.pop('notify_draft', None)
    return ConversationHandler.END

async def notify_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    draft = context.user_data.get('notify_draft')
    # Helper to safely edit either caption (for photo messages) or text
    async def _edit_message_safe(msg_obj, new_text: str, parse_mode: str = None):
        try:
            # Photo messages must use edit_message_caption
            if getattr(msg_obj, 'photo', None):
                await query.edit_message_caption(caption=new_text, parse_mode=parse_mode)
            else:
                await query.edit_message_text(new_text, parse_mode=parse_mode)
        except Exception:
            # Last resort: answer callback with alert
            try:
                await query.answer(text=new_text, show_alert=True)
            except Exception:
                logger.exception("Failed to deliver confirmation message")

    if not draft:
        await _edit_message_safe(query.message, "⚠️ No draft found or session expired.")
        return

    if data == 'notify_confirm_no':
        await _edit_message_safe(query.message, "❌ Notification cancelled.")
        context.user_data.pop('notify_draft', None)
        return

    # Confirm yes -> broadcast
    if data == 'notify_confirm_yes':
        text = draft.get('text', '')
        photo = draft.get('photo')
        try:
            # Show loading state immediately
            loading_msg = "⏳ Broadcasting to all subscribers...\n\n🔄 This may take a moment..."
            await _edit_message_safe(query.message, loading_msg)
            
            # Perform the broadcast
            sent = await broadcast_notification(bot=context.bot, text=text, photo_file_id=photo, parse_mode='Markdown')
            
            if sent == 0:
                msg = (
                    "⚠️ Notification sent to 0 subscribers.\n\n"
                    "This may happen because:\n"
                    "• Backend database is cold-starting (free tier)\n"
                    "• No users in the system yet\n\n"
                    "💡 Tip: Wait 30-60 seconds and try again."
                )
            else:
                msg = f"✅ Notification sent to {sent} subscribers."
            await _edit_message_safe(query.message, msg)
        except Exception as e:
            await _edit_message_safe(query.message, f"❌ Failed to broadcast: {e}")
        finally:
            context.user_data.pop('notify_draft', None)
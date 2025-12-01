# callbacks.py
from telegram import Update
from telegram.ext import CallbackContext
from docs import TERMS_AND_SERVICES
from games import games
from urllib.parse import quote
from buttons import unlocked_menu_markup, initial_menu_markup, regular_menu_markup
from api_client import update_user, create_user, get_leaderboard, get_user_by_tg_id
import html
import logging

logger = logging.getLogger(__name__)

async def ensure_user_exists(context: CallbackContext, user) -> bool:
    """Ensure user exists in context and backend"""
    if 'api_user' not in context.user_data:
        try:
            # Try to get existing user from backend
            existing_user = await get_user_by_tg_id(user.id)
            
            if existing_user:
                context.user_data['api_user'] = existing_user
                context.user_data['contact_shared'] = bool(existing_user.get('phone'))
                return True
            else:
                # Create new user
                user_data = {
                    "id": user.id,
                    "username": user.username or f"user_{user.id}",
                    "phone": "",
                    "score": 0,
                    "flags_level": 1,
                    "maps_level": 1,
                    "attires_level": 1,
                    "flags_stars": {},
                    "maps_stars": {},
                    "attires_stars": {}
                }
                created_user = await create_user(user_data)
                
                if created_user:
                    context.user_data['api_user'] = created_user
                    context.user_data['contact_shared'] = False
                    return True
                else:
                    # Fallback to local data
                    context.user_data['api_user'] = user_data
                    context.user_data['contact_shared'] = False
                    return True
        except Exception as e:
            logger.error(f"❌ Error ensuring user exists {user.id}: {e}")
            return False
    return True

async def handle_message_response(update: Update, context: CallbackContext):
    text = update.message.text
    user = update.effective_user
    
    # Ensure user exists
    if not await ensure_user_exists(context, user):
        await update.message.reply_text(
            "❌ There was an issue with your account. Please try /start again.",
            reply_markup=regular_menu_markup
        )
        return
    
    api_user = context.user_data.get('api_user', {})
    contact_shared = context.user_data.get('contact_shared', False)
    
    if text == "👤 Account":
        phone = api_user.get('phone', 'Not shared')
        first_name = user.first_name
        last_name = user.last_name or ''
        username = user.username or "No username"
        score = api_user.get('score', 0)
        flags_level = api_user.get('flags_level', 1)
        maps_level = api_user.get('maps_level', 1)
        attires_level = api_user.get('attires_level', 1)
        
        # Get user's rank from leaderboard
        rank = "N/A"
        try:
            leaderboard_data = await get_leaderboard()
            if leaderboard_data:
                for i, lb_user in enumerate(leaderboard_data, 1):
                    if lb_user.get('id') == user.id:
                        rank = f"#{i}"
                        break
        except Exception as e:
            logger.error(f"❌ Error getting rank for user {user.id}: {e}")
        
        account_info = (
            f"👤 <b>Your Account Info</b>\n\n"
            f"• <b>Name:</b> {html.escape(first_name)} {html.escape(last_name)}\n"
            f"• <b>Username:</b> @{html.escape(username) if username != 'No username' else 'No username'}\n"
            f"• <b>Telegram ID:</b> <code>{user.id}</code>\n"
            f"• <b>Phone:</b> <code>{html.escape(phone) if phone else 'Not shared'}</code>\n"
            f"• <b>Global Rank:</b> {rank}\n"
            f"• <b>Score:</b> {score} points\n"
            f"• <b>Game Levels:</b>\n"
            f"   🚩 Flags: Level {flags_level}\n"
            f"   🗺️ Maps: Level {maps_level}\n"
            f"   👕 Attires: Level {attires_level}\n"
            f"• <b>Contact Shared:</b> {'✅ Yes' if contact_shared else '❌ No'}"
        )
        
        await update.message.reply_html(account_info)
        return
    
    elif text == "🎮 Play":
        # User can always play games
        await update.message.reply_text(
            "🎮 Loading games...\n\n"
            "Tap on any game to start playing!",
            reply_markup=unlocked_menu_markup if contact_shared else regular_menu_markup
        )
        
        # Send each game using Telegram's Game API
        for game in games:
            await update.message.reply_game(game_short_name=game["short_name"])
    
    elif text == "✉️ Invite":
        invite_link = f"https://t.me/{context.bot.username}" if context.bot.username else "https://t.me/adwa1888bot"
        await update.message.reply_text(
            f"📣 Invite your friends to play!\n\n"
            f"Share this link:\n{invite_link}\n\n"
            f"Earn points when your friends join and play!"
        )
    
    elif text == "👥🏅 Refferal Leaderboard":
        await show_leaderboard(update, context)
    
    elif text == "📜Terms & Conditions":
        await update.message.reply_markdown_v2(TERMS_AND_SERVICES)
    
    elif text == "⚙️ Settings":
        settings_text = (
            "⚙️ <b>Settings</b>\n\n"
            "1. <b>Account</b> - View your profile\n"
            "2. <b>Notifications</b> - Coming soon\n"
            "3. <b>Language</b> - Coming soon\n"
            "4. <b>Privacy</b> - Manage your data\n\n"
            "Use the buttons below to navigate."
        )
        await update.message.reply_html(settings_text)
    
    elif text == "Skip Contact":
        # User chooses not to share contact
        context.user_data['contact_shared'] = False
        await update.message.reply_text(
            "✅ No problem! You can still enjoy all our games.\n\n"
            "You can share your contact anytime by tapping /start again.",
            reply_markup=regular_menu_markup
        )
    
    else:
        # If user sends any other text, show appropriate menu
        menu = unlocked_menu_markup if contact_shared else regular_menu_markup
        await update.message.reply_text(
            "What would you like to do?",
            reply_markup=menu
        )

async def show_leaderboard(update: Update, context: CallbackContext):
    """Display the leaderboard from API"""
    user = update.effective_user
    
    # Show loading message
    loading_msg = await update.message.reply_text("🏆 Fetching leaderboard...")
    
    try:
        # Get leaderboard data from API
        leaderboard_data = await get_leaderboard()
        
        if not leaderboard_data:
            await loading_msg.edit_text(
                "❌ Could not load leaderboard at this time.\n"
                "Please try again later."
            )
            return
        
        if len(leaderboard_data) == 0:
            await loading_msg.edit_text(
                "🏆 Leaderboard is empty!\n\n"
                "Be the first to score points by playing games! 🎮"
            )
            return
        
        # Format leaderboard
        leaderboard_text = "<b>🏆 Global Leaderboard</b>\n\n"
        
        # Show top 10 or all if less than 10
        display_count = min(10, len(leaderboard_data))
        
        # Emojis for top positions
        position_emojis = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        
        for i in range(display_count):
            lb_user = leaderboard_data[i]
            username = lb_user.get('username', 'Unknown')
            score = lb_user.get('score', 0)
            
            # Truncate long usernames
            if len(username) > 15:
                username = username[:12] + "..."
            
            # Get appropriate emoji for position
            if i < len(position_emojis):
                position_emoji = position_emojis[i]
            else:
                position_emoji = f"{i+1}."
            
            # Highlight current user
            api_user = context.user_data.get('api_user', {})
            is_current_user = lb_user.get('id') == api_user.get('id')
            
            if is_current_user:
                leaderboard_text += f"{position_emoji} <b>@{username} - {score} pts 👈 YOU</b>\n"
            else:
                leaderboard_text += f"{position_emoji} @{username} - {score} pts\n"
        
        # Add user's own position if not in top 10
        api_user = context.user_data.get('api_user', {})
        if api_user:
            user_id = api_user.get('id')
            user_score = api_user.get('score', 0)
            
            # Find user's position in leaderboard
            user_position = None
            for i, lb_user in enumerate(leaderboard_data):
                if lb_user.get('id') == user_id:
                    user_position = i + 1
                    break
            
            if user_position and user_position > 10:
                leaderboard_text += f"\n<b>Your Position:</b> #{user_position} - {user_score} pts"
            elif user_position is None:
                leaderboard_text += f"\n<b>Your Score:</b> {user_score} pts (not ranked yet)"
        
        # Add footer with refresh option
        leaderboard_text += "\n\nPlay more games to climb the ranks! 🎮\n"
        leaderboard_text += "Leaderboard updates in real-time."
        
        await loading_msg.edit_text(leaderboard_text, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"❌ Error showing leaderboard: {e}")
        await loading_msg.edit_text(
            "❌ Failed to load leaderboard.\n"
            "Please try again in a few moments."
        )

async def handle_contact_shared(update: Update, context: CallbackContext):
    """Handle when user shares their contact"""
    contact = update.message.contact
    user = update.effective_user
    
    logger.info(f"📱 User {user.id} shared contact: {contact.phone_number}")
    
    try:
        # Update user in backend API
        api_user = context.user_data.get('api_user', {})
        user_id = api_user.get('id', user.id)
        
        update_data = {
            "id": user_id,
            "username": api_user.get('username') or user.username or f"user_{user.id}",
            "phone": contact.phone_number,
            "score": api_user.get('score', 0),
            "flags_level": api_user.get('flags_level', 1),
            "maps_level": api_user.get('maps_level', 1),
            "attires_level": api_user.get('attires_level', 1),
            "flags_stars": api_user.get('flags_stars', {}),
            "maps_stars": api_user.get('maps_stars', {}),
            "attires_stars": api_user.get('attires_stars', {})
        }
        
        # Call API to update user
        updated_user = await update_user(user_id, update_data)
        
        if updated_user:
            context.user_data['api_user'] = updated_user
            context.user_data['contact_shared'] = True
            context.user_data['user_phone'] = contact.phone_number
            
            await update.message.reply_text(
                f"✅ Thank you {contact.first_name}!\n\n"
                "Your contact has been saved successfully!\n"
                "You now have access to all features! 🎉",
                reply_markup=unlocked_menu_markup
            )
        else:
            # Fallback if API update fails
            logger.warning(f"⚠️ API update failed for user {user.id}, storing locally")
            api_user['phone'] = contact.phone_number
            context.user_data['contact_shared'] = True
            context.user_data['user_phone'] = contact.phone_number
            
            await update.message.reply_text(
                f"✅ Thank you {contact.first_name}!\n\n"
                "Your contact has been saved!\n"
                "Note: Some features may be limited due to server connection.",
                reply_markup=unlocked_menu_markup
            )
            
    except Exception as e:
        logger.error(f"❌ Error handling contact share for user {user.id}: {e}")
        await update.message.reply_text(
            f"✅ Thank you {contact.first_name}!\n\n"
            "We encountered an issue saving your contact.\n"
            "You can still use the bot, but some features may not work.",
            reply_markup=regular_menu_markup
        )
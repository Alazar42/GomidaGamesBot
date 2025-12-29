# callbacks.py
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from docs import TERMS_AND_SERVICES
from games import games
from urllib.parse import quote
from buttons import unlocked_menu_markup, initial_menu_markup, regular_menu_markup
from api_client import update_user, create_user, get_leaderboard
import html

# Constants for leaderboard pagination
LEADERBOARD_PAGE_SIZE = 15  # Users per page (increased from 10)

async def handle_message_response(update: Update, context: CallbackContext):
    text = update.message.text
    user = update.effective_user
    
    # Check if we're in contact selection mode
    if text in ["📱 Select Contacts", "Cancel"]:
        await handle_contact_selection(update, context)
        return
    
    # Ensure user exists in context
    if 'api_user' not in context.user_data:
        # Try to get existing user or create new one
        from api_client import get_user_by_tg_id, create_user
        existing_user = await get_user_by_tg_id(user.id)
        
        if not existing_user:
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
            existing_user = await create_user(user_data)
        
        if existing_user:
            context.user_data['api_user'] = existing_user
            context.user_data['contact_shared'] = bool(existing_user.get('phone'))
    
    if text == "👤 Account":
        api_user = context.user_data.get('api_user', {})
        
        phone = api_user.get('phone', 'Not shared')
        first_name = user.first_name
        last_name = user.last_name or ''
        username = user.username or "No username"
        score = api_user.get('score', 0)
        flags_level = api_user.get('flags_level', 1)
        maps_level = api_user.get('maps_level', 1)
        attires_level = api_user.get('attires_level', 1)
        
        # Get user's rank if available
        rank = "N/A"
        leaderboard_data = await get_leaderboard()
        if leaderboard_data:
            for i, lb_user in enumerate(leaderboard_data, 1):
                if lb_user.get('id') == user.id:
                    rank = f"#{i}"
                    break
        
        account_info = (
            f"👤 <b>Your Account Info</b>\n\n"
            f"• <b>Name:</b> {html.escape(first_name)} {html.escape(last_name)}\n"
            f"• <b>Username:</b> @{html.escape(username)}\n"
            f"• <b>Phone:</b> <code>{html.escape(phone)}</code>\n"
            f"• <b>Global Rank:</b> {rank}\n"
            f"• <b>Score:</b> {score} points\n"
            f"• <b>Contact Shared:</b> {'✅ Yes' if context.user_data.get('contact_shared') else '❌ No'}"
        )
        
        await update.message.reply_html(account_info)
        return
    
    elif text == "🎮 Play":
        # Check if user has shared contact
        if not context.user_data.get('contact_shared', False):
            await update.message.reply_text(
                "🎮 You can play games without sharing contact!\n"
                "However, sharing contact unlocks additional features.",
                reply_markup=regular_menu_markup
            )
        
        # Send each game using Telegram's Game API
        for game in games:
            await update.message.reply_game(game_short_name=game["short_name"])
    
    elif text == "✉️ Invite":
        # Jump directly to contact sharing
        await jump_to_contact_invite(update, context)
    
    elif text == "👥🏅 Leaderboard":
        # Start with page 1
        await show_leaderboard(update, context, page=1)
    
    elif text == "📜Terms & Conditions":
        await update.message.reply_markdown_v2(TERMS_AND_SERVICES)
    
    elif text == "⚙️ Settings":
        await update.message.reply_text("Settings menu:\n1. Change username\n2. Change notifications\n3. Back")
    
    elif text == "Skip Contact":
        # User chooses not to share contact
        context.user_data['contact_shared'] = False
        await update.message.reply_text(
            "✅ You can still play games! Share contact anytime to unlock additional features.",
            reply_markup=regular_menu_markup
        )
    
    else:
        # If user sends any other text, show appropriate menu
        if context.user_data.get('contact_shared', False):
            await update.message.reply_text(
                "What would you like to do?",
                reply_markup=unlocked_menu_markup
            )
        else:
            await update.message.reply_text(
                "What would you like to do?",
                reply_markup=regular_menu_markup
            )

async def show_leaderboard(update: Update, context: CallbackContext, page: int = 1):
    """Display paginated leaderboard from API"""
    # Show loading message
    loading_msg = await update.message.reply_text("🏆 Fetching leaderboard...")
    
    # Get leaderboard data from API
    leaderboard_data = await get_leaderboard()
    
    if not leaderboard_data:
        await loading_msg.edit_text("❌ Could not load leaderboard. Please try again later.")
        return
    
    if not leaderboard_data:  # Empty list
        await loading_msg.edit_text("🏆 Leaderboard is empty. Be the first to score points!")
        return
    
    total_users = len(leaderboard_data)
    total_pages = (total_users + LEADERBOARD_PAGE_SIZE - 1) // LEADERBOARD_PAGE_SIZE
    
    # Ensure page is within valid range
    page = max(1, min(page, total_pages))
    
    # Calculate start and end indices for current page
    start_idx = (page - 1) * LEADERBOARD_PAGE_SIZE
    end_idx = min(start_idx + LEADERBOARD_PAGE_SIZE, total_users)
    
    # Format leaderboard header
    leaderboard_text = f"<b>🏆 Global Leaderboard</b>\n"
    leaderboard_text += f"<i>Page {page}/{total_pages} • {total_users} players</i>\n\n"
    
    # Emojis for positions
    position_emojis = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    
    for i in range(start_idx, end_idx):
        user = leaderboard_data[i]
        username = user.get('username', 'Unknown')
        score = user.get('score', 0)
        position = i + 1
        
        # Truncate long usernames
        if len(username) > 15:
            username = username[:12] + "..."
        
        # Get appropriate emoji for position
        if position <= 10:
            position_emoji = position_emojis[position - 1]
        else:
            position_emoji = f"{position}."
        
        # Highlight current user
        current_user = context.user_data.get('api_user', {})
        is_current_user = user.get('id') == current_user.get('id')
        
        if is_current_user:
            leaderboard_text += f"{position_emoji} <b>{username} - {score} pts 👈 YOU</b>\n"
        else:
            leaderboard_text += f"{position_emoji} {username} - {score} pts\n"
    
    # Add user's own position if not on current page
    current_user = context.user_data.get('api_user', {})
    if current_user:
        user_id = current_user.get('id')
        user_score = current_user.get('score', 0)
        
        # Find user's position in leaderboard
        user_position = None
        for i, user in enumerate(leaderboard_data):
            if user.get('id') == user_id:
                user_position = i + 1
                break
        
        if user_position and (user_position < start_idx + 1 or user_position > end_idx):
            leaderboard_text += f"\n<b>Your Position:</b> #{user_position} - {user_score} pts"
    
    # Add footer
    leaderboard_text += "\nPlay more games to climb the ranks! 🎮"
    
    # Create pagination buttons
    keyboard = []
    
    # Previous button (only if not on first page)
    if page > 1:
        keyboard.append(InlineKeyboardButton("◀️ Previous", callback_data=f"leaderboard_page_{page-1}"))
    
    # Refresh button
    keyboard.append(InlineKeyboardButton("🔄 Refresh", callback_data=f"leaderboard_page_{page}"))
    
    # Next button (only if not on last page)
    if page < total_pages:
        keyboard.append(InlineKeyboardButton("Next ▶️", callback_data=f"leaderboard_page_{page+1}"))
    
    # Add jump to my position button if user is in leaderboard
    if current_user and user_position:
        keyboard.append(InlineKeyboardButton("📍 My Rank", callback_data=f"leaderboard_jump_{user_position}"))
    
    reply_markup = InlineKeyboardMarkup([keyboard]) if keyboard else None
    
    # Edit the loading message with leaderboard
    await loading_msg.edit_text(leaderboard_text, parse_mode='HTML', reply_markup=reply_markup)

async def jump_to_contact_invite(update: Update, context: CallbackContext):
    """Jump directly to contact selection for inviting"""
    # Create a direct share link
    bot_username = context.bot.username
    invitation_text = "🎮 Let's play at Gomida House of Chewata!\n\nJoin me and let's have fun together!"
    bot_link = f"https://t.me/{bot_username}"
    
    # Create share URL that opens Telegram's sharing interface
    share_url = f"https://t.me/share/url?url={quote(bot_link)}&text={quote(invitation_text)}"
    
    # Create a simple keyboard with share button
    keyboard = [
        [InlineKeyboardButton("📱 Select Contacts", url=share_url)],
        [InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "📤 <b>Invite Friends to Play!</b>\n\n"
        "Tap the button below to select friends from your contacts and send them an invitation!\n\n"
        "🎁 <b>Bonus:</b> Earn extra points for each friend who joins!",
        parse_mode='HTML',
        reply_markup=reply_markup
    )

async def request_invite_contacts(update: Update, context: CallbackContext):
    """Request user to select contacts for invitation"""
    # Create contact selection keyboard
    contact_button = KeyboardButton("📱 Select Contacts", request_contact=False)
    
    keyboard = [[contact_button], ["Cancel"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    await update.message.reply_text(
        "📱 <b>Invite Friends</b>\n\n"
        "Tap the button below to select friends from your contacts:",
        parse_mode='HTML',
        reply_markup=reply_markup
    )

async def handle_contact_selection(update: Update, context: CallbackContext):
    """Handle contact selection for invitations"""
    text = update.message.text
    
    if text == "📱 Select Contacts":
        # Create shareable link with invitation message
        bot_username = context.bot.username
        invitation_text = "🎮 Let's play at Gomida House of Chewata!\n\nJoin me and let's have fun together!"
        bot_link = f"https://t.me/{bot_username}"
        
        # Create a deep link with invitation message
        share_url = f"https://t.me/share/url?url={quote(bot_link)}&text={quote(invitation_text)}"
        
        # Send the share link directly
        await update.message.reply_text(
            f"📤 <b>Ready to Invite!</b>\n\n"
            f"👉 <a href='{share_url}'>Tap here to select friends</a>\n\n"
            f"<b>Message that will be sent:</b>\n"
            f"<code>{invitation_text}\n\n{bot_link}</code>\n\n"
            f"🎮 <b>Earn bonus points for each friend who joins!</b>",
            parse_mode='HTML',
            disable_web_page_preview=True
        )
        
        # Return to main menu after a short delay
        if context.user_data.get('contact_shared', False):
            await update.message.reply_text(
                "What would you like to do next?",
                reply_markup=unlocked_menu_markup
            )
        else:
            await update.message.reply_text(
                "What would you like to do next?",
                reply_markup=regular_menu_markup
            )
    
    elif text == "Cancel":
        # Return to main menu
        if context.user_data.get('contact_shared', False):
            await update.message.reply_text(
                "Invitation cancelled.",
                reply_markup=unlocked_menu_markup
            )
        else:
            await update.message.reply_text(
                "Invitation cancelled.",
                reply_markup=regular_menu_markup
            )

from commands import send_registration_notification

async def handle_contact_shared(update: Update, context: CallbackContext):
    """Handle when user shares their contact"""
    contact = update.message.contact
    user = update.effective_user
    
    # Update user data in context
    context.user_data['contact_shared'] = True
    context.user_data['user_phone'] = contact.phone_number
    
    # Update user in backend API
    api_user = context.user_data.get('api_user', {})
    user_id = api_user.get('id', user.id)
    
    update_data = {
        "id": user_id,
        "username": api_user.get('username') or user.username or f"user_{user.id}",
        "first_name": user.first_name or "",
        "last_name": user.last_name or "",
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
    api_success = bool(updated_user)
    
    if updated_user:
        context.user_data['api_user'] = updated_user
    else:
        # Fallback: use update_data if API failed
        context.user_data['api_user'] = update_data
    
    # ✅ Send notification to admin group about contact update
    await send_registration_notification(
        bot=context.bot,
        new_user=context.user_data['api_user'],
        context={'contact_shared': True, 'api_response': api_success}
    )
    
    await update.message.reply_text(
        f"✅ Thank you {contact.first_name}!\n\n"
        "Your contact has been saved successfully!\n"
        "You now have access to all features!",
        reply_markup=unlocked_menu_markup
    )

async def handle_callback_query(update: Update, context: CallbackContext):
    """Handle callback queries for games, leaderboard pagination, and back to menu"""
    query = update.callback_query
    # Do not acknowledge immediately so we can answer with a URL later (query.answer(url=...)).
    # We'll answer the callback in each branch as appropriate.
    
    # Check if it's a back to menu callback
    if query.data == "back_to_menu":
        if context.user_data.get('contact_shared', False):
            await query.edit_message_text(
                "Returning to main menu...",
                reply_markup=unlocked_menu_markup
            )
        else:
            await query.edit_message_text(
                "Returning to main menu...",
                reply_markup=regular_menu_markup
            )
        # Acknowledge the callback to remove the loading state
        await query.answer()
        return
    
    # Check if it's a leaderboard pagination callback
    if query.data and query.data.startswith("leaderboard_"):
        await handle_leaderboard_callback(update, context)
        return
    
    # For Telegram Game API, the callback contains game_short_name
    if query.game_short_name:
        # Find the game in your games list
        game_data = next((g for g in games if g["short_name"] == query.game_short_name), None)
        
        if game_data:
            # Get user information
            user = update.effective_user
            
            # Ensure user exists in context
            if 'api_user' not in context.user_data:
                # Create or get user
                from api_client import get_user_by_tg_id, create_user
                existing_user = await get_user_by_tg_id(user.id)
                
                if not existing_user:
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
                    existing_user = await create_user(user_data)
                
                if existing_user:
                    context.user_data['api_user'] = existing_user
                    context.user_data['contact_shared'] = bool(existing_user.get('phone'))
            
            # Create URL parameters with user data
            api_user = context.user_data.get('api_user', {})
            user_params = {
                'tg_user_id': str(user.id),
                'tg_first_name': user.first_name or '',
                'tg_last_name': user.last_name or '',
                'tg_username': user.username or '',
                'tg_language': user.language_code or 'en',
                'user_score': str(api_user.get('score', 0)),
                'user_id': str(api_user.get('id', user.id)),
            }
            
            # Add game progress data
            user_params['flags_level'] = str(api_user.get('flags_level', 1))
            user_params['maps_level'] = str(api_user.get('maps_level', 1))
            user_params['attires_level'] = str(api_user.get('attires_level', 1))
            
            # Add phone if available
            if api_user.get('phone'):
                user_phone = api_user['phone']
                print(f"📱 Sending phone to game: {user_phone}")
                user_params['phone'] = user_phone
            
            # Build query string (only include non-empty values)
            query_parts = []
            for key, value in user_params.items():
                if value:  # Skip empty values
                    query_parts.append(f"{key}={quote(str(value))}")
            
            # Add game identifier
            query_parts.append(f"game={game_data['short_name']}")
            
            # Build the final URL
            if query_parts:
                game_url = f"{game_data['url']}?{'&'.join(query_parts)}"
            else:
                game_url = game_data['url']
            
            # Answer the callback query with the game URL
            print("Answered game callback with URL:", game_url)
            await query.answer(url=game_url)
        else:
            await query.answer(text="Game not found!", show_alert=True)
            print("No game data found for short name:", query.game_short_name)
    else:
        # Handle other callback queries if needed
        await query.answer()
        print("Unhandled callback query data:", query.data)

async def handle_leaderboard_callback(update: Update, context: CallbackContext):
    """Handle leaderboard pagination callbacks"""
    query = update.callback_query
    data = query.data
    
    if data.startswith("leaderboard_page_"):
        # Extract page number from callback data
        try:
            page = int(data.split("_")[-1])
            await show_leaderboard_callback(query, context, page)
            # Acknowledge the callback after editing the leaderboard
            await query.answer()
        except (ValueError, IndexError):
            await query.answer("Invalid page number!", show_alert=True)
    
    elif data.startswith("leaderboard_jump_"):
        # Jump to page containing user's position
        try:
            position = int(data.split("_")[-1])
            page = ((position - 1) // LEADERBOARD_PAGE_SIZE) + 1
            await show_leaderboard_callback(query, context, page)
            # Acknowledge the callback after editing the leaderboard
            await query.answer()
        except (ValueError, IndexError):
            await query.answer("Could not find your position!", show_alert=True)

async def show_leaderboard_callback(query, context: CallbackContext, page: int = 1):
    """Update leaderboard message for callback queries"""
    # Get leaderboard data from API
    leaderboard_data = await get_leaderboard()
    
    if not leaderboard_data or not leaderboard_data:
        await query.edit_message_text("❌ Could not load leaderboard. Please try again later.")
        return
    
    total_users = len(leaderboard_data)
    total_pages = (total_users + LEADERBOARD_PAGE_SIZE - 1) // LEADERBOARD_PAGE_SIZE
    
    # Ensure page is within valid range
    page = max(1, min(page, total_pages))
    
    # Calculate start and end indices for current page
    start_idx = (page - 1) * LEADERBOARD_PAGE_SIZE
    end_idx = min(start_idx + LEADERBOARD_PAGE_SIZE, total_users)
    
    # Format leaderboard header
    leaderboard_text = f"<b>🏆 Global Leaderboard</b>\n"
    leaderboard_text += f"<i>Page {page}/{total_pages} • {total_users} players</i>\n\n"
    
    # Emojis for positions
    position_emojis = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    
    for i in range(start_idx, end_idx):
        user = leaderboard_data[i]
        username = user.get('username', 'Unknown')
        score = user.get('score', 0)
        position = i + 1
        
        # Truncate long usernames
        if len(username) > 15:
            username = username[:12] + "..."
        
        # Get appropriate emoji for position
        if position <= 10:
            position_emoji = position_emojis[position - 1]
        else:
            position_emoji = f"{position}."
        
        # Highlight current user
        current_user = context.user_data.get('api_user', {})
        is_current_user = user.get('id') == current_user.get('id')
        
        if is_current_user:
            leaderboard_text += f"{position_emoji} <b>{username} - {score} pts 👈 YOU</b>\n"
        else:
            leaderboard_text += f"{position_emoji} {username} - {score} pts\n"
    
    # Add user's own position if not on current page
    current_user = context.user_data.get('api_user', {})
    if current_user:
        user_id = current_user.get('id')
        user_score = current_user.get('score', 0)
        
        # Find user's position in leaderboard
        user_position = None
        for i, user in enumerate(leaderboard_data):
            if user.get('id') == user_id:
                user_position = i + 1
                break
        
        if user_position and (user_position < start_idx + 1 or user_position > end_idx):
            leaderboard_text += f"\n<b>Your Position:</b> #{user_position} - {user_score} pts"
    
    # Add footer
    leaderboard_text += "\nPlay more games to climb the ranks! 🎮"
    
    # Create pagination buttons
    keyboard = []
    
    # Previous button (only if not on first page)
    if page > 1:
        keyboard.append(InlineKeyboardButton("◀️ Previous", callback_data=f"leaderboard_page_{page-1}"))
    
    # Refresh button
    keyboard.append(InlineKeyboardButton("🔄 Refresh", callback_data=f"leaderboard_page_{page}"))
    
    # Next button (only if not on last page)
    if page < total_pages:
        keyboard.append(InlineKeyboardButton("Next ▶️", callback_data=f"leaderboard_page_{page+1}"))
    
    # Add jump to my position button if user is in leaderboard
    if current_user and user_position:
        keyboard.append(InlineKeyboardButton("📍 My Rank", callback_data=f"leaderboard_jump_{user_position}"))
    
    reply_markup = InlineKeyboardMarkup([keyboard]) if keyboard else None
    
    # Edit the message with updated leaderboard
    await query.edit_message_text(leaderboard_text, parse_mode='HTML', reply_markup=reply_markup)
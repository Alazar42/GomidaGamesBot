# callbacks.py
from telegram import Update
from telegram.ext import CallbackContext
from docs import TERMS_AND_SERVICES
from games import games
from urllib.parse import quote
from buttons import unlocked_menu_markup, initial_menu_markup, regular_menu_markup
from api_client import update_user, create_user, get_leaderboard
import html

async def handle_message_response(update: Update, context: CallbackContext):
    text = update.message.text
    user = update.effective_user
    
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
        await update.message.reply_text("Share this link to invite friends: https://t.me/adwa1888bot")
    
    elif text == "👥🏅 Refferal Leaderboard":
        await show_leaderboard(update, context)
    
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

async def show_leaderboard(update: Update, context: CallbackContext):
    """Display the leaderboard from API"""
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
    
    # Format leaderboard
    leaderboard_text = "<b>🏆 Global Leaderboard</b>\n\n"
    
    # Show top 10 or all if less than 10
    display_count = min(10, len(leaderboard_data))
    
    # Emojis for top 3 positions
    position_emojis = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    
    for i in range(display_count):
        user = leaderboard_data[i]
        username = user.get('username', 'Unknown')
        score = user.get('score', 0)
        
        # Truncate long usernames
        if len(username) > 15:
            username = username[:12] + "..."
        
        # Get appropriate emoji for position
        if i < len(position_emojis):
            position_emoji = position_emojis[i]
        else:
            position_emoji = f"{i+1}."
        
        # Highlight current user
        current_user = context.user_data.get('api_user', {})
        is_current_user = user.get('id') == current_user.get('id')
        
        if is_current_user:
            leaderboard_text += f"{position_emoji} <b>@{username} - {score} pts 👈 YOU</b>\n"
        else:
            leaderboard_text += f"{position_emoji} @{username} - {score} pts\n"
    
    # Add user's own position if not in top 10
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
        
        if user_position and user_position > 10:
            leaderboard_text += f"\n<b>Your Position:</b> #{user_position} - {user_score} pts"
    
    # Add footer
    leaderboard_text += "\n\nPlay more games to climb the ranks! 🎮"
    
    await loading_msg.edit_text(leaderboard_text, parse_mode='HTML')

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
        await update.message.reply_text(
            f"✅ Thank you {contact.first_name}!\n\n"
            "Your contact has been saved successfully!\n"
            "You now have access to all features!",
            reply_markup=unlocked_menu_markup
        )
    else:
        # Fallback if API fails
        await update.message.reply_text(
            f"✅ Thank you {contact.first_name}!\n\n"
            "Your contact has been saved locally!\n"
            "Some features may be limited.",
            reply_markup=unlocked_menu_markup
        )

async def handle_callback_query(update: Update, context: CallbackContext):
    """Handle callback queries when user clicks Play button on Telegram game"""
    query = update.callback_query
    
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
                print(f"Game URL (no params): {game_url}")
            
            # Answer the callback query with the game URL
            await query.answer(url=game_url)
        else:
            await query.answer(text="Game not found!", show_alert=True)
    else:
        # Handle other callback queries if needed
        await query.answer()
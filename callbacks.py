from telegram import Update
from telegram.ext import CallbackContext
from docs import TERMS_AND_SERVICES
from games import games
from urllib.parse import quote
from buttons import unlocked_menu_markup, initial_menu_markup

async def handle_message_response(update: Update, context: CallbackContext):
    text = update.message.text

    if text == "👤 Account":
        await update.message.reply_contact(phone_number=update.message.contact.phone_number, first_name=update.message.contact.first_name, last_name=update.message.contact.last_name)
    
    elif text == "🎮 Play":
        # Check if user has shared contact
        if not context.user_data.get('contact_shared', False):
            await update.message.reply_text(
                "🔒 Games are locked!\n\n"
                "Please share your contact to unlock all games.\n"
                "Tap /start to begin.",
                reply_markup=initial_menu_markup
            )
            return
        
        # Send each game using Telegram's Game API
        for game in games:
            await update.message.reply_game(game_short_name=game["short_name"])
    
    elif text == "✉️ Invite":
        await update.message.reply_text("Share this link to invite friends: https://t.me/adwa1888bot")
    
    elif text == "👥🏅 Refferal Leaderboard":
        await update.message.reply_text("Here is the current leaderboard:\n1. UserA - 100 pts\n2. UserB - 90 pts")
    
    elif text == "📜Terms & Conditions":
        await update.message.reply_markdown_v2(TERMS_AND_SERVICES)
    
    elif text == "⚙️ Settings":
        await update.message.reply_text("Settings menu:\n1. Change username\n2. Change notifications\n3. Back")
    
    else:
        # If user sends any other text, remind them to share contact
        if not context.user_data.get('contact_shared', False):
            await update.message.reply_text(
                "Please share your contact to continue.\n"
                "Tap the '📞 Share Contact' button below:",
                reply_markup=initial_menu_markup
            )

async def handle_contact_shared(update: Update, context: CallbackContext):
    """Handle when user shares their contact"""
    contact = update.message.contact
    
    # Store that user has shared contact
    context.user_data['contact_shared'] = True
    context.user_data['user_phone'] = contact.phone_number
    context.user_data['user_first_name'] = contact.first_name
    context.user_data['user_last_name'] = contact.last_name
    
    # Thank user and show unlocked menu
    await update.message.reply_text(
        f"✅ Thank you {contact.first_name}!\n\n"
        "🎮 All games are now unlocked!\n"
        "Tap '🎮 Play' to start gaming!",
        reply_markup=unlocked_menu_markup
    )

async def handle_callback_query(update: Update, context: CallbackContext):
    """Handle callback queries when user clicks Play button on Telegram game"""
    query = update.callback_query
    
    # For Telegram Game API, the callback contains game_short_name
    if query.game_short_name:
        # Check if user has shared contact
        if not context.user_data.get('contact_shared', False):
            await query.answer(
                text="🔒 Please share your contact first to play games!\nTap /start to begin.",
                show_alert=True
            )
            return
        
        # Find the game in your games list
        game_data = next((g for g in games if g["short_name"] == query.game_short_name), None)
        
        if game_data:
            # Get user information
            user = update.effective_user
            
            # Create URL parameters with user data
            user_params = {
                'tg_user_id': str(user.id),
                'tg_first_name': user.first_name or '',
                'tg_last_name': user.last_name or '',
                'tg_username': user.username or '',
                'tg_language': user.language_code or 'en',
            }
            
            # Add contact info if available
            if context.user_data.get('user_phone'):
                user_phone = context.user_data['user_phone']
                print(f"📱 Sending phone to game: {user_phone}")
                
                # Add phone with ALL parameter names for compatibility
                user_params['user_phone'] = user_phone
                user_params['phone'] = user_phone
                user_params['telegram_phone'] = user_phone
                user_params['phone_number'] = user_phone
            
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
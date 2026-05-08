# notifications.py
import os
import logging
from typing import List
import json
from api_client import get_all_users

SUBSCRIBERS_FILE = os.path.join(os.path.dirname(__file__), "subscribers.json")

def _load_subscribers() -> List[int]:
    try:
        if os.path.exists(SUBSCRIBERS_FILE):
            with open(SUBSCRIBERS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return [int(x) for x in data]
    except Exception as e:
        logger.error(f"❌ Failed to load subscribers: {e}")
    return []

def _save_subscribers(subs: List[int]):
    try:
        with open(SUBSCRIBERS_FILE, "w", encoding="utf-8") as f:
            json.dump(list(subs), f)
    except Exception as e:
        logger.error(f"❌ Failed to save subscribers: {e}")

def add_subscriber(user_id: int):
    subs = set(_load_subscribers())
    subs.add(int(user_id))
    _save_subscribers(sorted(list(subs)))

def remove_subscriber(user_id: int):
    subs = set(_load_subscribers())
    subs.discard(int(user_id))
    _save_subscribers(sorted(list(subs)))

def get_subscribers() -> List[int]:
    return _load_subscribers()

async def broadcast_notification(bot, text: str, photo_file_id: str = None, parse_mode: str = None):
    """Send a message (and optional photo) to all subscribers."""
    subs = _load_subscribers()

    # If no local subscribers, try to fetch from main user DB
    if not subs:
        try:
            users = await get_all_users()
            if users:
                # Expect users to be dicts with Telegram IDs under 'id' key
                subs = [int(u.get('id')) for u in users if u.get('id')]
                logger.info(f"ℹ️ Loaded {len(subs)} subscribers from main DB")
        except Exception as e:
            logger.exception(f"Failed to load users from API fallback: {e}")

    if not subs:
        logger.info("ℹ️ No subscribers to broadcast to after checking main DB")
        return 0

    sent = 0
    for user_id in subs:
        try:
            if photo_file_id:
                await bot.send_photo(chat_id=user_id, photo=photo_file_id, caption=text, parse_mode=parse_mode)
            else:
                await bot.send_message(chat_id=user_id, text=text, parse_mode=parse_mode)
            sent += 1
        except Exception as e:
            logger.error(f"❌ Failed to send notification to {user_id}: {e}")
    logger.info(f"✅ Broadcast complete, messages sent: {sent}")
    return sent

logger = logging.getLogger(__name__)

# Get admin phone numbers from environment
def get_admin_phone_numbers() -> List[str]:
    """Get admin phone numbers from environment variable"""
    phone_numbers_str = os.getenv("ADMIN_PHONE_NUMBERS", "")
    if phone_numbers_str:
        # Split by comma and strip whitespace
        return [phone.strip() for phone in phone_numbers_str.split(",") if phone.strip()]
    return []

async def send_registration_notification(bot, new_user_username: str, new_user_phone: str = ""):
    """
    Send notification to admins about new registration
    
    Args:
        bot: Telegram Bot instance
        new_user_username: Username of the new user
        new_user_phone: Phone number of the new user (optional)
    """
    admin_phones = get_admin_phone_numbers()
    if not admin_phones:
        logger.warning("⚠️ No admin phone numbers configured for notifications")
        return
    
    # Format the notification message
    phone_info = f"Phone: {new_user_phone}" if new_user_phone else "Phone: Not shared"
    message = f"📱 New User Registration\n\n👤 Username: {new_user_username}\n{phone_info}\n\nWelcome to Gomida Games! 🎮"
    
    # Try to send to each admin
    for admin_phone in admin_phones:
        try:
            # In Telegram, we can't directly message phone numbers
            # We need to find the user ID by phone number or use a different approach
            # Since direct messaging by phone isn't straightforward in Telegram,
            # we need to use alternative methods
            logger.info(f"📨 Registration notification for: {new_user_username} - Would send to admin: {admin_phone}")
            
            # Alternative: Store admin user IDs instead of phone numbers
            # For now, we'll just log it
            
        except Exception as e:
            logger.error(f"❌ Failed to send notification to {admin_phone}: {e}")
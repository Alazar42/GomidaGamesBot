# notifications.py
import os
import logging
from typing import List

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
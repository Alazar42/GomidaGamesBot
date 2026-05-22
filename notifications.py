# notifications.py
import os
import logging
from typing import List
import json
import asyncio
import csv
import re
from io import StringIO

import httpx

from api_client import get_all_users

logger = logging.getLogger(__name__)

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

def _extract_sheet_id(sheet_url: str) -> str:
    match = re.search(r"/d/([a-zA-Z0-9-_]+)", sheet_url or "")
    return match.group(1) if match else (sheet_url or "").strip()


async def _fetch_sheet_users(sheet_url: str, gid: str = "0") -> List[int]:
    sheet_id = _extract_sheet_id(sheet_url)
    if not sheet_id:
        return []

    export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    if gid:
        export_url += f"&gid={gid}"

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        response = await client.get(export_url)
        response.raise_for_status()
        csv_text = response.text

    reader = csv.DictReader(StringIO(csv_text))
    sheet_users: List[int] = []
    for row in reader:
        found = None
        for key in row.keys():
            if key and key.strip().lower() in ("telegram id", "telegram_id", "telegramid", "telegram", "id"):
                found = row.get(key)
                break
        if not found:
            for value in row.values():
                if value and re.search(r"\d{5,}", str(value)):
                    found = value
                    break
        if found:
            digits = re.sub(r"[^0-9-]", "", str(found)).strip()
            if digits:
                try:
                    sheet_users.append(int(digits))
                except Exception:
                    continue

    return sorted(list(set(sheet_users)))


async def broadcast_notification(
    bot,
    text: str,
    photo_file_id: str = None,
    parse_mode: str = None,
    include_sheet_users: bool = False,
    sheet_url: str | None = None,
    sheet_gid: str = "0",
):
    """Send a message (and optional photo) to all subscribers.

    When include_sheet_users is True, adds users from a Google Sheet export too.
    """
    # Start with local subscribers and always augment with DB users.
    subs = set(_load_subscribers())

    try:
        users = await get_all_users()
        db_count = 0
        if users:
            # Extract user IDs, checking multiple possible field names
            for user in users:
                user_id = None
                # Try common variants
                for field in ('id', 'telegram_id', 'tg_id', 'telegramId'):
                    if field in user and user[field]:
                        try:
                            user_id = int(user[field])
                            break
                        except (ValueError, TypeError):
                            continue
                if user_id:
                    if user_id not in subs:
                        db_count += 1
                    subs.add(user_id)
            logger.info(f"ℹ️ Added {db_count} subscribers from main DB")
    except Exception as e:
        logger.exception(f"Failed to load users from API: {e}")

    if include_sheet_users:
        try:
            if sheet_url:
                sheet_users = await _fetch_sheet_users(sheet_url, sheet_gid)
                sheet_count = 0
                for user_id in sheet_users:
                    if user_id not in subs:
                        sheet_count += 1
                    subs.add(user_id)
                logger.info(f"ℹ️ Added {sheet_count} subscribers from spreadsheet")
        except Exception as e:
            logger.exception(f"Failed to load users from spreadsheet: {e}")

    if not subs:
        logger.info("ℹ️ No subscribers to broadcast to (checked DB and local subscribers)")
        return 0

    sent = 0
    for user_id in sorted(subs):
        try:
            logger.info(f"📤 Sending notification to user {user_id}...")
            if photo_file_id:
                await bot.send_photo(chat_id=user_id, photo=photo_file_id, caption=text, parse_mode=parse_mode)
            else:
                await bot.send_message(chat_id=user_id, text=text, parse_mode=parse_mode)
            sent += 1
        except Exception as e:
            logger.error(f"❌ Failed to send notification to {user_id}: {e}")
    logger.info(f"✅ Broadcast complete, messages sent: {sent}")
    return sent


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
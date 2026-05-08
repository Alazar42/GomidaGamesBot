# notifications.py
import os
import logging
from typing import List
import json
import re
import csv
import httpx
from io import StringIO
from api_client import get_all_users

THANKS_SHEET_URL_ENV = "THANKS_SHEET_URL"
THANKS_SHEET_GID_ENV = "THANKS_SHEET_GID"

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
                        subs.append(user_id)
                logger.info(f"ℹ️ Loaded {len(subs)} subscribers from main DB")
        except Exception as e:
            logger.exception(f"Failed to load users from API fallback: {e}")

    if not subs:
        logger.info("ℹ️ No subscribers to broadcast to after checking main DB")
        # Try to load from a Google Sheet (public CSV export) if provided via env
        sheet_url = os.getenv(THANKS_SHEET_URL_ENV, "")
        sheet_gid = os.getenv(THANKS_SHEET_GID_ENV, "")
        if sheet_url:
            try:
                sheet_ids = await _fetch_sheet_subscribers(sheet_url, sheet_gid)
                if sheet_ids:
                    subs = sheet_ids
                    logger.info(f"ℹ️ Loaded {len(subs)} subscribers from Google Sheet")
            except Exception:
                logger.exception("Failed to load subscribers from Google Sheet")

    if not subs:
        logger.info("ℹ️ No subscribers to broadcast to after checking main DB and sheet")
        return 0

    sent = 0
    for user_id in subs:
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


async def _fetch_sheet_subscribers(sheet_url: str, gid: str = None):
    """Attempt to fetch Telegram IDs from a Google Sheet by exporting CSV.

    Expects a sheet with a column named like 'Telegram Id' (case-insensitive).
    The sheet must be publicly viewable or accessible via the export URL.
    """
    # Extract sheet id if a full URL was provided
    m = re.search(r"/d/([a-zA-Z0-9-_]+)", sheet_url)
    if not m:
        # Maybe the value is just an id
        sheet_id = sheet_url.strip()
    else:
        sheet_id = m.group(1)

    export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    if gid:
        export_url += f"&gid={gid}"

    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        resp = await client.get(export_url)
        resp.raise_for_status()
        text = resp.text

    reader = csv.DictReader(StringIO(text))
    ids = []
    for row in reader:
        # Look for common variants of the column name
        found = None
        for key in row.keys():
            if key and key.strip().lower() in ("telegram id", "telegram_id", "telegramid", "telegram"):
                found = row.get(key)
                break
        if not found:
            # try any numeric-looking cell
            for v in row.values():
                if v and re.search(r"\d{5,}", str(v)):
                    found = v
                    break

        if found:
            # Strip non-digit characters
            digits = re.sub(r"[^0-9-]", "", str(found)).strip()
            if digits:
                try:
                    ids.append(int(digits))
                except Exception:
                    continue

    # Deduplicate
    return sorted(list(set(ids)))

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
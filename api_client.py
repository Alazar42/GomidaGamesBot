# api_client.py
import os
import httpx
import logging
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip('/')
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

def get_headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }

async def create_user(user_data: Dict[str, Any]) -> Optional[Dict]:
    """Create a new user via Supabase REST API"""
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("❌ SUPABASE_URL or SUPABASE_KEY not set in environment.")
        return None

    try:
        # Filter fields to match the simple database schema
        db_user_data = {
            "id": user_data.get("id"),
            "username": user_data.get("username"),
            "phone": user_data.get("phone", ""),
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{SUPABASE_URL}/rest/v1/users",
                headers=get_headers(),
                json=db_user_data
            )
            
            logger.info(f"🔍 Create user response status: {response.status_code}")
            
            if response.status_code in [200, 201]:
                logger.info(f"✅ User created successfully: {db_user_data.get('username')}")
                data = response.json()
                # Return the created data or the original input if list is empty
                return data[0] if isinstance(data, list) and len(data) > 0 else db_user_data
            else:
                logger.error(f"❌ Failed to create user: {response.status_code} - {response.text}")
                return None
    except Exception as e:
        logger.error(f"❌ Error creating user: {e}")
        return None

async def update_user(user_id: int, user_data: Dict[str, Any]) -> Optional[Dict]:
    """Update existing user via Supabase REST API"""
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("❌ SUPABASE_URL or SUPABASE_KEY not set in environment.")
        return None

    try:
        # Filter fields to match the simple database schema
        db_user_data = {
            "username": user_data.get("username"),
            "phone": user_data.get("phone", ""),
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # We patch based on id
            response = await client.patch(
                f"{SUPABASE_URL}/rest/v1/users?id=eq.{user_id}",
                headers=get_headers(),
                json=db_user_data
            )
            
            logger.info(f"🔍 Update user response status: {response.status_code}")
            
            if response.status_code in [200, 204]:
                logger.info(f"✅ User {user_id} updated successfully")
                data = response.json()
                return data[0] if isinstance(data, list) and len(data) > 0 else db_user_data
            
            logger.error(f"❌ Failed to update user {user_id}: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logger.error(f"❌ Error updating user {user_id}: {e}")
        return None

async def get_user_by_tg_id(tg_id: int) -> Optional[Dict]:
    """Get user by Telegram ID from Supabase users table"""
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("❌ SUPABASE_URL or SUPABASE_KEY not set in environment.")
        return None

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{SUPABASE_URL}/rest/v1/users?id=eq.{tg_id}&select=*",
                headers=get_headers()
            )
            
            logger.info(f"🔍 Get user response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    logger.info(f"✅ User {tg_id} fetched successfully")
                    return data[0]
            
            logger.info(f"ℹ️ User {tg_id} not found or error: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"❌ Error getting user {tg_id}: {e}")
        return None

async def get_leaderboard() -> Optional[List[Dict]]:
    """Get leaderboard data from API - Mocked or adapted if needed"""
    # If the simple DB only has id, username, phone, score isn't there, we can just return empty or error
    logger.info("ℹ️ Leaderboard requested but no score column exists in simple users schema.")
    return []

async def check_user_exists(tg_id: int) -> bool:
    """Check if user exists in backend"""
    user = await get_user_by_tg_id(tg_id)
    return user is not None

async def check_api_health() -> bool:
    """Check if Supabase API is accessible"""
    if not SUPABASE_URL:
        return False
        
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Hit Supabase base URL to verify connection
            response = await client.get(SUPABASE_URL)
            return response.status_code < 500
    except:
        return False
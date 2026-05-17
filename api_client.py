# api_client.py - Direct Supabase REST API via httpx
import os
import asyncio
import logging
import httpx
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Load Supabase credentials from .env
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip().strip('"')
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip().strip('"')

# Supabase REST API endpoint
SUPABASE_API_URL = f"{SUPABASE_URL}/rest/v1"

# Default headers for Supabase API
SUPABASE_HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

if not SUPABASE_URL or not SUPABASE_KEY:
    logger.error("❌ SUPABASE_URL or SUPABASE_KEY not set in .env")


async def create_user(user_data: Dict[str, Any]) -> Optional[Dict]:
    """Create a new user in Supabase database"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{SUPABASE_API_URL}/users",
                json=user_data,
                headers=SUPABASE_HEADERS
            )
            
            logger.info(f"🔍 Create user response status: {response.status_code}")
            
            if response.status_code in [200, 201]:
                logger.info(f"✅ User created successfully: {user_data.get('username')}")
                return response.json()[0] if response.json() else None
            else:
                logger.error(f"❌ Failed to create user: {response.status_code} - {response.text}")
                return None
                
    except Exception as e:
        logger.error(f"❌ Error creating user: {e}")
        return None


async def update_user(user_id: int, user_data: Dict[str, Any]) -> Optional[Dict]:
    """Update existing user in Supabase database"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.patch(
                f"{SUPABASE_API_URL}/users?id=eq.{user_id}",
                json=user_data,
                headers=SUPABASE_HEADERS
            )
            
            logger.info(f"🔍 Update user response status: {response.status_code}")
            
            if response.status_code in [200, 204]:
                logger.info(f"✅ User {user_id} updated successfully")
                return response.json()[0] if response.json() else {"id": user_id}
            else:
                logger.error(f"❌ Failed to update user {user_id}: {response.status_code} - {response.text}")
                return None
                
    except Exception as e:
        logger.error(f"❌ Error updating user {user_id}: {e}")
        return None


async def get_user_by_tg_id(tg_id: int) -> Optional[Dict]:
    """Get user by Telegram ID from Supabase"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{SUPABASE_API_URL}/users?id=eq.{tg_id}",
                headers=SUPABASE_HEADERS
            )
            
            logger.info(f"🔍 Get user response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    logger.info(f"✅ User {tg_id} fetched successfully")
                    return data[0]
                else:
                    logger.info(f"ℹ️ User {tg_id} not found")
                    return None
            else:
                logger.error(f"❌ Failed to get user {tg_id}: {response.status_code}")
                return None
                
    except Exception as e:
        logger.error(f"❌ Error getting user {tg_id}: {e}")
        return None


async def get_leaderboard() -> Optional[List[Dict]]:
    """Get leaderboard data from Supabase"""
    try:
        # Query users ordered by points descending, limit to 100
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{SUPABASE_API_URL}/users?order=points.desc&limit=100",
                headers=SUPABASE_HEADERS
            )
            
            logger.info(f"🔍 Leaderboard response status: {response.status_code}")
            
            if response.status_code == 200:
                logger.info("✅ Leaderboard data fetched successfully")
                return response.json()
            else:
                logger.error(f"❌ Failed to fetch leaderboard: {response.status_code}")
                return []
                
    except Exception as e:
        logger.error(f"❌ Error fetching leaderboard: {e}")
        return []


async def check_user_exists(tg_id: int) -> bool:
    """Check if user exists in database"""
    user = await get_user_by_tg_id(tg_id)
    return user is not None


async def create_user_direct(user_data: Dict[str, Any]) -> Optional[Dict]:
    """Alternative method to create user (same as create_user)"""
    return await create_user(user_data)


async def check_api_health() -> bool:
    """Check if Supabase is accessible"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{SUPABASE_API_URL}/users?limit=1",
                headers=SUPABASE_HEADERS
            )
            logger.info("✅ Supabase connection healthy")
            return response.status_code == 200
            
    except Exception as e:
        logger.error(f"❌ Supabase health check failed: {e}")
        return False


async def get_all_users() -> Optional[List[Dict]]:
    """Fetch all users from Supabase database. Returns a list of user dicts or None on error."""
    max_attempts = 3
    backoff = 1
    
    try:
        for attempt in range(1, max_attempts + 1):
            try:
                logger.info(f"🔍 Fetching users list (attempt {attempt}/{max_attempts})...")
                
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(
                        f"{SUPABASE_API_URL}/users",
                        headers=SUPABASE_HEADERS
                    )
                    
                    logger.info(f"🔍 Get all users response status: {response.status_code}")
                    
                    if response.status_code == 200:
                        logger.info(f"✅ Successfully fetched users from Supabase")
                        return response.json()
                    
            except Exception as e:
                if attempt < max_attempts:
                    logger.warning(f"⚠️ Attempt {attempt} failed, retrying in {backoff}s... Error: {e}")
                    await asyncio.sleep(backoff)
                    backoff *= 2
                else:
                    raise
        
        return None
        
    except Exception as e:
        logger.error(f"❌ Error fetching all users: {e}")
        return None
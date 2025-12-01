# api_client.py
import httpx
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

API_BASE_URL = "https://match-africa-backend.vercel.app"

async def create_user(user_data: Dict[str, Any]) -> Optional[Dict]:
    """Create a new user via API"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{API_BASE_URL}/users",
                json=user_data
            )
            
            if response.status_code == 200 or response.status_code == 201:
                logger.info(f"✅ User created successfully: {user_data.get('username')}")
                return response.json()
            else:
                logger.error(f"❌ Failed to create user: {response.status_code} - {response.text}")
                return None
    except Exception as e:
        logger.error(f"❌ Error creating user: {e}")
        return None

async def update_user(user_id: int, user_data: Dict[str, Any]) -> Optional[Dict]:
    """Update existing user via API"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.put(
                f"{API_BASE_URL}/users/{user_id}",
                json=user_data
            )
            
            if response.status_code == 200:
                logger.info(f"✅ User {user_id} updated successfully")
                return response.json()
            else:
                logger.error(f"❌ Failed to update user {user_id}: {response.status_code} - {response.text}")
                return None
    except Exception as e:
        logger.error(f"❌ Error updating user {user_id}: {e}")
        return None

async def get_user_by_tg_id(tg_id: int) -> Optional[Dict]:
    """Get user by Telegram ID using /users/{id} endpoint"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{API_BASE_URL}/users/{tg_id}")
            
            if response.status_code == 200:
                logger.info(f"✅ User {tg_id} fetched successfully")
                return response.json()
            else:
                # User doesn't exist yet
                logger.info(f"ℹ️ User {tg_id} not found in backend")
                return None
    except Exception as e:
        logger.error(f"❌ Error getting user {tg_id}: {e}")
        return None

async def get_leaderboard() -> Optional[List[Dict]]:
    """Get leaderboard data from API"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{API_BASE_URL}/users/leaderboard"
            )
            
            if response.status_code == 200:
                logger.info("✅ Leaderboard data fetched successfully")
                return response.json()
            else:
                logger.error(f"❌ Failed to fetch leaderboard: {response.status_code} - {response.text}")
                return None
    except Exception as e:
        logger.error(f"❌ Error fetching leaderboard: {e}")
        return None

async def check_user_exists(tg_id: int) -> bool:
    """Check if user exists in backend"""
    user = await get_user_by_tg_id(tg_id)
    return user is not None
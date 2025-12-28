# api_client.py
import httpx
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

API_BASE_URL = "https://matchafricabackend.onrender.com"

async def create_user(user_data: Dict[str, Any]) -> Optional[Dict]:
    """Create a new user via API"""
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.post(
                f"{API_BASE_URL}/users",
                json=user_data
            )
            
            logger.info(f"🔍 Create user response status: {response.status_code}")
            logger.info(f"🔍 Response headers: {dict(response.headers)}")
            
            if response.status_code in [200, 201, 307]:
                # Handle 307 redirect by following it
                if response.status_code == 307:
                    redirect_url = response.headers.get('location')
                    if redirect_url:
                        logger.info(f"🔄 Following redirect to: {redirect_url}")
                        response = await client.post(
                            redirect_url,
                            json=user_data
                        )
                        logger.info(f"🔍 Redirect response status: {response.status_code}")
                
                if response.status_code in [200, 201]:
                    logger.info(f"✅ User created successfully: {user_data.get('username')}")
                    return response.json()
                else:
                    logger.error(f"⚠️ Unexpected status after redirect: {response.status_code}")
                    return None
            else:
                logger.error(f"❌ Failed to create user: {response.status_code} - {response.text}")
                return None
    except Exception as e:
        logger.error(f"❌ Error creating user: {e}")
        return None

async def update_user(user_id: int, user_data: Dict[str, Any]) -> Optional[Dict]:
    """Update existing user via API"""
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.put(
                f"{API_BASE_URL}/users/{user_id}",
                json=user_data
            )
            
            logger.info(f"🔍 Update user response status: {response.status_code}")
            
            if response.status_code == 200:
                logger.info(f"✅ User {user_id} updated successfully")
                return response.json()
            elif response.status_code == 307:
                # Handle redirect for PUT as well
                redirect_url = response.headers.get('location')
                if redirect_url:
                    logger.info(f"🔄 Following redirect to: {redirect_url}")
                    response = await client.put(redirect_url, json=user_data)
                    if response.status_code == 200:
                        return response.json()
            
            logger.error(f"❌ Failed to update user {user_id}: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logger.error(f"❌ Error updating user {user_id}: {e}")
        return None

async def get_user_by_tg_id(tg_id: int) -> Optional[Dict]:
    """Get user by Telegram ID using /users/{id} endpoint"""
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(f"{API_BASE_URL}/users/{tg_id}")
            
            logger.info(f"🔍 Get user response status: {response.status_code}")
            
            if response.status_code == 200:
                logger.info(f"✅ User {tg_id} fetched successfully")
                return response.json()
            elif response.status_code == 307:
                # Handle redirect
                redirect_url = response.headers.get('location')
                if redirect_url:
                    logger.info(f"🔄 Following redirect to: {redirect_url}")
                    response = await client.get(redirect_url)
                    if response.status_code == 200:
                        return response.json()
            
            # User doesn't exist yet or other error
            logger.info(f"ℹ️ User {tg_id} not found or error: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"❌ Error getting user {tg_id}: {e}")
        return None

async def get_leaderboard() -> Optional[List[Dict]]:
    """Get leaderboard data from API"""
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(
                f"{API_BASE_URL}/users/leaderboard"
            )
            
            logger.info(f"🔍 Leaderboard response status: {response.status_code}")
            
            if response.status_code == 200:
                logger.info("✅ Leaderboard data fetched successfully")
                return response.json()
            elif response.status_code == 307:
                redirect_url = response.headers.get('location')
                if redirect_url:
                    logger.info(f"🔄 Following redirect to: {redirect_url}")
                    response = await client.get(redirect_url)
                    if response.status_code == 200:
                        return response.json()
            
            logger.error(f"❌ Failed to fetch leaderboard: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logger.error(f"❌ Error fetching leaderboard: {e}")
        return None

async def check_user_exists(tg_id: int) -> bool:
    """Check if user exists in backend"""
    user = await get_user_by_tg_id(tg_id)
    return user is not None

# Alternative direct approach for creating user
async def create_user_direct(user_data: Dict[str, Any]) -> Optional[Dict]:
    """Alternative method to create user, bypassing redirect issues"""
    try:
        # Try direct endpoint first
        direct_endpoint = f"{API_BASE_URL}/api/users"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                direct_endpoint,
                json=user_data
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"✅ User created via direct endpoint: {user_data.get('username')}")
                return response.json()
            
            # If direct endpoint fails, try the regular one with redirect handling
            logger.info("🔄 Trying regular endpoint with redirect...")
            return await create_user(user_data)
            
    except Exception as e:
        logger.error(f"❌ Error in create_user_direct: {e}")
        return None

# Health check for API
async def check_api_health() -> bool:
    """Check if API is accessible"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{API_BASE_URL}/health")
            return response.status_code == 200
    except:
        try:
            # Try the root endpoint
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(API_BASE_URL)
                return response.status_code < 500
        except:
            return False
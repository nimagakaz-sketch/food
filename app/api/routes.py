import time
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel
from app.database.db import db
from app.database.models import UserProfile, UserProfileCreate
from app.services.menu_generator import menu_generator
from app.services.price_comparator import price_comparator
from app.services.recipe_catalog import BASELINE_STORE_PRICES

router = APIRouter()
SERVER_START_TIME = time.time()

# --- Health Check (GET and HEAD) ---
@router.api_route("/health", methods=["GET", "HEAD"])
async def health_check():
    """Lightweight health check endpoint for monitoring services like UptimeRobot"""
    return {
        "status": "ok",
        "service": "food_family_bot",
        "time": datetime.utcnow().isoformat()
    }

# --- Profile Endpoints ---
@router.get("/api/profile/{user_id}", response_model=UserProfile)
async def get_profile(user_id: int):
    profile = await db.get_user_profile(user_id)
    if not profile:
        # Return default profile for new or web users
        return UserProfile(
            telegram_id=user_id,
            username="",
            first_name="Гость",
            favorite_products=["курица", "авокадо", "рыба"],
            stop_list=[],
            allergies=[],
            family_size=2,
            plan_days=7
        )
    return profile

@router.post("/api/profile", response_model=UserProfile)
async def update_profile(profile_in: UserProfileCreate):
    profile = UserProfile(**profile_in.model_dump())
    await db.save_user_profile(profile)
    # Regenerate menu with new preferences
    await menu_generator.generate_menu_for_user(profile, force_new=True)
    return profile

# --- Menu Endpoints ---
@router.get("/api/menu/{user_id}")
async def get_user_menu(user_id: int, refresh: bool = False):
    profile = await db.get_user_profile(user_id)
    if not profile:
        profile = UserProfile(
            telegram_id=user_id,
            username="Пользователь",
            first_name="Пользователь",
            favorite_products=["курица", "овощи", "рыба"],
            stop_list=[],
            allergies=[],
            family_size=2,
            plan_days=7
        )
        await db.save_user_profile(profile)
    
    menu = await menu_generator.generate_menu_for_user(profile, force_new=refresh)
    return menu.model_dump() if hasattr(menu, "model_dump") else menu

class GenerateMenuRequest(BaseModel):
    user_id: int
    force_new: bool = True

@router.post("/api/menu/generate")
async def generate_menu_api(req: GenerateMenuRequest):
    profile = await db.get_user_profile(req.user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="User profile not found. Please complete preferences first.")
    
    menu = await menu_generator.generate_menu_for_user(profile, force_new=req.force_new)
    return menu.model_dump() if hasattr(menu, "model_dump") else menu

# --- Price Comparison Endpoints ---
@router.get("/api/prices/compare/{user_id}")
async def get_price_comparison(user_id: int):
    profile = await db.get_user_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="User profile not found")
    
    menu = await menu_generator.generate_menu_for_user(profile)
    if not menu.price_comparison:
        comp = await price_comparator.compare_basket(menu.shopping_list)
        return comp.model_dump() if hasattr(comp, "model_dump") else comp
    return menu.price_comparison

@router.get("/api/prices/catalog")
async def get_price_catalog():
    """Get all supermarket prices across Pyaterochka, Magnit, and Lenta"""
    prices = await db.get_all_prices()
    if not prices:
        await price_comparator.init_prices()
        prices = await db.get_all_prices()
    return list(prices.values())

# --- Bot & System Status ---
@router.get("/api/status")
async def get_system_status():
    uptime_sec = int(time.time() - SERVER_START_TIME)
    users = await db.get_all_active_users()
    prices = await db.get_all_prices()

    return {
        "status": "online",
        "uptime_seconds": uptime_sec,
        "uptime_formatted": f"{uptime_sec // 3600}ч {(uptime_sec % 3600) // 60}м {uptime_sec % 60}с",
        "active_users_count": len(users),
        "tracked_products_count": len(prices),
        "scheduler_active": True,
        "auto_update": "Каждый понедельник в 09:00",
        "stores_monitored": ["Пятерочка", "Магнит", "Лента"]
    }

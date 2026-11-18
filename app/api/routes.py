import time
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel
from app.database.db import db
from app.database.models import UserProfile, UserProfileCreate, ItemActionRequest
from app.services.menu_generator import menu_generator
from app.services.price_comparator import price_comparator
from app.services.retail_parsers import CATEGORIZED_PRESET_CATALOG, retail_price_searcher

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

# --- Preset Catalog ---
@router.get("/api/catalog/preset")
async def get_preset_catalog():
    """Get preset categorized catalog of products for easy selection"""
    return CATEGORIZED_PRESET_CATALOG

# --- Profile Endpoints ---
@router.get("/api/profile/{user_id}", response_model=UserProfile)
async def get_profile(user_id: int):
    profile = await db.get_user_profile(user_id)
    if not profile:
        return UserProfile(
            telegram_id=user_id,
            username="",
            first_name="Гость",
            favorite_products=["Куриное филе", "Красная рыба (лосось/форель)", "Авокадо"],
            stop_list=["Лук репчатый"],
            allergies=[],
            family_size=2,
            plan_days=7
        )
    return profile

@router.post("/api/profile", response_model=UserProfile)
async def update_profile(profile_in: UserProfileCreate):
    profile = UserProfile(**profile_in.model_dump())
    await db.save_user_profile(profile)
    await menu_generator.generate_menu_for_user(profile, force_new=True)
    return profile

# --- Granular 1-Click Item Add / Remove Endpoints ---
@router.post("/api/profile/{user_id}/favorites", response_model=UserProfile)
async def add_favorite_product(user_id: int, req: ItemActionRequest):
    """Add a custom product to user's favorites"""
    if not req.item.strip():
        raise HTTPException(status_code=400, detail="Item name cannot be empty")
    profile = await db.add_favorite_item(user_id, req.item.strip())
    # Regenerate menu in background or return updated profile
    await menu_generator.generate_menu_for_user(profile, force_new=True)
    return profile

@router.delete("/api/profile/{user_id}/favorites/{item}", response_model=UserProfile)
async def remove_favorite_product(user_id: int, item: str):
    """Remove a product from user's favorites in 1 click"""
    profile = await db.remove_favorite_item(user_id, item)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    await menu_generator.generate_menu_for_user(profile, force_new=True)
    return profile

@router.post("/api/profile/{user_id}/stop-list", response_model=UserProfile)
async def add_stop_product(user_id: int, req: ItemActionRequest):
    """Add a custom product to user's stop-list"""
    if not req.item.strip():
        raise HTTPException(status_code=400, detail="Item name cannot be empty")
    profile = await db.add_stop_item(user_id, req.item.strip())
    await menu_generator.generate_menu_for_user(profile, force_new=True)
    return profile

@router.delete("/api/profile/{user_id}/stop-list/{item}", response_model=UserProfile)
async def remove_stop_product(user_id: int, item: str):
    """Remove a product from user's stop-list in 1 click"""
    profile = await db.remove_stop_item(user_id, item)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    await menu_generator.generate_menu_for_user(profile, force_new=True)
    return profile

@router.post("/api/profile/{user_id}/allergies", response_model=UserProfile)
async def add_allergy(user_id: int, req: ItemActionRequest):
    """Add an allergy/restriction to user's profile"""
    profile = await db.add_allergy_item(user_id, req.item.strip())
    await menu_generator.generate_menu_for_user(profile, force_new=True)
    return profile

@router.delete("/api/profile/{user_id}/allergies/{item}", response_model=UserProfile)
async def remove_allergy(user_id: int, item: str):
    """Remove an allergy/restriction from user's profile in 1 click"""
    profile = await db.remove_allergy_item(user_id, item)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
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
            favorite_products=["Куриное филе", "Красная рыба (лосось/форель)", "Авокадо"],
            stop_list=["Лук репчатый"],
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

@router.get("/api/prices/live")
async def query_live_price(product: str = Query(..., description="Name of the product")):
    """Direct live price query for any item across Pyaterochka, Magnit, and Lenta"""
    res = await retail_price_searcher.get_realtime_prices_for_item(product, 1.0, "кг")
    return res

# --- Bot & System Status ---
@router.get("/api/status")
async def get_system_status():
    uptime_sec = int(time.time() - SERVER_START_TIME)
    users = await db.get_all_active_users()

    return {
        "status": "online",
        "uptime_seconds": uptime_sec,
        "uptime_formatted": f"{uptime_sec // 3600}ч {(uptime_sec % 3600) // 60}м {uptime_sec % 60}с",
        "active_users_count": len(users),
        "scheduler_active": True,
        "auto_update": "Каждый понедельник в 09:00",
        "stores_monitored": ["Пятерочка", "Магнит", "Лента"],
        "pricing_mode": "Strict Real-Time Catalogs"
    }

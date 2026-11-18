import json
import logging
import os
import aiosqlite
from datetime import datetime
from typing import Optional, List, Dict, Any
from app.config import settings
from app.database.models import UserProfile, WeeklyMenu, PriceComparison

logger = logging.getLogger("food_bot.database")

class Database:
    def __init__(self, db_path: str = settings.DATABASE_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)

    async def init(self):
        """Initialize database tables"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER DEFAULT 1
            );
            """)

            await db.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                user_id INTEGER PRIMARY KEY,
                favorite_products TEXT DEFAULT '[]',
                stop_list TEXT DEFAULT '[]',
                allergies TEXT DEFAULT '[]',
                family_size INTEGER DEFAULT 2,
                plan_days INTEGER DEFAULT 7,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (telegram_id)
            );
            """)

            await db.execute("""
            CREATE TABLE IF NOT EXISTS user_menus (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                week_number INTEGER,
                year INTEGER,
                menu_data TEXT,
                shopping_list TEXT,
                price_comparison TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users (telegram_id)
            );
            """)

            await db.execute("""
            CREATE TABLE IF NOT EXISTS supermarket_prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_name TEXT UNIQUE,
                category TEXT,
                unit TEXT,
                price_pyaterochka REAL,
                price_magnit REAL,
                price_lenta REAL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)

            await db.commit()
            logger.info(f"Database initialized at {self.db_path}")

    # --- User & Preferences ---
    async def get_or_create_user(self, telegram_id: int, username: Optional[str] = None, first_name: Optional[str] = None):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT telegram_id FROM users WHERE telegram_id = ?", (telegram_id,)) as cursor:
                row = await cursor.fetchone()
                if not row:
                    await db.execute(
                        "INSERT INTO users (telegram_id, username, first_name) VALUES (?, ?, ?)",
                        (telegram_id, username, first_name)
                    )
                    # Create default preference entry
                    await db.execute(
                        "INSERT INTO user_preferences (user_id) VALUES (?)",
                        (telegram_id,)
                    )
                    await db.commit()

    async def get_user_profile(self, user_id: int) -> Optional[UserProfile]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT u.telegram_id, u.username, u.first_name, 
                       p.favorite_products, p.stop_list, p.allergies, p.family_size, p.plan_days, p.updated_at
                FROM users u
                LEFT JOIN user_preferences p ON u.telegram_id = p.user_id
                WHERE u.telegram_id = ?
            """, (user_id,)) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return None
                
                favs = json.loads(row["favorite_products"] or "[]")
                stops = json.loads(row["stop_list"] or "[]")
                allergies = json.loads(row["allergies"] or "[]")
                
                return UserProfile(
                    telegram_id=row["telegram_id"],
                    username=row["username"],
                    first_name=row["first_name"],
                    favorite_products=favs,
                    stop_list=stops,
                    allergies=allergies,
                    family_size=row["family_size"] or 2,
                    plan_days=row["plan_days"] or 7,
                    updated_at=str(row["updated_at"] or "")
                )

    async def save_user_profile(self, profile: UserProfile) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            await self.get_or_create_user(profile.telegram_id, profile.username, profile.first_name)
            await db.execute("""
                INSERT INTO user_preferences (user_id, favorite_products, stop_list, allergies, family_size, plan_days, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET
                    favorite_products = excluded.favorite_products,
                    stop_list = excluded.stop_list,
                    allergies = excluded.allergies,
                    family_size = excluded.family_size,
                    plan_days = excluded.plan_days,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                profile.telegram_id,
                json.dumps(profile.favorite_products, ensure_ascii=False),
                json.dumps(profile.stop_list, ensure_ascii=False),
                json.dumps(profile.allergies, ensure_ascii=False),
                profile.family_size,
                profile.plan_days
            ))
            await db.commit()
            return True

    async def get_all_active_users(self) -> List[int]:
        """Return list of telegram_ids of all active users"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT telegram_id FROM users WHERE is_active = 1") as cursor:
                rows = await cursor.fetchall()
                return [r[0] for r in rows]

    # --- Menus & Weekly Plans ---
    async def save_weekly_menu(self, user_id: int, week_number: int, year: int, days_json: list, shopping_list_json: list, price_comparison_json: dict) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            # Set older menus for this user to inactive
            await db.execute("UPDATE user_menus SET is_active = 0 WHERE user_id = ?", (user_id,))
            
            cursor = await db.execute("""
                INSERT INTO user_menus (user_id, week_number, year, menu_data, shopping_list, price_comparison, is_active)
                VALUES (?, ?, ?, ?, ?, ?, 1)
            """, (
                user_id,
                week_number,
                year,
                json.dumps(days_json, ensure_ascii=False),
                json.dumps(shopping_list_json, ensure_ascii=False),
                json.dumps(price_comparison_json, ensure_ascii=False)
            ))
            await db.commit()
            return cursor.lastrowid

    async def get_current_menu(self, user_id: int) -> Optional[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT id, user_id, week_number, year, menu_data, shopping_list, price_comparison, created_at
                FROM user_menus
                WHERE user_id = ? AND is_active = 1
                ORDER BY id DESC LIMIT 1
            """, (user_id,)) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return None
                
                return {
                    "id": row["id"],
                    "user_id": row["user_id"],
                    "week_number": row["week_number"],
                    "year": row["year"],
                    "days": json.loads(row["menu_data"] or "[]"),
                    "shopping_list": json.loads(row["shopping_list"] or "[]"),
                    "price_comparison": json.loads(row["price_comparison"] or "{}"),
                    "created_at": str(row["created_at"])
                }

    # --- Supermarket Prices ---
    async def get_all_prices(self) -> Dict[str, Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT product_name, category, unit, price_pyaterochka, price_magnit, price_lenta FROM supermarket_prices") as cursor:
                rows = await cursor.fetchall()
                result = {}
                for r in rows:
                    result[r["product_name"].lower()] = {
                        "product_name": r["product_name"],
                        "category": r["category"],
                        "unit": r["unit"],
                        "pyaterochka": r["price_pyaterochka"],
                        "magnit": r["price_magnit"],
                        "lenta": r["price_lenta"],
                    }
                return result

    async def upsert_price(self, product_name: str, category: str, unit: str, p_pyaterochka: float, p_magnit: float, p_lenta: float):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO supermarket_prices (product_name, category, unit, price_pyaterochka, price_magnit, price_lenta, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(product_name) DO UPDATE SET
                    category = excluded.category,
                    unit = excluded.unit,
                    price_pyaterochka = excluded.price_pyaterochka,
                    price_magnit = excluded.price_magnit,
                    price_lenta = excluded.price_lenta,
                    updated_at = CURRENT_TIMESTAMP
            """, (product_name, category, unit, p_pyaterochka, p_magnit, p_lenta))
            await db.commit()

db = Database()

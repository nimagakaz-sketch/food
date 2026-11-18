import os
import unittest
from starlette.requests import Request
from app.database.db import db
from app.database.models import UserProfile
from app.services.menu_generator import menu_generator
from app.services.price_comparator import price_comparator
from main import root_index, health_endpoint

def create_mock_request(method: str, path: str = "/") -> Request:
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "headers": [(b"host", b"localhost:8000")],
        "query_string": b"",
        "app": None,
    }
    return Request(scope)

class TestFoodBotBackend(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Use isolated test database
        db.db_path = "data/test_food_bot.db"
        await db.init()
        await price_comparator.init_prices()

    async def asyncTearDown(self):
        if os.path.exists("data/test_food_bot.db"):
            try:
                os.remove("data/test_food_bot.db")
            except Exception:
                pass

    # --- 1. HEALTH CHECK & HTTP HEAD TESTS (Requirement 4) ---
    async def test_health_check_get_and_head(self):
        # Test GET /
        req_get_root = create_mock_request("GET", "/")
        resp_get_root = await root_index(req_get_root)
        self.assertEqual(resp_get_root.status_code, 200)

        # Test HEAD / (must succeed with 200 OK and no heavy disk stream)
        req_head_root = create_mock_request("HEAD", "/")
        resp_head_root = await root_index(req_head_root)
        self.assertEqual(resp_head_root.status_code, 200)
        self.assertEqual(resp_head_root.headers.get("x-health"), "OK")

        # Test GET /health
        req_get_health = create_mock_request("GET", "/health")
        resp_get_health = await health_endpoint(req_get_health)
        self.assertEqual(resp_get_health["status"], "ok")

        # Test HEAD /health (crucial for UptimeRobot monitoring)
        req_head_health = create_mock_request("HEAD", "/health")
        resp_head_health = await health_endpoint(req_head_health)
        self.assertEqual(resp_head_health.status_code, 200)
        self.assertEqual(resp_head_health.headers.get("x-health"), "OK")

    # --- 2. ONBOARDING & PREFERENCES PROFILE TESTS (Requirement 1) ---
    async def test_user_onboarding_and_preferences(self):
        profile = UserProfile(
            telegram_id=99901,
            username="test_family",
            first_name="Иван",
            favorite_products=["курица", "авокадо", "рыба"],
            stop_list=["лук", "грибы", "свинина"],
            allergies=["глютен"],
            family_size=3,
            plan_days=7
        )
        saved = await db.save_user_profile(profile)
        self.assertTrue(saved)

        fetched = await db.get_user_profile(99901)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.telegram_id, 99901)
        self.assertEqual(fetched.family_size, 3)
        self.assertEqual(fetched.plan_days, 7)
        self.assertIn("курица", fetched.favorite_products)
        self.assertIn("лук", fetched.stop_list)
        self.assertIn("глютен", fetched.allergies)

    # --- 3. MENU GENERATION & ALLERGEN/STOP-LIST FILTERING (Requirement 2) ---
    async def test_menu_generation_respects_constraints(self):
        profile = UserProfile(
            telegram_id=99902,
            username="allergy_user",
            first_name="Мария",
            favorite_products=["рыба", "авокадо"],
            stop_list=["свинина", "грибы"],
            allergies=["глютен"],
            family_size=4,
            plan_days=5
        )
        await db.save_user_profile(profile)

        menu = await menu_generator.generate_menu_for_user(profile, force_new=True)
        self.assertEqual(len(menu.days), 5)
        self.assertEqual(menu.user_id, 99902)

        # Check all dishes in all days
        for day in menu.days:
            self.assertEqual(len(day.dishes), 3)  # breakfast, lunch, dinner
            for dish in day.dishes:
                dish_text = (
                    dish.name.lower() + " " +
                    " ".join(t.lower() for t in dish.tags) + " " +
                    " ".join(i.name.lower() for i in dish.ingredients)
                )
                # Verify stop-list is NOT in dish
                for stop_item in profile.stop_list:
                    self.assertNotIn(stop_item.lower(), dish_text, f"Stop item '{stop_item}' found in dish '{dish.name}'")

                # Verify allergens are excluded
                self.assertNotIn("глютен", [t.lower() for t in dish.tags])

                # Check family scaling: ingredients scaled for 4 members
                for ing in dish.ingredients:
                    self.assertGreater(ing.amount, 0)

        # Check shopping list aggregation
        self.assertGreater(len(menu.shopping_list), 0)

    # --- 4. SUPERMARKET PRICE COMPARISON (Requirement 3) ---
    async def test_supermarket_price_comparison(self):
        profile = UserProfile(
            telegram_id=99903,
            username="buyer_user",
            first_name="Алексей",
            favorite_products=["курица", "говядина"],
            stop_list=[],
            allergies=[],
            family_size=2,
            plan_days=7
        )
        await db.save_user_profile(profile)

        menu = await menu_generator.generate_menu_for_user(profile, force_new=True)
        comp = menu.price_comparison

        self.assertIsNotNone(comp)
        self.assertIn("pyaterochka", comp.stores)
        self.assertIn("magnit", comp.stores)
        self.assertIn("lenta", comp.stores)

        pya_total = comp.stores["pyaterochka"].total_price
        mag_total = comp.stores["magnit"].total_price
        len_total = comp.stores["lenta"].total_price

        self.assertGreater(pya_total, 0)
        self.assertGreater(mag_total, 0)
        self.assertGreater(len_total, 0)

        # Winning store must be marked
        winning_stores = [s for s in comp.stores.values() if s.is_cheapest]
        self.assertEqual(len(winning_stores), 1)
        self.assertEqual(comp.cheapest_store, winning_stores[0].store_name)
        self.assertGreaterEqual(comp.max_savings, 0)

        # Check item price breakdown
        self.assertGreater(len(comp.items), 0)
        first_item = comp.items[0]
        self.assertGreater(first_item.price_pyaterochka, 0)
        self.assertGreater(first_item.price_magnit, 0)
        self.assertGreater(first_item.price_lenta, 0)
        self.assertIn(first_item.best_store, ["Пятерочка", "Магнит", "Лента"])

if __name__ == "__main__":
    unittest.main()

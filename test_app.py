import os
import unittest
from starlette.requests import Request
from app.database.db import db
from app.database.models import UserProfile, ItemActionRequest
from app.services.menu_generator import menu_generator
from app.services.price_comparator import price_comparator
from app.services.retail_parsers import retail_price_searcher, CATEGORIZED_PRESET_CATALOG
from app.api.routes import add_favorite_product, remove_favorite_product, add_stop_product, remove_stop_product
from app.bot.keyboards.inline import get_multi_select_keyboard, POPULAR_FAVORITES, POPULAR_STOP_ITEMS
from app.bot.handlers.common import build_profile_keyboard
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

    # --- 1. HEALTH CHECK & HTTP HEAD TESTS ---
    async def test_health_check_get_and_head(self):
        req_get_root = create_mock_request("GET", "/")
        resp_get_root = await root_index(req_get_root)
        self.assertEqual(resp_get_root.status_code, 200)

        req_head_root = create_mock_request("HEAD", "/")
        resp_head_root = await root_index(req_head_root)
        self.assertEqual(resp_head_root.status_code, 200)
        self.assertEqual(resp_head_root.headers.get("x-health"), "OK")

        req_get_health = create_mock_request("GET", "/health")
        resp_get_health = await health_endpoint(req_get_health)
        self.assertEqual(resp_get_health["status"], "ok")

        req_head_health = create_mock_request("HEAD", "/health")
        resp_head_health = await health_endpoint(req_head_health)
        self.assertEqual(resp_head_health.status_code, 200)
        self.assertEqual(resp_head_health.headers.get("x-health"), "OK")

    # --- 2. CUSTOM PRODUCT MANUAL INPUT & 1-CLICK DELETE TESTS ---
    async def test_custom_product_input_and_one_click_delete(self):
        user_id = 99911
        # Start with empty profile
        await db.get_or_create_user(user_id, "family_cook", "Анна")

        # 1. Add custom product to Favorites
        prof = await add_favorite_product(user_id, ItemActionRequest(item="Киноа"))
        self.assertIn("Киноа", prof.favorite_products)

        # 2. Add custom product to Stop-List
        prof = await add_stop_product(user_id, ItemActionRequest(item="Кинза"))
        self.assertIn("Кинза", prof.stop_list)

        # 3. Add another item to Favorites (e.g. "Спаржа")
        prof = await db.add_favorite_item(user_id, "Спаржа")
        self.assertIn("Спаржа", prof.favorite_products)

        # 4. Remove in 1 click from Favorites
        prof_after_del = await remove_favorite_product(user_id, "Киноа")
        self.assertNotIn("Киноа", prof_after_del.favorite_products)
        self.assertIn("Спаржа", prof_after_del.favorite_products)

        # 5. Remove in 1 click from Stop-List
        prof_stop_del = await remove_stop_product(user_id, "Кинза")
        self.assertNotIn("Кинза", prof_stop_del.stop_list)

    # --- 3. PRESET CATEGORIZED CATALOG TEST ---
    def test_preset_categorized_catalog(self):
        self.assertIn("Мясо и птица", CATEGORIZED_PRESET_CATALOG)
        self.assertIn("Рыба и морепродукты", CATEGORIZED_PRESET_CATALOG)
        self.assertIn("Овощи и зелень", CATEGORIZED_PRESET_CATALOG)
        self.assertGreater(len(CATEGORIZED_PRESET_CATALOG["Мясо и птица"]), 0)

    # --- 4. REAL-TIME SUPERMARKET PRICE SEARCH TEST ---
    async def test_realtime_supermarket_price_search(self):
        # Query live price for an item across Pyaterochka, Magnit, and Lenta
        live_res = await retail_price_searcher.get_realtime_prices_for_item("Куриное филе", 1.0, "кг")
        
        self.assertIsNotNone(live_res)
        self.assertEqual(live_res["product_name"], "Куриное филе")
        self.assertTrue(live_res["is_live"])
        self.assertGreater(live_res["price_pyaterochka"], 0)
        self.assertGreater(live_res["price_magnit"], 0)
        self.assertGreater(live_res["price_lenta"], 0)
        self.assertIn(live_res["best_store"], ["Пятерочка", "Магнит", "Лента"])
        self.assertIsNotNone(live_res["checked_at"])

    # --- 5. MENU GENERATION WITH CUSTOM EXCLUSIONS & BASKET CALCULATION ---
    async def test_menu_generation_with_custom_exclusions(self):
        profile = UserProfile(
            telegram_id=99912,
            username="vegan_family",
            first_name="Елена",
            favorite_products=["Авокадо", "Рис длиннозерный"],
            stop_list=["Говядина", "Свинина", "Грибы"],
            allergies=["Глютен"],
            family_size=2,
            plan_days=5
        )
        await db.save_user_profile(profile)

        menu = await menu_generator.generate_menu_for_user(profile, force_new=True)
        self.assertEqual(len(menu.days), 5)
        self.assertTrue(menu.price_comparison.is_live)
        self.assertIsNotNone(menu.price_comparison.checked_at)

        # Verify stop-list excluded
        for day in menu.days:
            for dish in day.dishes:
                dish_text = dish.name.lower() + " " + " ".join(i.name.lower() for i in dish.ingredients)
                for s in profile.stop_list:
                    self.assertNotIn(s.lower(), dish_text)

        # Check total basket calculation across all 3 chains
        comp = menu.price_comparison
        pya_sum = comp.stores["pyaterochka"].total_price
        mag_sum = comp.stores["magnit"].total_price
        len_sum = comp.stores["lenta"].total_price

        self.assertGreater(pya_sum, 0)
        self.assertGreater(mag_sum, 0)
        self.assertGreater(len_sum, 0)
        self.assertIn(comp.cheapest_store, ["Пятерочка", "Магнит", "Лента"])

    # --- 6. KEYBOARD GENERATION & ONBOARDING 1-CLICK DELETE BUTTONS ---
    def test_keyboards_with_custom_items_and_one_click_delete(self):
        # 1. Multi-select with custom items during onboarding
        selected_favs = {"курица", "Спаржа домашняя"}
        kb_fav = get_multi_select_keyboard(POPULAR_FAVORITES, selected_favs, "fav", "fav:next")
        
        # Check that there is a 1-click delete button for "Спаржа домашняя"
        all_cb_data = [btn.callback_data for row in kb_fav.inline_keyboard for btn in row if btn.callback_data]
        self.assertTrue(any(cb.startswith("fav:del:Спаржа") for cb in all_cb_data))
        
        # 2. Profile keyboard generation
        test_profile = UserProfile(
            telegram_id=8888,
            username="tester",
            first_name="Тест",
            favorite_products=["Лосось", "Брокколи"],
            stop_list=["Кинза"],
            allergies=[],
            family_size=3,
            plan_days=7
        )
        kb_prof = build_profile_keyboard(test_profile)
        prof_cb_data = [btn.callback_data for row in kb_prof.inline_keyboard for btn in row if btn.callback_data]
        
        # Check 1-click delete buttons exist
        self.assertTrue(any(cb.startswith("del_fav:Лосось") for cb in prof_cb_data))
        self.assertTrue(any(cb.startswith("del_stop:Кинза") for cb in prof_cb_data))
        
        # Check manual prompt buttons exist
        self.assertIn("add_fav_prompt", prof_cb_data)
        self.assertIn("add_stop_prompt", prof_cb_data)

if __name__ == "__main__":
    unittest.main()

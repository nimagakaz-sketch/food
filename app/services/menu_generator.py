import datetime
import logging
import random
from typing import List, Dict, Any, Optional
from app.database.db import db
from app.database.models import UserProfile, WeeklyMenu, DayMenu, Dish, Ingredient
from app.services.recipe_catalog import RECIPE_CATALOG
from app.services.price_comparator import price_comparator

logger = logging.getLogger("food_bot.menu_generator")

DAY_NAMES = [
    "Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"
]

class MenuGenerator:
    def _is_dish_allowed(self, recipe: Dict[str, Any], stop_list: List[str], allergies: List[str]) -> bool:
        # Check allergies
        recipe_allergens = [a.lower() for a in recipe.get("allergen_tags", [])]
        for allergy in allergies:
            allergy_clean = allergy.strip().lower()
            if not allergy_clean:
                continue
            for r_allergen in recipe_allergens:
                if allergy_clean in r_allergen or r_allergen in allergy_clean:
                    return False
            # Check ingredients against allergy
            for ing in recipe.get("ingredients", []):
                if allergy_clean in ing["name"].lower():
                    return False

        # Check stop-list
        recipe_text = (
            recipe["name"].lower() + " " +
            " ".join(t.lower() for t in recipe.get("tags", [])) + " " +
            " ".join(i["name"].lower() for i in recipe.get("ingredients", []))
        )
        for stop_item in stop_list:
            stop_clean = stop_item.strip().lower()
            if not stop_clean:
                continue
            if stop_clean in recipe_text:
                return False

        return True

    def _score_recipe(self, recipe: Dict[str, Any], favorites: List[str]) -> int:
        score = 10
        recipe_text = (
            recipe["name"].lower() + " " +
            " ".join(t.lower() for t in recipe.get("tags", [])) + " " +
            " ".join(i["name"].lower() for i in recipe.get("ingredients", []))
        )
        for fav in favorites:
            fav_clean = fav.strip().lower()
            if fav_clean and fav_clean in recipe_text:
                score += 25
        return score

    def _scale_dish_for_family(self, recipe: Dict[str, Any], family_size: int) -> Dish:
        scaled_ingredients: List[Ingredient] = []
        for ing in recipe["ingredients"]:
            scaled_ingredients.append(Ingredient(
                name=ing["name"],
                amount=round(ing["amount"] * family_size, 1),
                unit=ing["unit"],
                category=ing.get("category", "бакалея")
            ))

        return Dish(
            id=recipe["id"],
            name=recipe["name"],
            meal_type=recipe["meal_type"],
            meal_name_ru=recipe["meal_name_ru"],
            description=recipe.get("description"),
            cooking_time_min=recipe.get("cooking_time_min", 30),
            calories=recipe.get("calories", 450) * family_size,
            proteins=round(recipe.get("proteins", 25.0) * family_size, 1),
            fats=round(recipe.get("fats", 15.0) * family_size, 1),
            carbs=round(recipe.get("carbs", 40.0) * family_size, 1),
            ingredients=scaled_ingredients,
            tags=recipe.get("tags", [])
        )

    def _aggregate_shopping_list(self, days: List[DayMenu]) -> List[Ingredient]:
        """Combine identical ingredients into one weekly shopping list"""
        agg: Dict[str, Ingredient] = {}
        for day in days:
            for dish in day.dishes:
                for ing in dish.ingredients:
                    key = ing.name.strip().lower()
                    if key in agg:
                        agg[key].amount = round(agg[key].amount + ing.amount, 1)
                    else:
                        agg[key] = Ingredient(
                            name=ing.name,
                            amount=ing.amount,
                            unit=ing.unit,
                            category=ing.category
                        )
        return list(agg.values())

    async def generate_menu_for_user(self, profile: UserProfile, force_new: bool = False) -> WeeklyMenu:
        now = datetime.datetime.now()
        year, week_num, _ = now.isocalendar()

        # Check existing menu if not forcing new
        if not force_new:
            existing = await db.get_current_menu(profile.telegram_id)
            if existing and existing["week_number"] == week_num and existing["year"] == year:
                logger.info(f"Returning existing menu for user {profile.telegram_id} for week {week_num}")
                return WeeklyMenu(
                    id=existing["id"],
                    user_id=profile.telegram_id,
                    week_number=existing["week_number"],
                    year=existing["year"],
                    days=existing["days"],
                    shopping_list=existing["shopping_list"],
                    price_comparison=existing.get("price_comparison"),
                    created_at=existing.get("created_at")
                )

        # Filter recipes
        allowed = [r for r in RECIPE_CATALOG if self._is_dish_allowed(r, profile.stop_list, profile.allergies)]
        if not allowed:
            # If all were filtered out due to excessive stop-list, fallback with least restrictive
            logger.warning(f"No recipes passed strict filter for user {profile.telegram_id}. Falling back.")
            allowed = RECIPE_CATALOG

        breakfasts = [r for r in allowed if r["meal_type"] == "breakfast"] or [r for r in RECIPE_CATALOG if r["meal_type"] == "breakfast"]
        lunches = [r for r in allowed if r["meal_type"] == "lunch"] or [r for r in RECIPE_CATALOG if r["meal_type"] == "lunch"]
        dinners = [r for r in allowed if r["meal_type"] == "dinner"] or [r for r in RECIPE_CATALOG if r["meal_type"] == "dinner"]

        # Score and weight selections
        def pick_variety(pool: List[Dict[str, Any]], count: int) -> List[Dict[str, Any]]:
            scored = [(r, self._score_recipe(r, profile.favorite_products)) for r in pool]
            # Shuffle slightly for freshness
            random.shuffle(scored)
            scored.sort(key=lambda x: x[1], reverse=True)
            chosen = []
            idx = 0
            while len(chosen) < count:
                chosen.append(scored[idx % len(scored)][0])
                idx += 1
            return chosen

        days_count = min(max(profile.plan_days, 1), 7)
        chosen_breakfasts = pick_variety(breakfasts, days_count)
        chosen_lunches = pick_variety(lunches, days_count)
        chosen_dinners = pick_variety(dinners, days_count)

        day_menus: List[DayMenu] = []
        for i in range(days_count):
            day_name = DAY_NAMES[i % len(DAY_NAMES)]
            b_dish = self._scale_dish_for_family(chosen_breakfasts[i], profile.family_size)
            l_dish = self._scale_dish_for_family(chosen_lunches[i], profile.family_size)
            d_dish = self._scale_dish_for_family(chosen_dinners[i], profile.family_size)

            total_cals = b_dish.calories + l_dish.calories + d_dish.calories
            day_menus.append(DayMenu(
                day_number=i + 1,
                day_name=day_name,
                dishes=[b_dish, l_dish, d_dish],
                total_calories=total_cals
            ))

        shopping_list = self._aggregate_shopping_list(day_menus)
        price_comparison = await price_comparator.compare_basket(shopping_list)

        days_json = [d.model_dump() if hasattr(d, "model_dump") else d.dict() for d in day_menus]
        shopping_list_json = [s.model_dump() if hasattr(s, "model_dump") else s.dict() for s in shopping_list]
        price_comparison_json = price_comparison.model_dump() if hasattr(price_comparison, "model_dump") else price_comparison.dict()

        menu_id = await db.save_weekly_menu(
            user_id=profile.telegram_id,
            week_number=week_num,
            year=year,
            days_json=days_json,
            shopping_list_json=shopping_list_json,
            price_comparison_json=price_comparison_json
        )

        return WeeklyMenu(
            id=menu_id,
            user_id=profile.telegram_id,
            week_number=week_num,
            year=year,
            days=day_menus,
            shopping_list=shopping_list,
            price_comparison=price_comparison,
            created_at=now.isoformat()
        )

menu_generator = MenuGenerator()

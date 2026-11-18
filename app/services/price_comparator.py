import logging
from typing import List, Dict, Any, Optional
from app.database.db import db
from app.database.models import Ingredient, StoreItemPrice, StoreBasketTotal, PriceComparison
from app.services.recipe_catalog import BASELINE_STORE_PRICES

logger = logging.getLogger("food_bot.prices")

class PriceComparator:
    def __init__(self):
        self._cached_prices: Dict[str, Dict[str, Any]] = {}

    async def init_prices(self):
        """Seed baseline prices to DB if not present and load into cache"""
        prices = await db.get_all_prices()
        if not prices:
            logger.info("Seeding baseline supermarket prices...")
            for item in BASELINE_STORE_PRICES:
                await db.upsert_price(
                    product_name=item["name"],
                    category=item["category"],
                    unit=item["unit"],
                    p_pyaterochka=item["pyaterochka"],
                    p_magnit=item["magnit"],
                    p_lenta=item["lenta"]
                )
            prices = await db.get_all_prices()
        self._cached_prices = prices
        logger.info(f"Loaded {len(self._cached_prices)} product prices from database.")

    def _normalize_name(self, name: str) -> str:
        return name.strip().lower()

    def _find_price_entry(self, ingredient_name: str) -> Optional[Dict[str, Any]]:
        norm = self._normalize_name(ingredient_name)
        if norm in self._cached_prices:
            return self._cached_prices[norm]
        
        # Substring / fuzzy matching
        for key, val in self._cached_prices.items():
            if key in norm or norm in key:
                return val
            # Common aliases
            if "куриц" in norm and "куриное" in key:
                return val
            if "говядин" in norm and "говядина" in key:
                return val
            if "яйц" in norm and "яйца" in key:
                return val
            if "молок" in norm and "молоко" in key:
                return val
            if "творог" in norm and "творог" in key:
                return val
            if "макарон" in norm or "паст" in norm or "спагетти" in norm:
                if "макаронные" in key:
                    return val
            if "рыб" in norm or "лосось" in norm or "форель" in norm:
                if "рыба" in key:
                    return val

        # Fallback default reasonable prices
        return {
            "product_name": ingredient_name,
            "category": "прочее",
            "unit": "кг",
            "pyaterochka": 150.0,
            "magnit": 145.0,
            "lenta": 155.0
        }

    def _calculate_item_cost(self, amount: float, unit: str, price_entry: Dict[str, Any]) -> tuple[float, float, float]:
        """Convert amount and calculate cost for Pyaterochka, Magnit, Lenta"""
        p_pya = price_entry["pyaterochka"]
        p_mag = price_entry["magnit"]
        p_len = price_entry["lenta"]
        entry_unit = price_entry.get("unit", "кг")

        # Conversion factor to match entry_unit
        if unit == "г" and entry_unit == "кг":
            factor = amount / 1000.0
        elif unit == "кг" and entry_unit == "кг":
            factor = amount
        elif unit == "мл" and entry_unit == "л":
            factor = amount / 1000.0
        elif unit == "л" and entry_unit == "л":
            factor = amount
        elif unit == "шт" and entry_unit == "дес":  # eggs
            factor = amount / 10.0
        elif unit == "шт":
            factor = amount
        else:
            factor = amount / 1000.0 if amount > 20 else amount

        cost_pya = round(factor * p_pya, 2)
        cost_mag = round(factor * p_mag, 2)
        cost_len = round(factor * p_len, 2)
        return cost_pya, cost_mag, cost_len

    async def compare_basket(self, shopping_list: List[Ingredient]) -> PriceComparison:
        """Compare shopping basket across Pyaterochka, Magnit, and Lenta"""
        if not self._cached_prices:
            await self.init_prices()

        item_prices: List[StoreItemPrice] = []
        total_pya = 0.0
        total_mag = 0.0
        total_len = 0.0
        hybrid_cheapest_total = 0.0

        for ing in shopping_list:
            entry = self._find_price_entry(ing.name)
            cost_pya, cost_mag, cost_len = self._calculate_item_cost(ing.amount, ing.unit, entry)

            # Determine best store for this item
            costs = [("Пятерочка", cost_pya), ("Магнит", cost_mag), ("Лента", cost_len)]
            best_store, min_item_cost = min(costs, key=lambda x: x[1])

            total_pya += cost_pya
            total_mag += cost_mag
            total_len += cost_len
            hybrid_cheapest_total += min_item_cost

            item_prices.append(StoreItemPrice(
                product_name=ing.name,
                amount_needed=round(ing.amount, 1),
                unit=ing.unit,
                price_pyaterochka=cost_pya,
                price_magnit=cost_mag,
                price_lenta=cost_len,
                best_store=best_store
            ))

        total_pya = round(total_pya, 2)
        total_mag = round(total_mag, 2)
        total_len = round(total_len, 2)
        hybrid_cheapest_total = round(hybrid_cheapest_total, 2)

        store_totals = {
            "pyaterochka": StoreBasketTotal(
                store_name="Пятерочка",
                store_code="pyaterochka",
                total_price=total_pya
            ),
            "magnit": StoreBasketTotal(
                store_name="Магнит",
                store_code="magnit",
                total_price=total_mag
            ),
            "lenta": StoreBasketTotal(
                store_name="Лента",
                store_code="lenta",
                total_price=total_len
            )
        }

        # Find cheapest single store
        sorted_stores = sorted(store_totals.values(), key=lambda s: s.total_price)
        cheapest_store_obj = sorted_stores[0]
        max_store_obj = sorted_stores[-1]
        
        cheapest_store_obj.is_cheapest = True
        max_savings = round(max_store_obj.total_price - cheapest_store_obj.total_price, 2)

        for s in store_totals.values():
            s.savings_vs_max = round(max_store_obj.total_price - s.total_price, 2)

        hybrid_savings = round(cheapest_store_obj.total_price - hybrid_cheapest_total, 2)
        hybrid_rec = None
        if hybrid_savings > 80:
            hybrid_rec = f"💡 Лайфхак: если купить часть товаров в Магните, а часть в Пятерочке/Ленте, корзина выйдет {int(hybrid_cheapest_total):,} ₽ (дополнительная экономия {int(hybrid_savings)} ₽)!"

        return PriceComparison(
            items=item_prices,
            stores=store_totals,
            cheapest_store=cheapest_store_obj.store_name,
            max_savings=max_savings,
            hybrid_recommendation=hybrid_rec
        )

price_comparator = PriceComparator()

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class ItemActionRequest(BaseModel):
    item: str

class UserProfileCreate(BaseModel):
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    favorite_products: List[str] = Field(default_factory=list)
    stop_list: List[str] = Field(default_factory=list)
    allergies: List[str] = Field(default_factory=list)
    family_size: int = Field(default=2, ge=1, le=15)
    plan_days: int = Field(default=7, ge=1, le=14)

class UserProfile(UserProfileCreate):
    updated_at: Optional[str] = None

class Ingredient(BaseModel):
    name: str
    amount: float
    unit: str  # 'г', 'кг', 'мл', 'л', 'шт', 'уп', 'зубчик'
    category: Optional[str] = "бакалея"

class Dish(BaseModel):
    id: str
    name: str
    meal_type: str  # 'breakfast', 'lunch', 'dinner', 'snack'
    meal_name_ru: str  # 'Завтрак', 'Обед', 'Ужин'
    description: Optional[str] = None
    cooking_time_min: int = 30
    calories: int = 450
    proteins: float = 25.0
    fats: float = 15.0
    carbs: float = 40.0
    ingredients: List[Ingredient]
    tags: List[str] = Field(default_factory=list)

class DayMenu(BaseModel):
    day_number: int
    day_name: str  # 'Понедельник', 'Вторник', ...
    dishes: List[Dish]
    total_calories: int = 0

class StoreItemPrice(BaseModel):
    product_name: str
    amount_needed: float
    unit: str
    price_pyaterochka: float
    price_magnit: float
    price_lenta: float
    best_store: str
    pya_title: Optional[str] = None
    mag_title: Optional[str] = None
    len_title: Optional[str] = None
    is_live: bool = True

class StoreBasketTotal(BaseModel):
    store_name: str
    store_code: str  # 'pyaterochka', 'magnit', 'lenta'
    total_price: float
    is_cheapest: bool = False
    savings_vs_max: float = 0.0

class PriceComparison(BaseModel):
    items: List[StoreItemPrice]
    stores: Dict[str, StoreBasketTotal]
    cheapest_store: str
    max_savings: float
    hybrid_recommendation: Optional[str] = None
    is_live: bool = True
    checked_at: Optional[str] = None

class WeeklyMenu(BaseModel):
    id: Optional[int] = None
    user_id: int
    week_number: int
    year: int
    days: List[DayMenu]
    shopping_list: List[Ingredient]
    price_comparison: Optional[PriceComparison] = None
    created_at: Optional[str] = None

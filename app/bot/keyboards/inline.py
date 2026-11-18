from typing import List, Set
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from app.config import settings

# Predefined quick-select choices for onboarding
POPULAR_FAVORITES = [
    ("🍗 Курица", "курица"),
    ("🥩 Говядина", "говядина"),
    ("🐟 Рыба / Лосось", "рыба"),
    ("🍝 Паста", "паста"),
    ("🥑 Авокадо", "авокадо"),
    ("🧀 Сыр / Творог", "творог"),
    ("🍚 Рис / Басмати", "рис"),
    ("🥦 Овощи", "овощи")
]

POPULAR_STOP_ITEMS = [
    ("🧅 Лук", "лук"),
    ("🍄 Грибы", "грибы"),
    ("🫑 Кинза", "кинза"),
    ("🐷 Свинина", "свинина"),
    ("🧄 Чеснок", "чеснок"),
    ("🥒 Кабачки", "кабачки"),
    ("🥦 Брокколи", "брокколи"),
    ("🫀 Субпродукты", "печень")
]

POPULAR_ALLERGIES = [
    ("🌾 Глютен", "глютен"),
    ("🥛 Лактоза", "лактоза"),
    ("🥜 Орехи", "орехи"),
    ("🦐 Морепродукты", "морепродукты"),
    ("🥚 Яйца", "яйца"),
    ("🌱 Вегетарианство", "мясо")
]

def get_multi_select_keyboard(
    items: List[tuple[str, str]], 
    selected: Set[str], 
    prefix: str, 
    next_callback: str,
    allow_skip: bool = True
) -> InlineKeyboardMarkup:
    """Creates a grid of toggleable items with checkmarks and a Next button"""
    rows = []
    # 2 items per row
    current_row = []
    for label, val in items:
        is_sel = val in selected
        btn_text = f"✅ {label}" if is_sel else label
        cb_data = f"{prefix}:toggle:{val}"
        current_row.append(InlineKeyboardButton(text=btn_text, callback_data=cb_data))
        if len(current_row) == 2:
            rows.append(current_row)
            current_row = []
    if current_row:
        rows.append(current_row)

    # Action row: Next or Skip
    action_row = []
    if allow_skip and not selected:
        action_row.append(InlineKeyboardButton(text="Пропустить ⏭", callback_data=next_callback))
    else:
        action_row.append(InlineKeyboardButton(text="Готово ➡️", callback_data=next_callback))
    
    rows.append(action_row)
    return InlineKeyboardMarkup(inline_keyboard=rows)

def get_family_size_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="1 чел", callback_data="fsize:1"),
            InlineKeyboardButton(text="2 чел", callback_data="fsize:2"),
            InlineKeyboardButton(text="3 чел", callback_data="fsize:3")
        ],
        [
            InlineKeyboardButton(text="4 чел", callback_data="fsize:4"),
            InlineKeyboardButton(text="5+ чел", callback_data="fsize:5")
        ]
    ])

def get_plan_days_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="3 дня", callback_data="pdays:3"),
            InlineKeyboardButton(text="5 дней", callback_data="pdays:5"),
            InlineKeyboardButton(text="7 дней (неделя) ⭐️", callback_data="pdays:7")
        ]
    ])

def get_main_menu_keyboard(has_menu: bool = True) -> InlineKeyboardMarkup:
    rows = []
    if has_menu:
        rows.append([
            InlineKeyboardButton(text="🍽 Меню на неделю", callback_data="view_menu"),
            InlineKeyboardButton(text="🛒 Сравнить цены", callback_data="view_prices")
        ])
        rows.append([
            InlineKeyboardButton(text="🔄 Новое меню", callback_data="regenerate_menu"),
            InlineKeyboardButton(text="⚙️ Мой профиль", callback_data="view_profile")
        ])
    else:
        rows.append([
            InlineKeyboardButton(text="🚀 Заполнить анкету", callback_data="start_onboarding")
        ])

    # Apple WebApp Button
    if settings.WEBAPP_URL:
        rows.append([
            InlineKeyboardButton(text="📱 Открыть Apple WebApp", web_app=WebAppInfo(url=settings.WEBAPP_URL))
        ])

    return InlineKeyboardMarkup(inline_keyboard=rows)

def get_menu_navigation_keyboard(day_count: int, current_day: int = 1) -> InlineKeyboardMarkup:
    day_short = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    row1 = []
    for i in range(min(day_count, 7)):
        txt = f"• {day_short[i]} •" if (i + 1) == current_day else day_short[i]
        row1.append(InlineKeyboardButton(text=txt, callback_data=f"show_day:{i+1}"))
    
    return InlineKeyboardMarkup(inline_keyboard=[
        row1,
        [
            InlineKeyboardButton(text="🛒 Цены в магазинах", callback_data="view_prices"),
            InlineKeyboardButton(text="🔄 Сгенерировать другое", callback_data="regenerate_menu")
        ],
        [
            InlineKeyboardButton(text="📱 Открыть WebApp", web_app=WebAppInfo(url=settings.WEBAPP_URL)),
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="view_profile")
        ]
    ])

def get_prices_view_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📋 Полный список продуктов", callback_data="view_shopping_list")
        ],
        [
            InlineKeyboardButton(text="🍽 Вернуться к меню", callback_data="view_menu"),
            InlineKeyboardButton(text="📱 Открыть в WebApp", web_app=WebAppInfo(url=settings.WEBAPP_URL))
        ]
    ])

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from app.database.db import db
from app.services.menu_generator import menu_generator
from app.bot.keyboards.inline import get_menu_navigation_keyboard, get_main_menu_keyboard

logger = logging.getLogger("food_bot.handlers.menu")
router = Router(name="menu")

def format_day_menu_text(day_data: dict, current_day: int, total_days: int) -> str:
    day_name = day_data.get("day_name", f"День {current_day}")
    total_cals = day_data.get("total_calories", 0)
    
    text = (
        f"📅 *ПЛАН ПИТАНИЯ — {day_name.upper()}* ({current_day}/{total_days})\n"
        f"🔥 Общая калорийность дня: *~{total_cals} ккал*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
    )

    icons = {
        "breakfast": "🍳",
        "lunch": "🍲",
        "dinner": "🥗"
    }

    for dish in day_data.get("dishes", []):
        m_type = dish.get("meal_type", "breakfast")
        icon = icons.get(m_type, "🍽")
        m_ru = dish.get("meal_name_ru", "Блюдо")
        name = dish.get("name", "")
        time_m = dish.get("cooking_time_min", 30)
        cals = dish.get("calories", 0)
        p = dish.get("proteins", 0)
        f = dish.get("fats", 0)
        c = dish.get("carbs", 0)

        text += (
            f"{icon} *{m_ru}: {name}*\n"
            f"⏱ {time_m} мин • ⚡️ {cals} ккал (Б: {p}г | Ж: {f}г | У: {c}г)\n"
            f"_{dish.get('description', '')}_\n\n"
            "🛒 *Ингредиенты на семью:*\n"
        )

        for ing in dish.get("ingredients", []):
            text += f"  • {ing['name']}: *{ing['amount']} {ing['unit']}*\n"
        
        text += "\n"

    text += "💡 Переключайте дни кнопками ниже или нажмите *Цены в магазинах* для расчета корзины."
    return text

@router.message(Command("menu"))
@router.callback_query(F.data == "view_menu")
async def show_weekly_menu(event: Message | CallbackQuery):
    user_id = event.from_user.id
    profile = await db.get_user_profile(user_id)
    if not profile or not profile.plan_days:
        msg = (
            "👋 Чтобы составить персональное меню, сначала пройдите короткую анкету вкусовых предпочтений."
        )
        if isinstance(event, CallbackQuery):
            await event.message.edit_text(msg, reply_markup=get_main_menu_keyboard(has_menu=False))
            await event.answer()
        else:
            await event.answer(msg, reply_markup=get_main_menu_keyboard(has_menu=False))
        return

    menu_obj = await menu_generator.generate_menu_for_user(profile)
    days = [d.model_dump() if hasattr(d, "model_dump") else d for d in menu_obj.days]
    first_day = days[0]

    text = format_day_menu_text(first_day, current_day=1, total_days=len(days))
    kb = get_menu_navigation_keyboard(len(days), current_day=1)

    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)
        await event.answer()
    else:
        await event.answer(text, parse_mode="Markdown", reply_markup=kb)

@router.callback_query(F.data.startswith("show_day:"))
async def switch_menu_day(callback: CallbackQuery):
    day_idx = int(callback.data.split(":")[1])
    user_id = callback.from_user.id
    profile = await db.get_user_profile(user_id)
    menu_obj = await menu_generator.generate_menu_for_user(profile)
    days = [d.model_dump() if hasattr(d, "model_dump") else d for d in menu_obj.days]

    if 1 <= day_idx <= len(days):
        selected_day = days[day_idx - 1]
        text = format_day_menu_text(selected_day, current_day=day_idx, total_days=len(days))
        kb = get_menu_navigation_keyboard(len(days), current_day=day_idx)
        await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)
    await callback.answer()

@router.message(Command("refresh"))
@router.callback_query(F.data == "regenerate_menu")
async def regenerate_menu_action(event: Message | CallbackQuery):
    user_id = event.from_user.id
    profile = await db.get_user_profile(user_id)
    if not profile:
        return

    if isinstance(event, CallbackQuery):
        await event.message.edit_text("🔄 Подбираем новые рецепты и сравниваем цены в Пятерочке, Магните и Ленте...")
    else:
        await event.answer("🔄 Подбираем новые рецепты и сравниваем цены...")

    menu_obj = await menu_generator.generate_menu_for_user(profile, force_new=True)
    days = [d.model_dump() if hasattr(d, "model_dump") else d for d in menu_obj.days]
    first_day = days[0]

    text = "✨ *Новое меню успешно сгенерировано!*\n\n" + format_day_menu_text(first_day, current_day=1, total_days=len(days))
    kb = get_menu_navigation_keyboard(len(days), current_day=1)

    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)
        await event.answer("Меню обновлено!")
    else:
        await event.answer(text, parse_mode="Markdown", reply_markup=kb)

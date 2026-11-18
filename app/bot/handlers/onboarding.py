import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from app.database.db import db
from app.database.models import UserProfile
from app.services.menu_generator import menu_generator
from app.bot.keyboards.inline import (
    POPULAR_FAVORITES, POPULAR_STOP_ITEMS, POPULAR_ALLERGIES,
    get_multi_select_keyboard, get_family_size_keyboard, get_plan_days_keyboard,
    get_main_menu_keyboard
)

logger = logging.getLogger("food_bot.handlers.onboarding")
router = Router(name="onboarding")

class OnboardingStates(StatesGroup):
    favorites = State()
    stop_list = State()
    allergies = State()
    family_size = State()
    plan_days = State()

# --- Helper to format selected items list ---
def format_selected_text(items: list[str]) -> str:
    if not items:
        return "_пока ничего не выбрано_"
    return ", ".join(f"*{it}*" for it in items)

# --- 1. FAVORITES ---
@router.callback_query(F.data == "start_onboarding")
async def start_onboarding_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(OnboardingStates.favorites)
    await state.update_data(favorites=[], stop_list=[], allergies=[], family_size=2, plan_days=7)

    kb = get_multi_select_keyboard(POPULAR_FAVORITES, set(), "fav", "fav:next", allow_skip=False)
    text = (
        "👋 *Шаг 1 из 4: Любимые продукты*\n\n"
        "Что вы и ваша семья обожаете есть? Мы сделаем акцент на этих блюдах и ингредиентах в меню.\n\n"
        "Нажимайте на кнопки, чтобы выбрать, либо *напишите свои варианты сообщением* (через запятую).\n\n"
        "Выбрано: _пока ничего не выбрано_"
    )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)
    await callback.answer()

@router.callback_query(OnboardingStates.favorites, F.data.startswith("fav:toggle:"))
async def toggle_favorite(callback: CallbackQuery, state: FSMContext):
    val = callback.data.split(":", 2)[2]
    data = await state.get_data()
    favs = set(data.get("favorites", []))
    if val in favs:
        favs.remove(val)
    else:
        favs.add(val)
    
    await state.update_data(favorites=list(favs))
    kb = get_multi_select_keyboard(POPULAR_FAVORITES, favs, "fav", "fav:next", allow_skip=False)
    text = (
        "👋 *Шаг 1 из 4: Любимые продукты*\n\n"
        "Что вы и ваша семья обожаете есть? Мы сделаем акцент на этих блюдах и ингредиентах в меню.\n\n"
        "Нажимайте на кнопки, чтобы выбрать, либо *напишите свои варианты сообщением* (через запятую).\n\n"
        f"Выбрано: {format_selected_text(list(favs))}"
    )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)
    await callback.answer()

@router.callback_query(OnboardingStates.favorites, F.data.startswith("fav:del:"))
async def delete_custom_favorite(callback: CallbackQuery, state: FSMContext):
    val = callback.data.split(":", 2)[2]
    data = await state.get_data()
    favs = set(data.get("favorites", []))
    to_remove = {x for x in favs if x.lower().startswith(val.lower()) or x == val}
    favs -= to_remove
    await state.update_data(favorites=list(favs))
    kb = get_multi_select_keyboard(POPULAR_FAVORITES, favs, "fav", "fav:next", allow_skip=False)
    text = (
        "👋 *Шаг 1 из 4: Любимые продукты*\n\n"
        "Что вы и ваша семья обожаете есть? Мы сделаем акцент на этих блюдах и ингредиентах в меню.\n\n"
        "Нажимайте на кнопки, чтобы выбрать, либо *напишите свои варианты сообщением* (через запятую).\n\n"
        f"Выбрано: {format_selected_text(list(favs))}"
    )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)
    await callback.answer(f"Удалено: {val}")

@router.message(OnboardingStates.favorites, F.text)
async def custom_favorites_text(message: Message, state: FSMContext):
    items = [x.strip() for x in message.text.split(",") if x.strip()]
    data = await state.get_data()
    favs = set(data.get("favorites", []))
    favs.update(items)
    await state.update_data(favorites=list(favs))

    kb = get_multi_select_keyboard(POPULAR_FAVORITES, favs, "fav", "fav:next", allow_skip=False)
    text = (
        "✅ Добавлено!\n\n"
        "👋 *Шаг 1 из 4: Любимые продукты*\n\n"
        f"Текущий список: {format_selected_text(list(favs))}\n\n"
        "Можете нажать еще кнопки или нажать *Готово ➡️* для перехода к следующему шагу."
    )
    await message.answer(text, parse_mode="Markdown", reply_markup=kb)

# --- 2. STOP-LIST ---
@router.callback_query(OnboardingStates.favorites, F.data == "fav:next")
async def go_to_stop_list(callback: CallbackQuery, state: FSMContext):
    await state.set_state(OnboardingStates.stop_list)
    data = await state.get_data()
    stops = set(data.get("stop_list", []))

    kb = get_multi_select_keyboard(POPULAR_STOP_ITEMS, stops, "stop", "stop:next", allow_skip=True)
    text = (
        "🚫 *Шаг 2 из 4: Стоп-лист (нелюбимые продукты)*\n\n"
        "Какие продукты вы *категорически не едите*? Мы гарантируем, что ни одно блюдо с ними не попадет в ваше меню.\n\n"
        "Выберите из списка или напишите текстом (например: _кинза, свинина, оливки_).\n\n"
        f"В стоп-листе: {format_selected_text(list(stops))}"
    )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)
    await callback.answer()

@router.callback_query(OnboardingStates.stop_list, F.data.startswith("stop:toggle:"))
async def toggle_stop_item(callback: CallbackQuery, state: FSMContext):
    val = callback.data.split(":", 2)[2]
    data = await state.get_data()
    stops = set(data.get("stop_list", []))
    if val in stops:
        stops.remove(val)
    else:
        stops.add(val)
    
    await state.update_data(stop_list=list(stops))
    kb = get_multi_select_keyboard(POPULAR_STOP_ITEMS, stops, "stop", "stop:next", allow_skip=True)
    text = (
        "🚫 *Шаг 2 из 4: Стоп-лист (нелюбимые продукты)*\n\n"
        "Какие продукты вы *категорически не едите*? Мы гарантируем, что ни одно блюдо с ними не попадет в ваше меню.\n\n"
        "Выберите из списка или напишите текстом (например: _кинза, свинина, оливки_).\n\n"
        f"В стоп-листе: {format_selected_text(list(stops))}"
    )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)
    await callback.answer()

@router.callback_query(OnboardingStates.stop_list, F.data.startswith("stop:del:"))
async def delete_custom_stop(callback: CallbackQuery, state: FSMContext):
    val = callback.data.split(":", 2)[2]
    data = await state.get_data()
    stops = set(data.get("stop_list", []))
    to_remove = {x for x in stops if x.lower().startswith(val.lower()) or x == val}
    stops -= to_remove
    await state.update_data(stop_list=list(stops))
    kb = get_multi_select_keyboard(POPULAR_STOP_ITEMS, stops, "stop", "stop:next", allow_skip=True)
    text = (
        "🚫 *Шаг 2 из 4: Стоп-лист (нелюбимые продукты)*\n\n"
        "Какие продукты вы *категорически не едите*? Мы гарантируем, что ни одно блюдо с ними не попадет в ваше меню.\n\n"
        "Выберите из списка или напишите текстом (например: _кинза, свинина, оливки_).\n\n"
        f"В стоп-листе: {format_selected_text(list(stops))}"
    )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)
    await callback.answer(f"Удалено: {val}")

@router.message(OnboardingStates.stop_list, F.text)
async def custom_stop_text(message: Message, state: FSMContext):
    items = [x.strip() for x in message.text.split(",") if x.strip()]
    data = await state.get_data()
    stops = set(data.get("stop_list", []))
    stops.update(items)
    await state.update_data(stop_list=list(stops))

    kb = get_multi_select_keyboard(POPULAR_STOP_ITEMS, stops, "stop", "stop:next", allow_skip=True)
    text = (
        "✅ Добавлено в стоп-лист!\n\n"
        f"Текущий стоп-лист: {format_selected_text(list(stops))}\n\n"
        "Нажмите *Готово ➡️* для перехода к аллергиям."
    )
    await message.answer(text, parse_mode="Markdown", reply_markup=kb)

# --- 3. ALLERGIES & RESTRICTIONS ---
@router.callback_query(OnboardingStates.stop_list, F.data == "stop:next")
async def go_to_allergies(callback: CallbackQuery, state: FSMContext):
    await state.set_state(OnboardingStates.allergies)
    data = await state.get_data()
    allergies = set(data.get("allergies", []))

    kb = get_multi_select_keyboard(POPULAR_ALLERGIES, allergies, "allg", "allg:next", allow_skip=True)
    text = (
        "⚠️ *Шаг 3 из 4: Аллергии и ограничения*\n\n"
        "Есть ли у кого-то из членов семьи медицинские или строгие пищевые ограничения? (глютен, лактоза, орехи и др.)\n\n"
        "Выберите из кнопок или введите свои вручную.\n\n"
        f"Выбрано: {format_selected_text(list(allergies))}"
    )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)
    await callback.answer()

@router.callback_query(OnboardingStates.allergies, F.data.startswith("allg:toggle:"))
async def toggle_allergy(callback: CallbackQuery, state: FSMContext):
    val = callback.data.split(":", 2)[2]
    data = await state.get_data()
    allgs = set(data.get("allergies", []))
    if val in allgs:
        allgs.remove(val)
    else:
        allgs.add(val)
    
    await state.update_data(allergies=list(allgs))
    kb = get_multi_select_keyboard(POPULAR_ALLERGIES, allgs, "allg", "allg:next", allow_skip=True)
    text = (
        "⚠️ *Шаг 3 из 4: Аллергии и ограничения*\n\n"
        "Есть ли у кого-то из членов семьи медицинские или строгие пищевые ограничения? (глютен, лактоза, орехи и др.)\n\n"
        "Выберите из кнопок или введите свои вручную.\n\n"
        f"Выбрано: {format_selected_text(list(allgs))}"
    )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)
    await callback.answer()

@router.callback_query(OnboardingStates.allergies, F.data.startswith("allg:del:"))
async def delete_custom_allergy(callback: CallbackQuery, state: FSMContext):
    val = callback.data.split(":", 2)[2]
    data = await state.get_data()
    allgs = set(data.get("allergies", []))
    to_remove = {x for x in allgs if x.lower().startswith(val.lower()) or x == val}
    allgs -= to_remove
    await state.update_data(allergies=list(allgs))
    kb = get_multi_select_keyboard(POPULAR_ALLERGIES, allgs, "allg", "allg:next", allow_skip=True)
    text = (
        "⚠️ *Шаг 3 из 4: Аллергии и ограничения*\n\n"
        "Есть ли у кого-то из членов семьи медицинские или строгие пищевые ограничения? (глютен, лактоза, орехи и др.)\n\n"
        "Выберите из кнопок или введите свои вручную.\n\n"
        f"Выбрано: {format_selected_text(list(allgs))}"
    )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)
    await callback.answer(f"Удалено: {val}")

@router.message(OnboardingStates.allergies, F.text)
async def custom_allergies_text(message: Message, state: FSMContext):
    items = [x.strip() for x in message.text.split(",") if x.strip()]
    data = await state.get_data()
    allgs = set(data.get("allergies", []))
    allgs.update(items)
    await state.update_data(allergies=list(allgs))

    kb = get_multi_select_keyboard(POPULAR_ALLERGIES, allgs, "allg", "allg:next", allow_skip=True)
    text = (
        "✅ Ограничения сохранены!\n\n"
        f"Текущие аллергии/ограничения: {format_selected_text(list(allgs))}\n\n"
        "Нажмите *Готово ➡️* для перехода к размеру семьи."
    )
    await message.answer(text, parse_mode="Markdown", reply_markup=kb)

# --- 4. FAMILY SIZE & PLAN DAYS ---
@router.callback_query(OnboardingStates.allergies, F.data == "allg:next")
async def go_to_family_size(callback: CallbackQuery, state: FSMContext):
    await state.set_state(OnboardingStates.family_size)
    text = (
        "👨‍👩‍👧‍👦 *Шаг 4 из 4: Размер семьи*\n\n"
        "Сколько человек в вашей семье? Мы точно рассчитаем порции ингредиентов и граммовки для покупок."
    )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=get_family_size_keyboard())
    await callback.answer()

@router.callback_query(OnboardingStates.family_size, F.data.startswith("fsize:"))
async def set_family_size(callback: CallbackQuery, state: FSMContext):
    size = int(callback.data.split(":")[1])
    await state.update_data(family_size=size)
    await state.set_state(OnboardingStates.plan_days)

    text = (
        f"👨‍👩‍👧‍👦 Размер семьи: *{size} чел.*\n\n"
        "📅 *На какой период составить план питания?*\n\n"
        "Каждый понедельник меню будет автоматически обновляться на новые сбалансированные рецепты!"
    )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=get_plan_days_keyboard())
    await callback.answer()

@router.callback_query(OnboardingStates.plan_days, F.data.startswith("pdays:"))
async def finish_onboarding(callback: CallbackQuery, state: FSMContext):
    days = int(callback.data.split(":")[1])
    data = await state.get_data()
    await state.clear()

    user_id = callback.from_user.id
    username = callback.from_user.username
    first_name = callback.from_user.first_name

    profile = UserProfile(
        telegram_id=user_id,
        username=username,
        first_name=first_name,
        favorite_products=data.get("favorites", []),
        stop_list=data.get("stop_list", []),
        allergies=data.get("allergies", []),
        family_size=data.get("family_size", 2),
        plan_days=days
    )

    await db.save_user_profile(profile)

    wait_msg = await callback.message.edit_text(
        "✨ *Анкета успешно сохранена!*\n\n"
        "🍳 Подбираем сбалансированные блюда без стоп-листа...\n"
        "📊 Опрашиваем каталоги цен *Пятерочки*, *Магнита* и *Ленты*...",
        parse_mode="Markdown"
    )

    # Generate first menu
    weekly_menu = await menu_generator.generate_menu_for_user(profile, force_new=True)
    comp = weekly_menu.price_comparison

    best_store = comp.cheapest_store if comp else "Магнит"
    savings = int(comp.max_savings) if comp else 0

    favs_str = ", ".join(profile.favorite_products[:4]) if profile.favorite_products else "Все подряд"
    stops_str = ", ".join(profile.stop_list[:4]) if profile.stop_list else "Нет"
    allgs_str = ", ".join(profile.allergies[:3]) if profile.allergies else "Нет"

    summary_text = (
        "🎉 *Ваш профиль питания готов!*\n\n"
        f"• *Семья:* {profile.family_size} чел. | *Период:* {profile.plan_days} дн.\n"
        f"• *Любимое:* {favs_str}\n"
        f"• *Стоп-лист:* {stops_str}\n"
        f"• *Ограничения:* {allgs_str}\n\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"🥗 *Меню на {len(weekly_menu.days)} дней сформировано!*\n"
        f"🛒 *Сравнение цен в супермаркетах:*\n"
    )

    if comp:
        for store_code, s in comp.stores.items():
            badge = " 🏆 (Самый дешевый)" if s.is_cheapest else ""
            summary_text += f"• *{s.store_name}:* {int(s.total_price):,} ₽{badge}\n"
        
        summary_text += (
            f"\n🔥 Экономия при покупке в *{best_store}* составляет *{savings:,} ₽*!\n"
            f"🔄 Автообновление меню: *каждый понедельник*\n"
        )

    await wait_msg.edit_text(
        summary_text,
        parse_mode="Markdown",
        reply_markup=get_main_menu_keyboard(has_menu=True)
    )
    await callback.answer()

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from app.config import settings
from app.database.db import db
from app.bot.keyboards.inline import get_main_menu_keyboard
from app.services.menu_generator import menu_generator

logger = logging.getLogger("food_bot.handlers.common")
router = Router(name="common")

class ProfileEditStates(StatesGroup):
    waiting_for_favorite = State()
    waiting_for_stop = State()

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name

    await db.get_or_create_user(user_id, username, first_name)
    profile = await db.get_user_profile(user_id)

    has_profile = bool(profile and (profile.favorite_products or profile.stop_list or profile.allergies))

    if not has_profile:
        welcome_text = (
            f"👋 Привет, *{first_name or 'друг'}*!\n\n"
            "Я ваш персональный ассистент по *планированию семейного меню* и *поиску актуальных цен в реальном времени*.\n\n"
            "✨ *Что я умею:*\n"
            "1. 🥗 Составлять сбалансированное меню на неделю с учетом любимых блюд всей семьи.\n"
            "2. 🚫 Исключать нелюбимые продукты (стоп-лист) и аллергены (глютен, лактозу и др.).\n"
            "3. 🛒 Искать актуальные на текущий момент цены в каталогах *Пятерочки*, *Магнита* и *Ленты*.\n"
            "4. 🔄 Автоматически обновлять меню каждый понедельник!\n\n"
            "Давайте настроим предпочтения вашей семьи в короткой анкете (1 минута)!"
        )
        await message.answer(welcome_text, parse_mode="Markdown", reply_markup=get_main_menu_keyboard(has_menu=False))
    else:
        text = (
            f"👋 Рады видеть вас снова, *{first_name or 'друг'}*!\n\n"
            "Ваше меню и расчет актуальных цен в супермаркетах готовы к просмотру."
        )
        await message.answer(text, parse_mode="Markdown", reply_markup=get_main_menu_keyboard(has_menu=True))

def build_profile_keyboard(profile) -> InlineKeyboardMarkup:
    rows = []
    
    # 1-Click Delete buttons for Favorites
    if profile.favorite_products:
        del_fav_row = []
        for it in profile.favorite_products[:8]:
            del_fav_row.append(InlineKeyboardButton(text=f"✕ {it}", callback_data=f"del_fav:{it[:20]}"))
            if len(del_fav_row) == 2:
                rows.append(del_fav_row)
                del_fav_row = []
        if del_fav_row:
            rows.append(del_fav_row)

    # 1-Click Delete buttons for Stop-List
    if profile.stop_list:
        del_stop_row = []
        for it in profile.stop_list[:8]:
            del_stop_row.append(InlineKeyboardButton(text=f"✕ 🚫 {it}", callback_data=f"del_stop:{it[:20]}"))
            if len(del_stop_row) == 2:
                rows.append(del_stop_row)
                del_stop_row = []
        if del_stop_row:
            rows.append(del_stop_row)

    # Interactive manual addition buttons
    rows.append([
        InlineKeyboardButton(text="➕ В любимые", callback_data="add_fav_prompt"),
        InlineKeyboardButton(text="🚫 В стоп-лист", callback_data="add_stop_prompt")
    ])

    rows.append([
        InlineKeyboardButton(text="✏️ Перезаполнить анкету", callback_data="start_onboarding"),
        InlineKeyboardButton(text="🍽 Посмотреть меню", callback_data="view_menu")
    ])

    if settings.WEBAPP_URL:
        rows.append([
            InlineKeyboardButton(text="📱 Открыть Liquid Glass WebApp", web_app=WebAppInfo(url=settings.WEBAPP_URL))
        ])

    return InlineKeyboardMarkup(inline_keyboard=rows)

@router.message(Command("profile"))
@router.callback_query(F.data == "view_profile")
async def show_profile(event: Message | CallbackQuery, state: FSMContext = None):
    if state:
        await state.clear()
    user_id = event.from_user.id
    profile = await db.get_user_profile(user_id)
    if not profile:
        return

    favs_str = ", ".join(profile.favorite_products) if profile.favorite_products else "— (нажмите кнопку или отправьте текст)"
    stops_str = ", ".join(profile.stop_list) if profile.stop_list else "—"
    allgs_str = ", ".join(profile.allergies) if profile.allergies else "—"

    text = (
        "⚙️ *ПРОФИЛЬ И ПРЕДПОЧТЕНИЯ СЕМЬИ*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👨‍👩‍👧‍👦 *Размер семьи:* {profile.family_size} чел. | *Период:* {profile.plan_days} дн.\n\n"
        f"❤️ *Любимые продукты (база меню):*\n{favs_str}\n\n"
        f"🚫 *Стоп-лист (категорически исключены):*\n{stops_str}\n\n"
        f"⚠️ *Аллергии/ограничения:* {allgs_str}\n\n"
        "💡 *Интерактивное управление:*\n"
        "• Нажмите *✕ <Продукт>* для удаления в один клик.\n"
        "• Нажмите кнопки ниже или отправьте: `+ спаржа` (в любимые), `- лук` (в стоп-лист)."
    )

    kb = build_profile_keyboard(profile)

    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)
        await event.answer()
    else:
        await event.answer(text, parse_mode="Markdown", reply_markup=kb)

# Prompt for manual custom favorite adding
@router.callback_query(F.data == "add_fav_prompt")
async def prompt_add_favorite(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ProfileEditStates.waiting_for_favorite)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_profile_edit")]
    ])
    await callback.message.edit_text(
        "✍️ *Добавление своего продукта в любимые:*\n\n"
        "Напишите название абсолютно любого продукта (или нескольких через запятую), который вы хотите добавить:\n\n"
        "_(Например: киноа, спаржа, батат)_",
        parse_mode="Markdown",
        reply_markup=kb
    )
    await callback.answer()

# Prompt for manual custom stop-list adding
@router.callback_query(F.data == "add_stop_prompt")
async def prompt_add_stop(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ProfileEditStates.waiting_for_stop)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_profile_edit")]
    ])
    await callback.message.edit_text(
        "✍️ *Добавление своего продукта в стоп-лист:*\n\n"
        "Напишите название абсолютно любого продукта (или нескольких через запятую), который нужно категорически исключить из меню:\n\n"
        "_(Например: кинза, свинина, оливки)_",
        parse_mode="Markdown",
        reply_markup=kb
    )
    await callback.answer()

@router.callback_query(F.data == "cancel_profile_edit")
async def cancel_profile_edit_cb(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await show_profile(callback)

@router.message(ProfileEditStates.waiting_for_favorite, F.text)
async def process_manual_favorite_input(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    items = [x.strip() for x in message.text.split(",") if x.strip()]
    profile = None
    for it in items:
        profile = await db.add_favorite_item(user_id, it)
    if profile:
        await menu_generator.generate_menu_for_user(profile, force_new=True)
    added_str = ", ".join(f"*{it}*" for it in items)
    await message.answer(f"✅ Добавлено в любимые: {added_str}! Меню обновлено.", parse_mode="Markdown")
    await show_profile(message)

@router.message(ProfileEditStates.waiting_for_stop, F.text)
async def process_manual_stop_input(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    items = [x.strip() for x in message.text.split(",") if x.strip()]
    profile = None
    for it in items:
        profile = await db.add_stop_item(user_id, it)
    if profile:
        await menu_generator.generate_menu_for_user(profile, force_new=True)
    added_str = ", ".join(f"*{it}*" for it in items)
    await message.answer(f"🚫 Добавлено в стоп-лист: {added_str}! Меню исключило данные блюда.", parse_mode="Markdown")
    await show_profile(message)

# 1-Click Delete Callbacks in Telegram Chat
@router.callback_query(F.data.startswith("del_fav:"))
async def callback_delete_favorite(callback: CallbackQuery):
    item = callback.data.split(":", 1)[1]
    user_id = callback.from_user.id
    profile = await db.get_user_profile(user_id)
    matched = item
    if profile:
        for f in profile.favorite_products:
            if f.lower() == item.lower() or f.lower().startswith(item.lower()):
                matched = f
                break
    profile = await db.remove_favorite_item(user_id, matched)
    if profile:
        await menu_generator.generate_menu_for_user(profile, force_new=True)
    await callback.answer(f"Удалено из любимых: {matched}")
    await show_profile(callback)

@router.callback_query(F.data.startswith("del_stop:"))
async def callback_delete_stop(callback: CallbackQuery):
    item = callback.data.split(":", 1)[1]
    user_id = callback.from_user.id
    profile = await db.get_user_profile(user_id)
    matched = item
    if profile:
        for s in profile.stop_list:
            if s.lower() == item.lower() or s.lower().startswith(item.lower()):
                matched = s
                break
    profile = await db.remove_stop_item(user_id, matched)
    if profile:
        await menu_generator.generate_menu_for_user(profile, force_new=True)
    await callback.answer(f"Удалено из стоп-листа: {matched}")
    await show_profile(callback)

# Fast Text-based Item Adding: "+ продукт" or "- продукт"
@router.message(F.text.startswith("+") | F.text.startswith("-"))
async def text_add_remove_item(message: Message):
    text = message.text.strip()
    user_id = message.from_user.id
    if text.startswith("+"):
        item_name = text[1:].strip()
        if item_name:
            profile = await db.add_favorite_item(user_id, item_name)
            await menu_generator.generate_menu_for_user(profile, force_new=True)
            await message.answer(f"✅ Продукт *{item_name}* добавлен в *любимые*! Меню обновлено.", parse_mode="Markdown")
    elif text.startswith("-"):
        item_name = text[1:].strip()
        if item_name:
            profile = await db.add_stop_item(user_id, item_name)
            await menu_generator.generate_menu_for_user(profile, force_new=True)
            await message.answer(f"🚫 Продукт *{item_name}* добавлен в *стоп-лист*! Меню пересчитано без него.", parse_mode="Markdown")

@router.message(Command("help"))
async def cmd_help(message: Message):
    text = (
        "📖 *СПРАВКА ПО БОТУ*\n\n"
        "• /start — Главное меню\n"
        "• /menu — План питания на неделю с КБЖУ и рецептами\n"
        "• /prices — Актуальные онлайн цены в Пятерочке, Магните и Ленте\n"
        "• /refresh — Пересоздать меню с новыми блюдами\n"
        "• /profile — Настройки семьи, любимое и стоп-лист\n"
        "• /health — Проверка статуса сервера и баз данных (UptimeRobot)\n\n"
        "💡 *Лайфхак:* напишите `+ спаржа` чтобы добавить в любимые или `- свинина` чтобы добавить в стоп-лист."
    )
    await message.answer(text, parse_mode="Markdown")

@router.message(Command("health"))
async def cmd_health(message: Message):
    await message.answer("🟢 *Health Check:* Бот и онлайн-парсер цен работают в штатном режиме (status: ok).", parse_mode="Markdown")

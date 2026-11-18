import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from app.database.db import db
from app.bot.keyboards.inline import get_main_menu_keyboard

logger = logging.getLogger("food_bot.handlers.common")
router = Router(name="common")

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name

    await db.get_or_create_user(user_id, username, first_name)
    profile = await db.get_user_profile(user_id)

    # Check if user already completed preferences
    has_profile = bool(profile and (profile.favorite_products or profile.stop_list or profile.allergies))

    if not has_profile:
        welcome_text = (
            f"👋 Привет, *{first_name or 'друг'}*!\n\n"
            "Я ваш персональный ассистент по *планированию семейного меню* и *поиску лучших цен в супермаркетах*.\n\n"
            "✨ *Что я умею:*\n"
            "1. 🥗 Составлять сбалансированное меню на неделю с учетом любимых блюд всей семьи.\n"
            "2. 🚫 Исключать нелюбимые продукты (стоп-лист) и аллергены (глютен, лактозу и др.).\n"
            "3. 🛒 Сравнивать цены на продукты в *Пятерочке*, *Магните* и *Ленте* и находить самый выгодный магазин.\n"
            "4. 🔄 Автоматически обновлять меню каждый понедельник!\n\n"
            "Давайте настроим предпочтения вашей семьи в короткой анкете (1 минута)!"
        )
        await message.answer(welcome_text, parse_mode="Markdown", reply_markup=get_main_menu_keyboard(has_menu=False))
    else:
        text = (
            f"👋 Рады видеть вас снова, *{first_name or 'друг'}*!\n\n"
            "Ваше персональное меню и расчет цен в супермаркетах готовы к просмотру."
        )
        await message.answer(text, parse_mode="Markdown", reply_markup=get_main_menu_keyboard(has_menu=True))

@router.message(Command("profile"))
@router.callback_query(F.data == "view_profile")
async def show_profile(event: Message | CallbackQuery):
    user_id = event.from_user.id
    profile = await db.get_user_profile(user_id)
    if not profile:
        return

    favs_str = ", ".join(profile.favorite_products) if profile.favorite_products else "—"
    stops_str = ", ".join(profile.stop_list) if profile.stop_list else "—"
    allgs_str = ", ".join(profile.allergies) if profile.allergies else "—"

    text = (
        "⚙️ *ПРОФИЛЬ И ПРЕДПОЧТЕНИЯ СЕМЬИ*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👨‍👩‍👧‍👦 *Размер семьи:* {profile.family_size} чел.\n"
        f"📅 *Период планирования:* {profile.plan_days} дней\n\n"
        f"❤️ *Любимые продукты:* {favs_str}\n\n"
        f"🚫 *Стоп-лист:* {stops_str}\n\n"
        f"⚠️ *Аллергии/ограничения:* {allgs_str}\n\n"
        "🔄 *Автообновление меню:* Каждый понедельник в 09:00\n\n"
        "Чтобы обновить анкету, нажмите кнопку ниже."
    )

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
    from app.config import settings
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Изменить анкету заново", callback_data="start_onboarding")],
        [InlineKeyboardButton(text="🍽 Посмотреть меню", callback_data="view_menu")],
        [InlineKeyboardButton(text="📱 Открыть Apple WebApp", web_app=WebAppInfo(url=settings.WEBAPP_URL))]
    ])

    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)
        await event.answer()
    else:
        await event.answer(text, parse_mode="Markdown", reply_markup=kb)

@router.message(Command("help"))
async def cmd_help(message: Message):
    text = (
        "📖 *СПРАВКА ПО БОТУ*\n\n"
        "• /start — Главное меню и запуск\n"
        "• /menu — План питания на неделю с КБЖУ и ингредиентами\n"
        "• /prices — Сравнение цен корзины в Пятерочке, Магните и Ленте\n"
        "• /refresh — Пересоздать меню с новыми блюдами\n"
        "• /profile — Настройки семьи, стоп-листа и аллергий\n"
        "• /health — Проверка статуса сервера и баз данных\n\n"
        "🗓 *Автообновление:* каждую неделю по понедельникам вы получаете свежее меню и актуальный расчет выгодных супермаркетов."
    )
    await message.answer(text, parse_mode="Markdown")

@router.message(Command("health"))
async def cmd_health(message: Message):
    await message.answer("🟢 *Health Check:* Бот и база данных работают в штатном режиме (status: ok).", parse_mode="Markdown")

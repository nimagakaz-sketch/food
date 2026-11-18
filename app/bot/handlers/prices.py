import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from app.database.db import db
from app.services.menu_generator import menu_generator
from app.bot.keyboards.inline import get_prices_view_keyboard

logger = logging.getLogger("food_bot.handlers.prices")
router = Router(name="prices")

@router.message(Command("prices"))
@router.callback_query(F.data == "view_prices")
async def show_price_comparison(event: Message | CallbackQuery):
    user_id = event.from_user.id
    profile = await db.get_user_profile(user_id)
    if not profile:
        return

    menu_obj = await menu_generator.generate_menu_for_user(profile)
    comp = menu_obj.price_comparison

    if not comp:
        text = "Цены пока не рассчитаны. Попробуйте обновить меню."
        if isinstance(event, CallbackQuery):
            await event.message.edit_text(text)
            await event.answer()
        else:
            await event.answer(text)
        return

    stores = comp.stores if isinstance(comp.stores, dict) else (comp.stores.model_dump() if hasattr(comp.stores, "model_dump") else comp.stores.dict())
    items = comp.items if isinstance(comp.items, list) else []

    best_store = comp.cheapest_store
    savings = int(comp.max_savings)

    text = (
        "🛒 *СРАВНЕНИЕ ЦЕН В СУПЕРМАРКЕТАХ*\n"
        f"Расчет полной корзины на семью из {profile.family_size} чел. на {profile.plan_days} дн.:\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
    )

    # Store Totals
    store_emojis = {
        "pyaterochka": "🔴",
        "magnit": "🟡",
        "lenta": "🔵"
    }

    # Sort stores by price
    sorted_stores = sorted(
        stores.values(),
        key=lambda s: s.get("total_price", 0) if isinstance(s, dict) else s.total_price
    )

    for idx, s in enumerate(sorted_stores):
        s_dict = s if isinstance(s, dict) else s.dict()
        s_code = s_dict.get("store_code", "")
        s_name = s_dict.get("store_name", "")
        total = int(s_dict.get("total_price", 0))
        emoji = store_emojis.get(s_code, "🏬")

        if idx == 0:
            text += f"{emoji} *{s_name}:* *{total:,} ₽* 🏆 *(Самый выгодный!)*\n"
        else:
            diff = total - int(sorted_stores[0].get("total_price", 0) if isinstance(sorted_stores[0], dict) else sorted_stores[0].total_price)
            text += f"{emoji} *{s_name}:* {total:,} ₽ _(+{diff:,} ₽)_\n"

    text += (
        f"\n💡 *Экономия:* покупая в *{best_store}*, вы бережете *{savings:,} ₽* по сравнению с самым дорогим магазином!\n"
    )

    if comp.hybrid_recommendation:
        text += f"\n{comp.hybrid_recommendation}\n"

    text += "\n📊 *Детализация цен по ключевым продуктам:*\n"
    text += "_(Пят. / Магн. / Лента)_\n\n"

    # Show top items breakdown
    for it in items[:12]:
        it_dict = it if isinstance(it, dict) else it.dict()
        p_name = it_dict.get("product_name", "")
        amt = it_dict.get("amount_needed", 0)
        unit = it_dict.get("unit", "")
        p_pya = int(it_dict.get("price_pyaterochka", 0))
        p_mag = int(it_dict.get("price_magnit", 0))
        p_len = int(it_dict.get("price_lenta", 0))

        # highlight minimum
        min_p = min(p_pya, p_mag, p_len)
        def fmt_price(p):
            return f"*{p}*₽" if p == min_p else f"{p}₽"

        text += f"• *{p_name}* ({amt} {unit}):\n"
        text += f"   Пят: {fmt_price(p_pya)} | Магн: {fmt_price(p_mag)} | Лента: {fmt_price(p_len)}\n"

    text += "\n📱 Нажмите кнопку ниже для полного интерактивного списка или WebApp."

    kb = get_prices_view_keyboard()
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)
        await event.answer()
    else:
        await event.answer(text, parse_mode="Markdown", reply_markup=kb)

@router.callback_query(F.data == "view_shopping_list")
async def show_full_shopping_list(callback: CallbackQuery):
    user_id = callback.from_user.id
    profile = await db.get_user_profile(user_id)
    menu_obj = await menu_generator.generate_menu_for_user(profile)

    text = (
        "📋 *ПОЛНЫЙ СПИСОК ПОКУПОК НА НЕДЕЛЮ*\n"
        f"Для семьи из {profile.family_size} чел. на {profile.plan_days} дней:\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
    )

    categories = {}
    for ing in menu_obj.shopping_list:
        ing_dict = ing if isinstance(ing, dict) else ing.dict()
        cat = ing_dict.get("category", "прочее").capitalize()
        categories.setdefault(cat, []).append(ing_dict)

    for cat_name, items in categories.items():
        text += f"*{cat_name}:*\n"
        for it in items:
            text += f"  ▫️ {it['name']} — *{it['amount']} {it['unit']}*\n"
        text += "\n"

    text += "🛒 Все продукты учтены в корзине супермаркетов."
    kb = get_prices_view_keyboard()
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)
    await callback.answer()

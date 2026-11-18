import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from app.config import settings
from app.database.db import db

logger = logging.getLogger("food_bot.scheduler")

class MenuScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.bot_instance = None

    def set_bot(self, bot):
        self.bot_instance = bot

    def start(self):
        # Run every Monday at configured hour and minute
        trigger = CronTrigger(
            day_of_week=settings.AUTO_UPDATE_DAY_OF_WEEK,
            hour=settings.AUTO_UPDATE_HOUR,
            minute=settings.AUTO_UPDATE_MINUTE
        )
        self.scheduler.add_job(
            self.update_all_user_menus,
            trigger=trigger,
            id="weekly_monday_menu_update",
            replace_existing=True
        )
        self.scheduler.start()
        logger.info(f"MenuScheduler started: configured for every Monday at {settings.AUTO_UPDATE_HOUR:02d}:{settings.AUTO_UPDATE_MINUTE:02d}")

    def shutdown(self):
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("MenuScheduler shut down.")

    async def update_all_user_menus(self):
        """Weekly Monday automated menu generation for all active users"""
        from app.services.menu_generator import menu_generator
        
        logger.info("Executing automated Monday weekly menu update...")
        user_ids = await db.get_all_active_users()
        logger.info(f"Found {len(user_ids)} active users for weekly menu update.")

        for uid in user_ids:
            try:
                profile = await db.get_user_profile(uid)
                if not profile:
                    continue

                new_menu = await menu_generator.generate_menu_for_user(profile, force_new=True)
                logger.info(f"Successfully generated new Monday menu for user {uid}")

                # Notify user via Telegram bot if connected
                if self.bot_instance:
                    comp = new_menu.price_comparison
                    best_store = comp.cheapest_store if comp else "супермаркетах"
                    savings = int(comp.max_savings) if comp else 0

                    msg = (
                        "🌅 *Доброе утро понедельника!*\n\n"
                        "🗓 Ваше новое сбалансированное меню на неделю готово!\n\n"
                        f"🛒 *Лучшие цены недели:* Самая выгодная корзина в *{best_store}* "
                        f"(экономия до *{savings:,} ₽*).\n\n"
                        "Откройте меню, чтобы посмотреть блюда и список покупок."
                    )
                    
                    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
                    kb = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🍽 Посмотреть меню", callback_data="view_menu")],
                        [InlineKeyboardButton(text="📱 Открыть WebApp", web_app=WebAppInfo(url=settings.WEBAPP_URL))]
                    ])
                    try:
                        await self.bot_instance.send_message(
                            chat_id=uid,
                            text=msg,
                            parse_mode="Markdown",
                            reply_markup=kb
                        )
                    except Exception as e:
                        logger.warning(f"Could not send weekly notification to {uid}: {e}")

            except Exception as e:
                logger.error(f"Error updating weekly menu for user {uid}: {e}")

menu_scheduler = MenuScheduler()

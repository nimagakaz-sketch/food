from app.bot.bot_instance import bot, dp
from app.bot.handlers import common, onboarding, menu, prices

def setup_bot_handlers():
    dp.include_router(common.router)
    dp.include_router(onboarding.router)
    dp.include_router(menu.router)
    dp.include_router(prices.router)

__all__ = ["bot", "dp", "setup_bot_handlers"]

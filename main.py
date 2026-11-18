import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database.db import db
from app.services.price_comparator import price_comparator
from app.services.scheduler import menu_scheduler
from app.api.routes import router as api_router
from app.bot import bot, dp, setup_bot_handlers

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("food_bot")

WEB_DIR = Path(__file__).resolve().parent / "web"

bot_task: asyncio.Task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global bot_task
    logger.info("Initializing Food & Price Bot backend...")
    
    # 1. Initialize SQLite Database
    await db.init()

    # 2. Seed and Cache Supermarket Prices
    await price_comparator.init_prices()

    # 3. Setup and start Telegram Bot & Scheduler
    setup_bot_handlers()
    menu_scheduler.set_bot(bot)
    menu_scheduler.start()

    # Run bot polling in background if token is configured
    if settings.TELEGRAM_BOT_TOKEN and not settings.TELEGRAM_BOT_TOKEN.startswith("demo"):
        logger.info("Starting Telegram Bot polling in background...")
        bot_task = asyncio.create_task(dp.start_polling(bot, skip_updates=True))
    else:
        logger.warning("No active TELEGRAM_BOT_TOKEN provided, running in WebApp/API only mode.")

    yield

    # Shutdown
    logger.info("Shutting down Food & Price Bot backend...")
    menu_scheduler.shutdown()
    if bot_task and not bot_task.done():
        bot_task.cancel()
        try:
            await bot_task
        except asyncio.CancelledError:
            pass
    await bot.session.close()

# FastAPI application
app = FastAPI(
    title="Food & Supermarket Price Planner API",
    description="Backend for Telegram Family Menu & Best Supermarket Price Comparator (Пятерочка, Магнит, Лента)",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware for WebApp
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routes
app.include_router(api_router)

# Mount static web directories
if (WEB_DIR / "css").exists():
    app.mount("/css", StaticFiles(directory=str(WEB_DIR / "css")), name="css")
if (WEB_DIR / "js").exists():
    app.mount("/js", StaticFiles(directory=str(WEB_DIR / "js")), name="js")

# Requirement 4: Главная страница с поддержкой GET и HEAD
@app.api_route("/", methods=["GET", "HEAD"])
async def root_index(request: Request):
    """
    Root endpoint supporting both GET and HEAD methods.
    Returns lightweight 200 OK headers for HEAD (e.g. UptimeRobot monitoring)
    without executing heavy rendering or disk streaming.
    """
    if request.method == "HEAD":
        return Response(status_code=200, headers={"X-Health": "OK", "Content-Type": "text/html; charset=utf-8"})

    index_file = WEB_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file), media_type="text/html")
    return {"message": "Food & Price Bot API is online", "health": "/health", "docs": "/docs"}

# Dedicated lightweight health check endpoint (GET and HEAD)
@app.api_route("/health", methods=["GET", "HEAD"])
async def health_endpoint(request: Request):
    """
    Lightweight health check for monitoring services (e.g. UptimeRobot).
    Supports GET and HEAD, returns 200 OK instantly.
    """
    if request.method == "HEAD":
        return Response(status_code=200, headers={"X-Health": "OK", "Content-Type": "application/json"})
    return {"status": "ok", "app": "food_bot", "timestamp": str(asyncio.get_event_loop().time())}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )

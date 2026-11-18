import os
from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    # Telegram Bot
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "8593240850:AAGqei6Qv-DQnx5IZurU9VEriw84zKwrXYg")
    
    # Server & Web
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    WEBAPP_URL: str = os.getenv("WEBAPP_URL", "http://localhost:8000")
    
    # Database (SQLite by default, Supabase ready)
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", str(BASE_DIR / "data" / "food_bot.db"))
    USE_SUPABASE: bool = os.getenv("USE_SUPABASE", "false").lower() in ("true", "1", "yes")
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    
    # Scheduler
    AUTO_UPDATE_DAY_OF_WEEK: str = os.getenv("AUTO_UPDATE_DAY_OF_WEEK", "mon")
    AUTO_UPDATE_HOUR: int = int(os.getenv("AUTO_UPDATE_HOUR", "9"))
    AUTO_UPDATE_MINUTE: int = int(os.getenv("AUTO_UPDATE_MINUTE", "0"))
    
    # App
    DEBUG: bool = os.getenv("DEBUG", "true").lower() in ("true", "1", "yes")

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()

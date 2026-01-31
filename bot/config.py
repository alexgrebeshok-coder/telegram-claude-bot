import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError(
        "BOT_TOKEN не установлен. "
        "Скопируйте .env.example в .env и укажите токен бота от @BotFather"
    )

ADMIN_IDS_RAW = os.getenv("ADMIN_IDS", "")
if not ADMIN_IDS_RAW:
    raise ValueError(
        "ADMIN_IDS не установлен. "
        "Укажите в .env ваш Telegram ID (можно узнать через @userinfobot)"
    )
ADMIN_IDS = [int(x.strip()) for x in ADMIN_IDS_RAW.split(",") if x.strip().isdigit()]

if not ADMIN_IDS:
    raise ValueError(
        "ADMIN_IDS содержит некорректные значения. "
        "Укажите числовые ID через запятую, например: ADMIN_IDS=123456789,987654321"
    )

# Claude Code CLI
# Рабочая директория для Claude Code (где будут выполняться команды)
CLAUDE_WORKING_DIR = os.getenv("CLAUDE_WORKING_DIR", os.path.expanduser("~"))

# Таймаут выполнения задачи в секундах (по умолчанию 10 минут)
CLAUDE_TIMEOUT = int(os.getenv("CLAUDE_TIMEOUT", "600"))

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///claude_bot.db")

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

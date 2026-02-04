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

# GLM-4.7 (Zhipu AI, удалённый API) — опционально
GLM_API_KEY = os.getenv("GLM_API_KEY") or os.getenv("ZHIPUAI_API_KEY")
# Использовать подписку (Coding API) или баланс (open.bigmodel.cn). По умолчанию true = подписка.
GLM_USE_SUBSCRIPTION = os.getenv("GLM_USE_SUBSCRIPTION", "true").lower() in ("1", "true", "yes")

# Общая локальная память: директория для экспорта диалогов (Markdown)
BOT_MEMORY_DIR = os.getenv("BOT_MEMORY_DIR", os.path.join(CLAUDE_WORKING_DIR, "bot_memory"))

# Системный промпт для Claude Code CLI (append к дефолтному)
# По умолчанию — append_system_prompt.md в корне проекта
_script_dir = os.path.dirname(os.path.abspath(__file__))
SYSTEM_PROMPT_FILE = os.getenv(
    "SYSTEM_PROMPT_FILE",
    os.path.join(_script_dir, "..", "append_system_prompt.md"),
)

# Whisper.cpp (распознавание речи)
_whisper_dir = os.path.join(os.path.dirname(__file__), "..", "whisper.cpp")
WHISPER_CPP_PATH = os.getenv(
    "WHISPER_CPP_PATH",
    os.path.join(_whisper_dir, "whisper-cli"),
)
WHISPER_MODEL_PATH = os.getenv(
    "WHISPER_MODEL_PATH",
    os.path.join(_whisper_dir, "ggml-small-q5_1.bin"),
)
WHISPER_TIMEOUT = int(os.getenv("WHISPER_TIMEOUT", "60"))

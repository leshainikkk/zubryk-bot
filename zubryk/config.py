import os
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
DATABASE_URL = os.environ.get("DATABASE_URL", "")
APP_TIMEZONE = os.environ.get("APP_TIMEZONE", "Europe/Minsk")
TIMEZONE = ZoneInfo(APP_TIMEZONE)
MINI_APP_URL = os.environ.get("MINI_APP_URL", "")
BOT_USERNAME = os.environ.get("BOT_USERNAME", "")
ENABLE_PREVIEW = os.environ.get("ENABLE_PREVIEW", "false").lower() == "true"
INIT_DATA_MAX_AGE = int(os.environ.get("INIT_DATA_MAX_AGE", "86400"))


def get_mini_app_url():
    path=ROOT/".runtime/mini_app_url"
    try:
        value=path.read_text().strip()
    except OSError:
        value=MINI_APP_URL
    return value if value.startswith("https://") else ""

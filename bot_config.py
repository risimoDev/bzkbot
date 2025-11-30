import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    bot_token: str = os.getenv("BOT_TOKEN", "")
    access_phrase: str = os.getenv("ACCESS_PHRASE", "")
    admin_ids: list[int] = field(default_factory=list)
    dues_amount: int = int(os.getenv("DUES_AMOUNT", "500"))
    timezone: str = os.getenv("TIMEZONE", "Europe/Moscow")
    db_path: str = os.getenv("DB_PATH", "bzkbot.db")

    def __post_init__(self):
        raw_admins = os.getenv("ADMIN_IDS", "")
        self.admin_ids = [int(x) for x in raw_admins.split(",") if x.strip().isdigit()]

config = Config()

if not config.bot_token:
    raise RuntimeError("BOT_TOKEN не задан в .env")
if not config.access_phrase:
    raise RuntimeError("ACCESS_PHRASE не задан в .env")

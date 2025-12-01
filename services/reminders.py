from datetime import datetime
import pytz
from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from ui.keyboards import ack_button
from db.dao import DAO
from ui.messages import reminder_text
from db.dao import DAO
from ui.messages import reminder_text

ACK_PREFIX = "ack_"

def ack_callback_data(type_: str) -> str:
    return f"{ACK_PREFIX}{type_}"

async def send_daily_reminders(bot: Bot, dao: DAO, tzname: str, dues_amount: int, vpn_amount: int):
    tz = pytz.timezone(tzname)
    now = datetime.now(tz).isoformat()
    for type_ in ("dues", "vpn"):
        users = await dao.users_for_reminder(type_)
        for user_id, tg_id in users:
            text = reminder_text(type_, dues_amount, vpn_amount)
            kb = ack_button(type_)
            try:
                await bot.send_message(chat_id=tg_id, text=text, reply_markup=kb)
                await dao.upsert_reminder(user_id=user_id, type_=type_, acknowledged=False, last_sent_at=now)
            except Exception:
                await dao.upsert_reminder(user_id=user_id, type_=type_, acknowledged=False, last_sent_at=now)

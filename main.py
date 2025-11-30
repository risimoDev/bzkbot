import asyncio
import logging
from datetime import time
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from bot_config import config
from db.dao import DAO
from services.reminders import send_daily_reminders, ack_callback_data
from ui.keyboards import main_menu, notifications_menu, admin_menu, reply_menu_button
from ui.messages import welcome_message, access_granted_message, access_denied_message, status_message, admin_prompt_paid, admin_prompt_savings, saved_message, marked_message, admin_prompt_schedule, schedule_updated

bot = Bot(token=config.bot_token)
dp = Dispatcher()
dao = DAO(config.db_path)
scheduler = AsyncIOScheduler()

ACCESS_DENIED = access_denied_message()

class AdminPaidDues(StatesGroup):
    waiting_input = State()

class AdminPaidVPN(StatesGroup):
    waiting_input = State()

class AdminSavings(StatesGroup):
    waiting_input = State()

class AdminSchedule(StatesGroup):
    waiting_input = State()

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await dao.init()
    user = await dao.get_or_create_user(message.from_user.id)
    logging.info(f"/start from tg_id={message.from_user.id}; user_active={user.is_active}")
    if user.is_active:
        kb = main_menu(is_admin=message.from_user.id in config.admin_ids)
        rkb = reply_menu_button()
        await message.answer(access_granted_message(), reply_markup=kb)
        try:
            await message.answer("Для удобства доступна кнопка Меню", reply_markup=rkb)
        except Exception:
            pass
    else:
        await message.answer(welcome_message())

@dp.message(F.text)
async def handle_text(message: Message):
    await dao.init()
    user = await dao.get_or_create_user(message.from_user.id)
    text = (message.text or "").strip()
    logging.info(f"text from tg_id={message.from_user.id}: '{text}' | user_active={user.is_active}")
    if not user.is_active:
        # Сравнение кодовой фразы: без лишних пробелов, регистронезависимо
        access = text.casefold() == (config.access_phrase or "").strip().casefold()
        logging.info(f"access phrase match={access}; env_phrase='{config.access_phrase}'")
        if access:
            await dao.activate_user(message.from_user.id)
            kb = main_menu(is_admin=message.from_user.id in config.admin_ids)
            rkb = reply_menu_button()
            await message.answer(access_granted_message(), reply_markup=kb)
            try:
                await message.answer("Для удобства доступна кнопка Меню", reply_markup=rkb)
            except Exception:
                pass
            logging.info(f"user tg_id={message.from_user.id} activated; is_admin={(message.from_user.id in config.admin_ids)}")
        else:
            await message.answer(ACCESS_DENIED)
            logging.warning(f"access denied for tg_id={message.from_user.id}")
        return
    # Активный пользователь
    if text.lower() in ("/menu", "меню"):
        kb = main_menu(is_admin=message.from_user.id in config.admin_ids)
        await message.answer("Главное меню", reply_markup=kb)
    elif text.lower().startswith("/paid_dues"):
        if message.from_user.id not in config.admin_ids:
            await message.answer("Только админ")
            return
        try:
            _, raw_tg_id, raw_amount = text.split()
            tg_id = int(raw_tg_id)
            amount = int(raw_amount)
        except Exception:
            await message.answer("Формат: /paid_dues <tg_id> <amount>")
            return
        user = await dao.get_or_create_user(tg_id)
        from datetime import datetime
        await dao.record_payment(user.id, "dues", amount, datetime.now().isoformat())
        await message.answer("Отмечено")
    elif text.lower().startswith("/paid_vpn"):
        if message.from_user.id not in config.admin_ids:
            await message.answer("Только админ")
            return
        try:
            _, raw_tg_id, raw_amount = text.split()
            tg_id = int(raw_tg_id)
            amount = int(raw_amount)
        except Exception:
            await message.answer("Формат: /paid_vpn <tg_id> <amount>")
            return
        user = await dao.get_or_create_user(tg_id)
        from datetime import datetime
        await dao.record_payment(user.id, "vpn", amount, datetime.now().isoformat())
        await message.answer("Отмечено")
    elif text.lower().startswith("/notify_on"):
        if message.from_user.id not in config.admin_ids:
            await message.answer("Только админ")
            return
        try:
            _, raw_tg_id, typ = text.split()
            tg_id = int(raw_tg_id)
        except Exception:
            await message.answer("Формат: /notify_on <tg_id> <dues|vpn>")
            return
        u = await dao.get_or_create_user(tg_id)
        await dao.set_notifications(u.id, dues=(typ=="dues") if typ in ("dues","vpn") else None, vpn=(typ=="vpn") if typ in ("dues","vpn") else None)
        await message.answer("Включено")
    elif text.lower().startswith("/notify_off"):
        if message.from_user.id not in config.admin_ids:
            await message.answer("Только админ")
            return
        try:
            _, raw_tg_id, typ = text.split()
            tg_id = int(raw_tg_id)
        except Exception:
            await message.answer("Формат: /notify_off <tg_id> <dues|vpn>")
            return
        u = await dao.get_or_create_user(tg_id)
        await dao.set_notifications(u.id, dues=(typ!="dues") if typ in ("dues","vpn") else None, vpn=(typ!="vpn") if typ in ("dues","vpn") else None)
        await message.answer("Выключено")
    elif text.lower().startswith("/savings"):
        if message.from_user.id not in config.admin_ids:
            await message.answer("Только админ")
            return
        try:
            _, raw_amount = text.split()
            amount = int(raw_amount)
        except Exception:
            await message.answer("Формат: /savings <amount>")
            return
        await dao.set_savings(amount)
        await message.answer("Обновлено")

# Главное меню
@dp.callback_query(F.data == "menu_status")
async def menu_status(cb: CallbackQuery):
    total_dues = await dao.get_total_collected("dues")
    total_vpn = await dao.get_total_collected("vpn")
    savings = await dao.get_savings()
    text = status_message(total_dues, total_vpn, savings)
    kb = main_menu(is_admin=cb.from_user.id in config.admin_ids)
    await cb.message.edit_text(text, reply_markup=kb)
    await cb.answer()

@dp.callback_query(F.data == "menu_notifications")
async def menu_notifications(cb: CallbackQuery):
    user = await dao.get_or_create_user(cb.from_user.id)
    kb = notifications_menu(user.allow_dues_notifications, user.allow_vpn_notifications)
    await cb.message.edit_text("🔔 Уведомления", reply_markup=kb)
    await cb.answer()

@dp.callback_query(F.data == "menu_admin")
async def menu_admin(cb: CallbackQuery):
    if cb.from_user.id not in config.admin_ids:
        await cb.answer("Недостаточно прав", show_alert=True)
        return
    kb = admin_menu()
    await cb.message.edit_text("🛠 Админ-панель", reply_markup=kb)
    await cb.answer()

@dp.callback_query(F.data == "back_main")
async def back_main(cb: CallbackQuery):
    kb = main_menu(is_admin=cb.from_user.id in config.admin_ids)
    await cb.message.edit_text("Главное меню", reply_markup=kb)
    await cb.answer()

# Тогглы уведомлений
@dp.callback_query(F.data == "toggle_dues")
async def toggle_dues(cb: CallbackQuery):
    user = await dao.get_or_create_user(cb.from_user.id)
    await dao.set_notifications(user.id, dues=not user.allow_dues_notifications)
    user = await dao.get_or_create_user(cb.from_user.id)
    kb = notifications_menu(user.allow_dues_notifications, user.allow_vpn_notifications)
    await cb.message.edit_reply_markup(reply_markup=kb)
    await cb.answer("Сохранено")

@dp.callback_query(F.data == "toggle_vpn")
async def toggle_vpn(cb: CallbackQuery):
    user = await dao.get_or_create_user(cb.from_user.id)
    await dao.set_notifications(user.id, vpn=not user.allow_vpn_notifications)
    user = await dao.get_or_create_user(cb.from_user.id)
    kb = notifications_menu(user.allow_dues_notifications, user.allow_vpn_notifications)
    await cb.message.edit_reply_markup(reply_markup=kb)
    await cb.answer("Сохранено")

# Админ: по кнопкам
@dp.callback_query(F.data == "admin_paid_dues")
async def admin_paid_dues(cb: CallbackQuery, state: FSMContext):
    if cb.from_user.id not in config.admin_ids:
        await cb.answer("Недостаточно прав", show_alert=True)
        return
    await state.set_state(AdminPaidDues.waiting_input)
    await cb.message.edit_text(admin_prompt_paid("dues"))
    await cb.answer()

@dp.callback_query(F.data == "admin_paid_vpn")
async def admin_paid_vpn(cb: CallbackQuery, state: FSMContext):
    if cb.from_user.id not in config.admin_ids:
        await cb.answer("Недостаточно прав", show_alert=True)
        return
    await state.set_state(AdminPaidVPN.waiting_input)
    await cb.message.edit_text(admin_prompt_paid("vpn"))
    await cb.answer()

@dp.callback_query(F.data == "admin_savings")
async def admin_savings(cb: CallbackQuery, state: FSMContext):
    if cb.from_user.id not in config.admin_ids:
        await cb.answer("Недостаточно прав", show_alert=True)
        return
    await state.set_state(AdminSavings.waiting_input)
    await cb.message.edit_text(admin_prompt_savings())
    await cb.answer()

@dp.callback_query(F.data == "admin_schedule")
async def admin_schedule(cb: CallbackQuery, state: FSMContext):
    if cb.from_user.id not in config.admin_ids:
        await cb.answer("Недостаточно прав", show_alert=True)
        return
    hour, minute = await dao.get_schedule_time()
    await state.set_state(AdminSchedule.waiting_input)
    await cb.message.edit_text(admin_prompt_schedule(hour, minute), parse_mode="Markdown")
    await cb.answer()

@dp.message(AdminSchedule.waiting_input)
async def handle_admin_schedule_input(message: Message, state: FSMContext):
    try:
        raw = (message.text or "").strip()
        parts = raw.split(":")
        hour = int(parts[0]); minute = int(parts[1])
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError()
    except Exception:
        await message.answer("Введите время как `HH:MM`", parse_mode="Markdown")
        return
    await dao.set_schedule_time(hour, minute)
    # Пересоздать job
    try:
        scheduler.remove_job("daily_reminders")
    except Exception:
        pass
    scheduler.add_job(
        send_daily_reminders,
        CronTrigger(hour=hour, minute=minute, timezone=config.timezone),
        args=[bot, dao, config.timezone, config.dues_amount],
        id="daily_reminders",
        replace_existing=True,
    )
    await state.clear()
    await message.answer(schedule_updated(hour, minute))

# Обработка ввода для FSM
@dp.message(AdminPaidDues.waiting_input)
async def handle_admin_paid_dues_input(message: Message, state: FSMContext):
    try:
        raw_tg_id, raw_amount = (message.text or "").split()
        tg_id = int(raw_tg_id)
        amount = int(raw_amount)
    except Exception:
        await message.answer("Формат: `tg_id сумма`", parse_mode="Markdown")
        return
    u = await dao.get_or_create_user(tg_id)
    from datetime import datetime
    await dao.record_payment(u.id, "dues", amount, datetime.now().isoformat())
    await state.clear()
    await message.answer(marked_message())

@dp.message(AdminPaidVPN.waiting_input)
async def handle_admin_paid_vpn_input(message: Message, state: FSMContext):
    try:
        raw_tg_id, raw_amount = (message.text or "").split()
        tg_id = int(raw_tg_id)
        amount = int(raw_amount)
    except Exception:
        await message.answer("Формат: `tg_id сумма`", parse_mode="Markdown")
        return
    u = await dao.get_or_create_user(tg_id)
    from datetime import datetime
    await dao.record_payment(u.id, "vpn", amount, datetime.now().isoformat())
    await state.clear()
    await message.answer(marked_message())

@dp.message(AdminSavings.waiting_input)
async def handle_admin_savings_input(message: Message, state: FSMContext):
    try:
        amount = int((message.text or "").strip())
    except Exception:
        await message.answer("Введите целое число в ₽")
        return
    await dao.set_savings(amount)
    await state.clear()
    await message.answer(saved_message())

@dp.callback_query(F.data.startswith("ack_"))
async def on_ack(cb: CallbackQuery):
    await dao.init()
    type_ = cb.data.replace("ack_", "")
    user = await dao.get_or_create_user(cb.from_user.id)
    await dao.upsert_reminder(user_id=user.id, type_=type_, acknowledged=True, last_sent_at=None)
    await cb.message.answer("Спасибо, отмечено.")
    await cb.answer()

async def on_startup():
    await dao.init()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    logging.info("Bot startup: init DB and scheduler")
    hour, minute = await dao.get_schedule_time()
    scheduler.add_job(
        send_daily_reminders,
        CronTrigger(hour=hour, minute=minute, timezone=config.timezone),
        args=[bot, dao, config.timezone, config.dues_amount],
        id="daily_reminders",
        replace_existing=True,
    )
    logging.info(f"Scheduler configured: daily_reminders at {hour:02d}:{minute:02d} tz={config.timezone}")
    scheduler.start()

async def main():
    await on_startup()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

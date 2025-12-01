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
from ui.keyboards import main_menu, notifications_menu, admin_menu, reply_menu_button, status_toggle_menu, admin_users_page_keyboard, admin_user_actions_keyboard, custom_notify_audience_keyboard, custom_history_page_keyboard, batch_actions_keyboard, ack_custom_keyboard
from ui.messages import welcome_message, access_granted_message, access_denied_message, status_message, admin_prompt_paid, admin_prompt_savings, saved_message, marked_message, admin_prompt_schedule, schedule_updated, status_hidden_message, admin_prompt_status_visibility, status_visibility_changed, admin_users_list, admin_user_status_toggled, component_toggled, custom_notify_intro, custom_notify_enter_ids, custom_notify_enter_text, custom_notify_sent, custom_notify_invalid_ids, custom_history_list, batch_resend_result, custom_acknowledged
ADMIN_USERS_PAGE_SIZE = 10

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

class AdminStatusVisibility(StatesGroup):
    waiting_input = State()

class AdminCustomAudience(StatesGroup):
    waiting_ids = State()
    waiting_text_all = State()
    waiting_text_list = State()
    waiting_text_resend = State()

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
    u = await dao.get_or_create_user(cb.from_user.id)
    show = await dao.get_show_status(u.id)
    vis = await dao.get_component_visibility(u.id)
    if not show:
        await cb.message.edit_text(status_hidden_message(), reply_markup=status_toggle_menu(show))
    else:
        total_dues = await dao.get_total_collected("dues")
        total_vpn = await dao.get_total_collected("vpn")
        savings = await dao.get_savings()
        parts = ["📊 Статус"]
        if vis["dues"]:
            parts.append(f"• Сборы: {total_dues}₽")
        if vis["vpn"]:
            parts.append(f"• VPN: {total_vpn}₽")
        if vis["savings"]:
            parts.append(f"• Сберегательный счёт: {savings}₽")
        text = "\n".join(parts)
        kb = status_toggle_menu(True)
        await cb.message.edit_text(text, reply_markup=kb)
    await cb.answer()

@dp.callback_query(F.data == "menu_notifications")
async def menu_notifications(cb: CallbackQuery):
    user = await dao.get_or_create_user(cb.from_user.id)
    show = await dao.get_show_status(user.id)
    kb = notifications_menu(user.allow_dues_notifications, user.allow_vpn_notifications, show)
    await cb.message.edit_text("🔔 Уведомления", reply_markup=kb)
    await cb.answer()
@dp.callback_query(F.data == "toggle_status")
async def toggle_status(cb: CallbackQuery):
    u = await dao.get_or_create_user(cb.from_user.id)
    show = await dao.get_show_status(u.id)
    await dao.set_show_status(u.id, not show)
    new_show = await dao.get_show_status(u.id)
    if not new_show:
        await cb.message.edit_text(status_hidden_message(), reply_markup=status_toggle_menu(new_show))
    else:
        total_dues = await dao.get_total_collected("dues")
        total_vpn = await dao.get_total_collected("vpn")
        savings = await dao.get_savings()
        text = status_message(total_dues, total_vpn, savings)
        await cb.message.edit_text(text, reply_markup=status_toggle_menu(new_show))
    await cb.answer("Сохранено")

@dp.callback_query(F.data == "admin_status_visibility")
async def admin_status_visibility(cb: CallbackQuery, state: FSMContext):
    if cb.from_user.id not in config.admin_ids:
        await cb.answer("Недостаточно прав", show_alert=True)
        return
    await state.set_state(AdminStatusVisibility.waiting_input)
    await cb.message.edit_text(admin_prompt_status_visibility(), parse_mode="Markdown")
    await cb.answer()

@dp.callback_query(F.data == "admin_custom_notification")
async def admin_custom_notification(cb: CallbackQuery, state: FSMContext):
    if cb.from_user.id not in config.admin_ids:
        await cb.answer("Недостаточно прав", show_alert=True)
        return
    await cb.message.edit_text(custom_notify_intro(), reply_markup=custom_notify_audience_keyboard())
    await cb.answer()

@dp.callback_query(F.data == "custom_audience_all")
async def custom_audience_all(cb: CallbackQuery, state: FSMContext):
    await state.set_state(AdminCustomAudience.waiting_text_all)
    await cb.message.edit_text(custom_notify_enter_text("все активные"))
    await cb.answer()

@dp.callback_query(F.data == "custom_audience_list")
async def custom_audience_list(cb: CallbackQuery, state: FSMContext):
    await state.set_state(AdminCustomAudience.waiting_ids)
    await cb.message.edit_text(custom_notify_enter_ids())
    await cb.answer()

@dp.message(AdminCustomAudience.waiting_ids)
async def custom_audience_ids_input(message: Message, state: FSMContext):
    raw = (message.text or "").replace("\n", " ")
    parts = [p.strip() for p in raw.replace(",", " ").split() if p.strip()]
    try:
        ids = [int(p) for p in parts]
    except Exception:
        await message.answer(custom_notify_invalid_ids())
        return
    await state.update_data(tg_ids=ids)
    await state.set_state(AdminCustomAudience.waiting_text_list)
    await message.answer(custom_notify_enter_text(f"{len(ids)} пользователей"))

@dp.message(AdminCustomAudience.waiting_text_all)
async def custom_notify_text_all(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if not text:
        await message.answer("Текст не может быть пустым")
        return
    ids = await dao.active_user_ids()
    from datetime import datetime
    sent_at = datetime.now().isoformat()
    import uuid
    batch_id = uuid.uuid4().hex
    created = await dao.create_custom_notifications_batch(text, ids, sent_at, batch_id)
    count = 0
    for tg_id, notif_id in created:
        try:
            await bot.send_message(tg_id, text, reply_markup=ack_custom_keyboard(notif_id))
            count += 1
        except Exception:
            pass
    await state.clear()
    await message.answer(custom_notify_sent(count))

@dp.message(AdminCustomAudience.waiting_text_list)
async def custom_notify_text_list(message: Message, state: FSMContext):
    data = await state.get_data()
    ids: list[int] = data.get("tg_ids", [])
    text = (message.text or "").strip()
    if not text:
        await message.answer("Текст не может быть пустым")
        return
    from datetime import datetime
    sent_at = datetime.now().isoformat()
    import uuid
    batch_id = uuid.uuid4().hex
    created = await dao.create_custom_notifications_batch(text, ids, sent_at, batch_id)
    count = 0
    for tg_id, notif_id in created:
        try:
            await bot.send_message(tg_id, text, reply_markup=ack_custom_keyboard(notif_id))
            count += 1
        except Exception:
            pass
    await state.clear()
    await message.answer(custom_notify_sent(count))

@dp.callback_query(F.data.startswith("admin_custom_history_"))
async def custom_history(cb: CallbackQuery):
    if cb.from_user.id not in config.admin_ids:
        await cb.answer("Недостаточно прав", show_alert=True)
        return
    try:
        page = int(cb.data.split("_")[-1])
    except Exception:
        page = 1
    total_batches = await dao.count_batches()
    PAGE_SIZE = 5
    total_pages = max(1, (total_batches + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(1, min(page, total_pages))
    batches = await dao.list_batches(page, PAGE_SIZE)
    text = custom_history_list(f"История (стр. {page})", batches)
    kb = custom_history_page_keyboard(page, total_pages)
    await cb.message.edit_text(text, reply_markup=kb)
    await cb.answer()

@dp.callback_query(F.data.startswith("resend_batch_"))
async def resend_batch(cb: CallbackQuery):
    if cb.from_user.id not in config.admin_ids:
        await cb.answer("Недостаточно прав", show_alert=True)
        return
    batch_id = cb.data.replace("resend_batch_", "")
    unacked = await dao.unacked_in_batch(batch_id)
    attempted = len(unacked)
    sent = 0
    for item in unacked:
        try:
            notif = await dao.get_custom_notif(item["notif_id"])
            if notif:
                await bot.send_message(item["tg_id"], notif["text"], reply_markup=ack_custom_keyboard(item["notif_id"]))
                sent += 1
        except Exception:
            pass
    await cb.message.edit_text(batch_resend_result(batch_id, attempted, sent), reply_markup=batch_actions_keyboard(batch_id))
    await cb.answer("Готово")

@dp.callback_query(F.data.startswith("ackc_"))
async def ack_custom(cb: CallbackQuery):
    notif_id = cb.data.replace("ackc_", "")
    try:
        notif_id_int = int(notif_id)
    except ValueError:
        await cb.answer("Ошибка", show_alert=True)
        return
    user = await dao.get_or_create_user(cb.from_user.id)
    await dao.acknowledge_custom(user.id, notif_id_int)
    await cb.message.edit_text(custom_acknowledged())
    await cb.answer("OK")

@dp.message(AdminStatusVisibility.waiting_input)
async def handle_admin_status_visibility(message: Message, state: FSMContext):
    try:
        raw_tg_id, mode = (message.text or "").strip().split()
        tg_id = int(raw_tg_id)
        mode = mode.lower()
        if mode not in ("show", "hide"):
            raise ValueError()
    except Exception:
        await message.answer("Формат: `tg_id show|hide`", parse_mode="Markdown")
        return
    u = await dao.get_or_create_user(tg_id)
    await dao.set_show_status(u.id, mode == "show")
    await state.clear()
    await message.answer(status_visibility_changed(tg_id, mode == "show"))

@dp.callback_query(F.data == "menu_admin")
async def menu_admin(cb: CallbackQuery):
    @dp.callback_query(F.data.startswith("admin_users_page_"))
    async def admin_users_page(cb: CallbackQuery):
        if cb.from_user.id not in config.admin_ids:
            await cb.answer("Недостаточно прав", show_alert=True)
            return
        try:
            page = int(cb.data.split("_")[-1])
        except Exception:
            page = 1
        total = await dao.total_users()
        total_pages = max(1, (total + ADMIN_USERS_PAGE_SIZE - 1) // ADMIN_USERS_PAGE_SIZE)
        page = max(1, min(page, total_pages))
        users = await dao.users_page(page, ADMIN_USERS_PAGE_SIZE)
        text = admin_users_list(f"Пользователи (страница {page})", users)
        kb = admin_users_page_keyboard(page, total_pages)
        await cb.message.edit_text(text, reply_markup=kb)
        await cb.answer()

    @dp.callback_query(F.data.startswith("admin_toggle_user_status_"))
    async def admin_toggle_user_status(cb: CallbackQuery):
        if cb.from_user.id not in config.admin_ids:
            await cb.answer("Недостаточно прав", show_alert=True)
            return
        try:
            user_id = int(cb.data.split("_")[-1])
        except Exception:
            await cb.answer("Ошибка ID")
            return
        # Получаем tg_id
        async with aiosqlite.connect(config.db_path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT id, tg_id, show_status FROM users WHERE id=?", (user_id,))
            row = await cur.fetchone()
        if not row:
            await cb.answer("Не найден")
            return
        current_show = bool(row["show_status"])
        await dao.set_show_status(row["id"], not current_show)
        new_show = await dao.get_show_status(row["id"])
        await cb.message.edit_text(admin_user_status_toggled(row["tg_id"], new_show), reply_markup=admin_user_actions_keyboard(row["id"], new_show))
        await cb.answer("Готово")

    @dp.callback_query(F.data.startswith("admin_toggle_component_"))
    async def admin_toggle_component(cb: CallbackQuery):
        if cb.from_user.id not in config.admin_ids:
            await cb.answer("Недостаточно прав", show_alert=True)
            return
        parts = cb.data.split("_")
        try:
            component = parts[3]
            user_id = int(parts[4])
        except Exception:
            await cb.answer("Ошибка данных")
            return
        async with aiosqlite.connect(config.db_path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT id, tg_id FROM users WHERE id=?", (user_id,))
            row = await cur.fetchone()
        if not row:
            await cb.answer("Не найден")
            return
        await dao.toggle_component(user_id, component)
        vis = await dao.get_component_visibility(user_id)
        show_status = await dao.get_show_status(user_id)
        await cb.message.edit_text(
            component_toggled(row["tg_id"], component, vis[component]),
            reply_markup=admin_user_actions_keyboard(row["id"], show_status)
        )
        await cb.answer("Готово")

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

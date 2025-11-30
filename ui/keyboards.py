from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

def main_menu(is_admin: bool) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="Мой статус", callback_data="menu_status")],
        [InlineKeyboardButton(text="Уведомления", callback_data="menu_notifications")],
    ]
    if is_admin:
        rows.append([InlineKeyboardButton(text="Админ-панель", callback_data="menu_admin")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def notifications_menu(allow_dues: bool, allow_vpn: bool) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=("Сбор: включено" if allow_dues else "Сбор: выключено"), callback_data="toggle_dues")],
        [InlineKeyboardButton(text=("VPN: включено" if allow_vpn else "VPN: выключено"), callback_data="toggle_vpn")],
        [InlineKeyboardButton(text="Назад", callback_data="back_main")]
    ])

def status_toggle_menu(show_status: bool) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=("Статус: показывать" if show_status else "Статус: скрывать"), callback_data="toggle_status")],
        [InlineKeyboardButton(text="Назад", callback_data="back_main")]
    ])

def admin_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Отметить оплату сбора", callback_data="admin_paid_dues")],
        [InlineKeyboardButton(text="Отметить оплату VPN", callback_data="admin_paid_vpn")],
        [InlineKeyboardButton(text="Сберегательный счёт", callback_data="admin_savings")],
        [InlineKeyboardButton(text="Время рассылки", callback_data="admin_schedule")],
        [InlineKeyboardButton(text="Назад", callback_data="back_main")]
    ])

def ack_button(type_: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Уведомление прочитано", callback_data=f"ack_{type_}")]])

def reply_menu_button() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Меню")]],
        resize_keyboard=True,
        one_time_keyboard=False
    )

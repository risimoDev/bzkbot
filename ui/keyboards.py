from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

def main_menu(is_admin: bool) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="Мой статус", callback_data="menu_status")],
        [InlineKeyboardButton(text="Уведомления", callback_data="menu_notifications")],
    ]
    if is_admin:
        rows.append([InlineKeyboardButton(text="Админ-панель", callback_data="menu_admin")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def notifications_menu(allow_dues: bool, allow_vpn: bool, show_status: bool) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=("Сбор: включено" if allow_dues else "Сбор: выключено"), callback_data="toggle_dues")],
        [InlineKeyboardButton(text=("VPN: включено" if allow_vpn else "VPN: выключено"), callback_data="toggle_vpn")],
        [InlineKeyboardButton(text=("Статус: показывать" if show_status else "Статус: скрывать"), callback_data="toggle_status")],
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
        [InlineKeyboardButton(text="Сумма VPN", callback_data="admin_vpn_amount")],
        [InlineKeyboardButton(text="Время рассылки", callback_data="admin_schedule")],
        [InlineKeyboardButton(text="Видимость статуса", callback_data="admin_status_visibility")],
        [InlineKeyboardButton(text="Пользователи", callback_data="admin_users_page_1")],
        [InlineKeyboardButton(text="Кастом уведомление", callback_data="admin_custom_notification")],
        [InlineKeyboardButton(text="История уведомлений", callback_data="admin_custom_history_1")],
        [InlineKeyboardButton(text="Назад", callback_data="back_main")]
    ])

def custom_notify_audience_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Всем активным", callback_data="custom_audience_all")],
        [InlineKeyboardButton(text="Список TG ID", callback_data="custom_audience_list")],
        [InlineKeyboardButton(text="Отмена", callback_data="menu_admin")]
    ])

def custom_history_page_keyboard(page: int, total_pages: int) -> InlineKeyboardMarkup:
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton(text="«", callback_data=f"admin_custom_history_{page-1}"))
    nav.append(InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav.append(InlineKeyboardButton(text="»", callback_data=f"admin_custom_history_{page+1}"))
    return InlineKeyboardMarkup(inline_keyboard=[nav, [InlineKeyboardButton(text="Назад", callback_data="menu_admin")]])

def batch_actions_keyboard(batch_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Повторить непрочитавшим", callback_data=f"resend_batch_{batch_id}")],
        [InlineKeyboardButton(text="Назад", callback_data="admin_custom_history_1")]
    ])

def ack_custom_keyboard(notif_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Прочитано", callback_data=f"ackc_{notif_id}")]])

def admin_users_page_keyboard(page: int, total_pages: int) -> InlineKeyboardMarkup:
    buttons = []
    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton(text="«", callback_data=f"admin_users_page_{page-1}"))
    nav_row.append(InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton(text="»", callback_data=f"admin_users_page_{page+1}"))
    buttons.append(nav_row)
    buttons.append([InlineKeyboardButton(text="Назад", callback_data="menu_admin")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def admin_user_actions_keyboard(user_id: int, show_status: bool) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=("Скрыть общий статус" if show_status else "Показать общий статус"), callback_data=f"admin_toggle_user_status_{user_id}")],
        [InlineKeyboardButton(text="Перекл. Сбор", callback_data=f"admin_toggle_component_dues_{user_id}"), InlineKeyboardButton(text="Перекл. VPN", callback_data=f"admin_toggle_component_vpn_{user_id}"), InlineKeyboardButton(text="Перекл. Сбережения", callback_data=f"admin_toggle_component_savings_{user_id}")],
        [InlineKeyboardButton(text="Назад", callback_data="admin_users_page_1")]
    ])

def ack_button(type_: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Уведомление прочитано", callback_data=f"ack_{type_}")]])

def reply_menu_button() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Меню")]],
        resize_keyboard=True,
        one_time_keyboard=False
    )

def welcome_message() -> str:
    return (
        "👋 Добро пожаловать!\n"
        "Введите кодовую фразу для доступа."
    )

def access_granted_message() -> str:
    return "✅ Доступ предоставлен. Ниже главное меню:"

def access_denied_message() -> str:
    return "⛔ Доступ запрещён. Введите корректную кодовую фразу."

def status_message(total_dues: int, total_vpn: int, savings: int) -> str:
    return (
        "📊 Статус\n"
        f"• Сборы: {total_dues}₽\n"
        f"• VPN: {total_vpn}₽\n"
        f"• Сберегательный счёт: {savings}₽"
    )

def status_hidden_message() -> str:
    return "🙈 Статус скрыт. Вы можете включить его в настройках."

def reminder_text(type_: str, dues_amount: int) -> str:
    if type_ == "dues":
        return f"🔔 Ежемесячный сбор: {dues_amount}₽. Нажмите кнопку ниже, когда прочитаете."
    return "🔔 Оплата VPN: проверьте актуальность. Нажмите кнопку ниже, когда прочитаете."

def admin_prompt_paid(type_: str) -> str:
    human = "сбора" if type_ == "dues" else "VPN"
    return f"🧾 Введите данные оплаты {human}:\n`tg_id сумма` (например: `123456789 500`)"

def admin_prompt_savings() -> str:
    return "💰 Введите новую сумму сберегательного счёта (в ₽):"

def saved_message() -> str:
    return "✅ Сохранено"

def marked_message() -> str:
    return "✅ Отмечено"

def admin_prompt_schedule(hour: int, minute: int) -> str:
    return (
        "⏰ Текущее время рассылки: "
        f"{hour:02d}:{minute:02d}\n"
        "Введите новое время в формате `HH:MM`"
    )

def schedule_updated(hour: int, minute: int) -> str:
    return f"✅ Время рассылки обновлено: {hour:02d}:{minute:02d}"

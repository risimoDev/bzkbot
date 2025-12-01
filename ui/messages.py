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

def admin_prompt_status_visibility() -> str:
    return ("👁 Введите управление видимостью статуса:\n"
            "`tg_id show` или `tg_id hide`\nНапример: `123456789 hide`")

def status_visibility_changed(tg_id: int, show: bool) -> str:
    return f"✅ Статус для {tg_id} теперь: {'показывать' if show else 'скрывать'}"

def admin_users_list(title: str, users: list[dict]) -> str:
    lines = ["👥 " + title]
    if not users:
        lines.append("(Нет пользователей)")
    for u in users:
        lines.append(
            f"ID:{u['id']} TG:{u['tg_id']} "
            f"{'✔' if u['active'] else '✖'} "
            f"STS:{'👁' if u['show_status'] else '🙈'} "
            f"DUES:{'🔔' if u['dues'] else '🚫'} VPN:{'🔔' if u['vpn'] else '🚫'}"
            f" | VDUES:{'👁' if u.get('show_dues', True) else '🙈'} "
            f"VVPN:{'👁' if u.get('show_vpn', True) else '🙈'} "
            f"VSAV:{'👁' if u.get('show_savings', True) else '🙈'}"
        )
    lines.append("\nНажмите номер для управления (пока через ввод команды или кнопку действия).")
    return "\n".join(lines)

def admin_user_status_toggled(tg_id: int, show: bool) -> str:
    return f"🔄 Видимость статуса для {tg_id}: {'показывать' if show else 'скрывать'}"

def component_toggled(tg_id: int, component: str, show: bool) -> str:
    names = {"dues": "Сбор", "vpn": "VPN", "savings": "Сбережения"}
    return f"🔄 {names.get(component, component)} для {tg_id}: {'показывать' if show else 'скрывать'}"

def custom_notify_intro() -> str:
    return "✉ Создание кастомного уведомления. Выберите аудиторию."

def custom_notify_enter_ids() -> str:
    return "Введите TG ID через пробел или запятую:"

def custom_notify_enter_text(audience_desc: str) -> str:
    return f"Введите текст уведомления для: {audience_desc}"

def custom_notify_sent(count: int) -> str:
    return f"✅ Отправлено уведомлений: {count}"

def custom_notify_invalid_ids() -> str:
    return "Некорректный формат списка ID."

def custom_history_list(title: str, batches: list[dict]) -> str:
    lines = ["🗂 " + title]
    if not batches:
        lines.append("(Нет отправленных батчей)")
    for b in batches:
        lines.append(
            f"{b['sent_at']} | {b['batch_id'][:6]} | ack {b['acked']}/{b['total']}\n" +
            (b['text'][:80] + ("…" if len(b['text']) > 80 else ""))
        )
    return "\n".join(lines)

def batch_resend_result(batch_id: str, attempted: int, sent: int) -> str:
    return f"🔁 Батч {batch_id[:6]}: повторно попыток={attempted}, доставлено={sent}"

def custom_acknowledged() -> str:
    return "✅ Уведомление отмечено прочитанным"

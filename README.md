# BZKBot

Телеграм-бот для учёта оплат (ежемесячный сбор и VPN), напоминаний и админ-управления через кнопки.

## Функционал
- Доступ только по кодовой фразе (`ACCESS_PHRASE`).
- Два типа уведомлений: сбор (фикс. сумма) и VPN.
- Ежедневная рассылка пока пользователь не подтвердит прочтение.
- Админ-панель (inline-кнопки + FSM): отметить оплату, изменить сбережения, изменить время рассылки.
- Отдельное хранение времени рассылки в БД, динамическое обновление задания APScheduler.

## Стек
- Python 3.11
- aiogram 3.x
- APScheduler (ежедневные задачи)
- SQLite (файл БД)
- Docker/Docker Compose для деплоя

## Структура проекта
```
main.py                # Точка входа
bot_config.py          # Конфиг и загрузка .env
db/dao.py              # Работа с SQLite
services/reminders.py  # Логика рассылки
ui/keyboards.py        # Inline + Reply клавиатуры
ui/messages.py         # Тексты сообщений
requirements.txt       # Зависимости
Dockerfile             # Образ
docker-compose.yml     # Оркестрация
.dockerignore          # Исключения
README.md
```

## Переменные окружения (.env)
```
BOT_TOKEN=7746...C2P8
ACCESS_PHRASE=ChevCheliosBZK
ADMIN_IDS=757479170
DUES_AMOUNT=500
TIMEZONE=Europe/Moscow
DB_PATH=bzkbot.db            # Для локального запуска
```

Для Docker укажите путь БД на volume:
```
DB_PATH=/data/bzkbot.db
```

## Локальный запуск (Windows PowerShell)
```
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

## Docker

### .dockerignore (создан)
Исключает виртуальное окружение, артефакты и кэш.

### Сборка и запуск
```
docker compose build
docker compose up -d
docker compose logs -f
```

### Обновление
```
docker compose up -d --build
```

### Резервная копия БД
```
docker cp bzkbot:/data/bzkbot.db ./backup_$(date +%F).db
```

## Команды / текст
- `/start` — вход, если активен сразу показывает меню.
- Кнопка Reply «Меню» — вызывает главное меню.
- Inline меню: Статус, Уведомления, Админ.
- Админ: отметка оплат (сбор/VPN), изменение сбережений, установка времени `HH:MM`.

## Изменение времени рассылки
Админ → «Время рассылки» → ввод `HH:MM`. APScheduler пересоздаёт задачу.

## Безопасность
- Не коммитьте реальный `BOT_TOKEN` в публичный репозиторий.
- В Docker используется непривилегированный пользователь `app`.

## Быстрый деплой на сервере
1. Установить Docker + Compose.
2. Скопировать файлы проекта и создать `.env` с `DB_PATH=/data/bzkbot.db`.
3. Выполнить команды сборки.
4. Проверить логи.

## Healthcheck
В `Dockerfile` добавлен простой `HEALTHCHECK` (можно расширить метриками через отдельный эндпоинт при необходимости).

## TODO/Идеи для улучшения
- Добавить экспорт CSV оплат.
- Добавить метрики Prometheus (опционально).
- Добавить ограничение частоты команд (rate limit).


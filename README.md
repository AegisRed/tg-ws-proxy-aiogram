# TGWS aiogram SOCKS5 adapter

Небольшой Python-адаптер для запуска Telegram-ботов на **aiogram 3** через внешний **SOCKS5-прокси**. Использует стандартный облачный `api.telegram.org`; локальный Telegram Bot API и ключи приложения Telegram **не нужны**.

> [!IMPORTANT]
> **Это клиентский SOCKS5-адаптер, а не готовый прокси-сервер.** Для подключения нужен существующий, доступный с машины бота SOCKS5 endpoint (`host:port`). Библиотека не создаёт прокси, WebSocket-туннель или удалённую точку выхода автоматически. Если в сети заблокирован прямой доступ к Telegram, SOCKS5-сервер должен иметь к нему доступ.

## Быстрый старт

Python 3.10+, aiogram 3. Пакет пока устанавливается из GitHub:

```bash
pip install 'tgws-botapi[aiogram] @ git+https://github.com/AegisRed/tg-ws-proxy-aiogram.git'
```

Укажите URL **своего** SOCKS5-прокси в окружении:

```dotenv
BOT_TOKEN=YOUR_TEST_BOT_TOKEN_FROM_BOTFATHER
TGWS_SOCKS5_URL=socks5://127.0.0.1:1080
```

Замените обычное создание объекта `Bot`:

```python
from tgws_botapi.aiogram import create_aiogram_bot

bot = create_aiogram_bot(BOT_TOKEN)
```

`Dispatcher`, роутеры, фильтры, клавиатуры и хендлеры не меняются.

URL можно передать прямо при создании бота:

```python
bot = create_aiogram_bot(
    BOT_TOKEN,
    proxy_url="socks5://proxy.example:1080",
)
```

Для прокси с авторизацией поддерживается обычный URL, например `socks5://user:password@host:1080` (специальные символы в логине и пароле нужно URL-кодировать).

### Что происходит под капотом

`aiogram` создаёт `AiohttpSession(proxy=...)`. Запросы `getUpdates`, `sendMessage`, `getFile` и остальные Bot API идут через SOCKS5 к **официальному** Telegram Bot API по HTTPS. Используется `aiohttp-socks`. Файлы передаются тем же проксируемым HTTP-клиентом.

Если `TGWS_SOCKS5_URL` не задан или имеет неправильный формат, библиотека выдаёт ошибку при запуске. **Без разрешения пользователя переход на прямое подключение не выполняется.**

### Чем отличается от старой реализации

| | SOCKS5 (рекомендуется) | Старый MTProto/WS runtime |
| --- | --- | --- |
| Telegram Bot Token | Нужно | Нужно |
| `TELEGRAM_API_ID` / `TELEGRAM_API_HASH` | **Не нужны** | Нужны |
| Локальный Bot API / TDLib | **Не нужен** | Нужен |
| Внешний SOCKS5 сервер | **Нужен** | Не нужен (есть собственный MTProto-маршрут) |
| Отдельный контейнер прокси | Не обязателен | Ранее требовался |

Исходный Flowseal MTProto/WS-runtime пока **оставлен в репозитории как legacy-код** для обратной совместимости. Его CLI, Dockerfile и `docker-compose.yml` не относятся к новому SOCKS5-режиму и по-прежнему требуют отдельного `api_id/api_hash` при запуске. Они не используются в примере выше и не нужны для `Event_bot`. При переходе на SOCKS5 старый шлюз запускать не нужно.

Для исторического CLI установите дополнительные зависимости: `pip install -e '.[aiogram,legacy]'`. Перед удалением legacy-кода следует отдельно проверить все его потребители.

## Проверка

```bash
pip install -e '.[aiogram,legacy,dev]'
python -m unittest discover -s tests -v
python -m build
```

Автоматические тесты проверяют создание сессии, URL, режим «без прямого fallback» и обратную совместимость старого ядра **без реального Telegram-токена**. Сквозное соединение до Telegram необходимо проверить самостоятельно с доступным SOCKS5-прокси и отдельным тестовым ботом.

После перехода на SOCKS5 **не вызывайте** Telegram Bot API `logOut`: бот снова работает с обычным облачным Bot API. Если ранее вы вызывали `logOut` для локального сервера, переход обратно в облако может требовать ожидания до 10 минут.

## Происхождение и лицензия

Историческое MTProto/WS-ядро основано на [Flowseal/tg-ws-proxy](https://github.com/Flowseal/tg-ws-proxy), © Flowseal, MIT. Обновления адаптера поддерживаются [AegisRed](https://github.com/AegisRed). Лицензия исходного проекта сохранена в [LICENSE](LICENSE).

> [!TIP]
>
> ### 🎉 Поддержать меня
>
> **USDT (TRC20)**: `TZ7gTmzay3DKWZvwHCRtrxxNBVhhMcZyuE`
>
> **USDT (SOL)**: `CsGRX1E1ed3zCN7xSiUh27jwBQFcYGr8amRdib4pKh75`
>
> Проект полностью бесплатен для всех, но если поддержите буду очень благодарен💕.

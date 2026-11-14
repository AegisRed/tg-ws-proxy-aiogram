# TGWS BotAPI

Экспериментальный **headless runtime для Python-ботов на Telegram Bot API**. Объединяет MTProto → WebSocket-транспорт [Flowseal/tg-ws-proxy](https://github.com/Flowseal/tg-ws-proxy) с локальным Telegram Bot API-сервером, который умеет подключаться к MTProto-прокси.

Цель: положить runtime в Docker-проект бота, настроить токены один раз и запускать бот обычной командой без отдельного GUI, VPN или ручного управления прокси.

> [!IMPORTANT]
> **Статус: alpha/PoC.** Python-обёртка и конфигурация готовы для тестов, но сквозная проверка через настоящие Telegram DC ещё не выполнена. Запуск требует **патченного** `telegram-bot-api` с поддержкой `--tdlib-proxy-type=mtproto`; стандартный бинарник не подходит. Нельзя утверждать работоспособность во всех заблокированных сетях: доступен должен быть хотя бы один WebSocket/Cloudflare-маршрут.

## Быстрый старт — Docker

Нужны Docker Engine/Compose (или Docker Desktop на Windows), `api_id`/`api_hash` из [my.telegram.org](https://my.telegram.org), а также токен от BotFather.

```bash
cp .env.example .env
# Заполните TELEGRAM_API_ID, TELEGRAM_API_HASH, BOT_TOKEN
docker compose up --build -d
docker compose logs -f example-bot
```

Это запускает **один контейнер** с тремя управляемыми процессами: вашим Python-ботом, локальным Telegram Bot API и Flowseal MTProto WebSocket-прокси. Внутренние порты не публикуются наружу. Команда запускает демонстрационный echo-бот; вместо него можно указать свой Python-модуль.

Контейнер собирается поверх [avbor/docker-telegram-bot-api](https://github.com/avbor/docker-telegram-bot-api), который добавляет MTProto proxy-параметры к TDLib. В производственной среде закрепите исходный Docker-образ по проверенному digest (параметр сборки `BOT_API_IMAGE`) и самостоятельно проверьте совместимость его версии с актуальным Bot API.

### Подключить к своему aiogram 3 боту

Установка Python-части:

Пока пакет не опубликован в PyPI, установите его напрямую из форка:

```bash
pip install 'tgws-botapi[aiogram] @ git+https://github.com/AegisRed/tg-ws-proxy-aiogram.git'
```

Либо скачайте wheel из GitHub Release и установите его с дополнительной
зависимостью `aiogram`. Команда `pip install 'tgws-botapi[aiogram]'` станет
доступна только после отдельной публикации пакета в PyPI.

Замените создание объекта бота:

```python
from tgws_botapi.aiogram import create_aiogram_bot

bot = create_aiogram_bot(BOT_TOKEN)
```

Обработчики, `Dispatcher`, клавиатуры и бизнес-логика `aiogram` остаются прежними. Помощник автоматически берёт адрес локального Bot API из переменной `TGWS_BOT_API_URL` (по умолчанию `http://127.0.0.1:8081`). **Python-пакет сам по себе не содержит бинарник Bot API**: для полностью автономного запуска используйте Docker runtime или установите совместимую сборку сервера отдельно.

Другой вариант — использовать обычный объект `Bot`:

```python
from aiogram import Bot
from tgws_botapi.aiogram import aiogram_session

bot = Bot(BOT_TOKEN, session=aiogram_session())
```

### Свой Docker-проект

После публикации образа можно использовать его как основу:

```dockerfile
FROM ghcr.io/aegisred/tg-ws-proxy-aiogram:<release-tag>
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["run", "--", "python", "bot.py"]
```

Замените `<release-tag>` на существующий релиз; **до первого релиза публичного образа может не быть**. Для локальной проверки можно сначала собрать исходный образ командой `docker build -t tgws-botapi .`, затем использовать `FROM tgws-botapi`.

## Настройки

Конфигурация полностью через переменные окружения — GUI удалён.

| Переменная | Назначение | По умолчанию |
| --- | --- | --- |
| `TELEGRAM_API_ID` | ID приложения Telegram (обязательно) | — |
| `TELEGRAM_API_HASH` | Hash приложения (обязательно) | — |
| `BOT_TOKEN` | Токен вашего бота (требуется примеру) | — |
| `TGWS_BOTAPI_BINARY` | Путь к **патченному** `telegram-bot-api` | `telegram-bot-api` |
| `TGWS_PROXY_PORT` | Порт встроенного MTProto-прокси | `1443` |
| `TGWS_BOT_API_PORT` | Порт локального Bot API | `8081` |
| `TGWS_BOT_API_URL` | Адрес для Python-адаптера | `http://127.0.0.1:8081` |
| `TGWS_SECRET` | MTProto secret (32 hex) | генерируется при запуске |
| `TGWS_DATA_DIR` | Постоянное хранилище Bot API | `.tgws-data` / Docker volume |
| `TGWS_CFPROXY_DOMAINS` | Свои Cloudflare-домены через пробел/запятую | автоматически |
| `TGWS_ALLOW_DIRECT_FALLBACK` | Разрешить прямой TCP при сбое WS | `false` |

Runtime всегда привязывает оба сервера к loopback-адресу; параметр `TGWS_ALLOW_DIRECT_FALLBACK=false` запрещает Flowseal незаметно обходить WebSocket-маршрут прямым TCP.

## Запуск без Docker

Для запуска в обычном окружении нужен установленный совместимый Bot API Server с MTProto patch (например, собранный по [патчам avbor](https://github.com/avbor/docker-telegram-bot-api/tree/main/add_proxy)) и Python 3.10+.

```bash
pip install '.[aiogram]'
export TELEGRAM_API_ID=12345
export TELEGRAM_API_HASH=your_hash
export BOT_TOKEN=your_token
tgws-botapi run -- python -m examples.echo_bot
```

Команда `tgws-mtproto` запускает только сетевое ядро Flowseal и предназначена для отладки.

## Область ответственности

- Проксируется **связь Bot API-сервера с Telegram DC**, а не произвольные HTTP-запросы ко всем сайтам. Вызовы DeepSeek, Boosty, платёжных систем и т. п. требуют отдельного канала связи.
- Для домашних серверов рекомендуется long polling. Webhook по-прежнему требует доступный Telegram HTTPS endpoint.
- Перед переводом действующего бота с `api.telegram.org` на локальный сервер Telegram рекомендует выполнить [Bot API `logOut`](https://core.telegram.org/bots/api#logout). Не запускайте один токен на двух Bot API-серверах одновременно: возможна потеря или дублирование обновлений.
- Для production необходимо проверить методы, которыми реально пользуется бот, включая свежие возможности Bot API. Наличие локального сервера само по себе не гарантирует поддержку последних методов.
- Не публикуйте `.env`, токены, `api_hash` или директорию данных, не открывайте внутренние порты в интернет.

## Проверка и релизы

```bash
python -m pip install -e '.[dev]'
python -m unittest discover -s tests -q
python -m build
```

CI проверяет библиотеку на Linux и Windows. По тегу `v*` workflow готовит wheel/sdist для GitHub Releases и контейнер GHCR. Выпуск не запускается автоматически без тега, PyPI publish не выполняется до настройки trusted publishing.

## Авторы и лицензия

Сетевое ядро основано на [Flowseal/tg-ws-proxy](https://github.com/Flowseal/tg-ws-proxy), © Flowseal, MIT. Форк поддерживается [AegisRed](https://github.com/AegisRed). Все права и условия оригинальной MIT-лицензии сохранены в [LICENSE](LICENSE).

> [!TIP]
>
> ### 🎉 Поддержать меня
>
> **USDT (TRC20)**: `TZ7gTmzay3DKWZvwHCRtrxxNBVhhMcZyuE`
>
> **USDT (SOL)**: `CsGRX1E1ed3zCN7xSiUh27jwBQFcYGr8amRdib4pKh75`

Проект полностью бесплатен для всех, но если поддержите буду очень благодарен💕.

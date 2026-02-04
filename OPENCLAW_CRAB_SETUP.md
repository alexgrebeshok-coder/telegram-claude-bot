# Крабик через OpenClaw «из коробки»

Инструкция по настройке бота **Крабик** как Telegram-канала OpenClaw. При такой настройке **отдельные серверы Flask и MCP не используются** — только OpenClaw Gateway.

## Чеклист

- [ ] **Шаг 1:** Остановить любой процесс, использующий токен Крабика (см. раздел 1).
- [ ] **Шаг 2:** Установить OpenClaw CLI и пройти `openclaw onboard --install-daemon` с токеном Крабика (разделы 2–3).
- [ ] **Шаг 3:** Убедиться, что запущен только OpenClaw Gateway; при необходимости запустить `openclaw gateway --port 18789` (раздел 4).
- [ ] **Шаг 4:** Проверить ответ бота в Telegram (раздел 5).

## Схема работы

```
Telegram (Крабик)  →  OpenClaw Gateway (порт 18789)  →  Pi Agent  →  ответ в Telegram
```

Один процесс — Gateway. Токен бота Крабика настраивается в OpenClaw.

## Шаги

### 1. Освободить токен Крабика

С токеном бота может работать только **один** потребитель. Перед подключением к OpenClaw нужно остановить всё, что уже использует этот токен:

- Любой процесс/сервис, который показывает «Flask Server / MCP Server» и обрабатывает сообщения Крабика.
- **Не запускать** этот репозиторий (telegram_claude_bot) с тем же BOT_TOKEN, что и Крабик — иначе конфликт с OpenClaw.

**Как остановить процессы, использующие токен:**

- **macOS (launchd):** `launchctl list | grep -i claude` или `grep -l BOT_TOKEN ~/Library/LaunchAgents/*.plist 2>/dev/null` — затем `launchctl unload ~/Library/LaunchAgents/<имя>.plist`
- **Linux (systemd):** `systemctl --user list-units | grep -i telegram` (или claude/openclaw) — затем `systemctl --user stop <unit>`
- **Docker:** `docker ps` — найти контейнер с ботом, затем `docker stop <container_id>`
- **Процесс Python (run.py):** завершить терминал, где запущен `python run.py`, или `pkill -f "run.py"` (если это именно бот с токеном Крабика)

### 2. Установить OpenClaw

```bash
# Вариант 1: официальный установщик
curl -fsSL https://openclaw.ai/install.sh | bash

# Вариант 2: через npm
npm install -g openclaw@latest
```

Требуется **Node.js ≥ 22**.

### 3. Онбординг с токеном Крабика

```bash
openclaw onboard --install-daemon
```

В мастере:

- Выбрать канал **Telegram**.
- Указать **токен бота Крабика** (из @BotFather).

Токен можно задать и вручную в `~/.openclaw/openclaw.json`:

```json
{
  "channels": {
    "telegram": {
      "enabled": true,
      "botToken": "ВАШ_ТОКЕН_КРАБИКА",
      "dmPolicy": "pairing"
    }
  }
}
```

Или через переменную окружения: `TELEGRAM_BOT_TOKEN=...`.

### 4. Запускать только Gateway

Отдельные Flask и MCP **не нужны**. Запускается только OpenClaw Gateway:

- Если при онбординге был установлен демон — Gateway уже запущен.
- Проверка: `openclaw gateway status` или `openclaw health`.
- Ручной запуск: `openclaw gateway --port 18789`.

Дашборд (опционально): http://127.0.0.1:18789/

### 5. Проверить в Telegram

Написать боту Крабику в Telegram (например, отправить `/status`, если команда включена в OpenClaw, или любое сообщение). Ответ должен приходить от OpenClaw (агент Pi). Сообщений про «Flask Server» или «MCP Server» быть не должно.

Если бот не отвечает:

- Убедиться, что никакой другой процесс не использует тот же токен.
- Проверить pairing для личных сообщений: `openclaw pairing list telegram`, при необходимости одобрить код.

## Важно

- **Flask и MCP** в схеме «Крабик = OpenClaw» **не используются**. Не поднимайте отдельные серверы — достаточно Gateway.
- Этот репозиторий (telegram_claude_bot) — **альтернативный** бот (Claude Code через subprocess). Для Крабика через OpenClaw он не используется с тем же токеном; Крабиком в этом режиме управляет только OpenClaw.

Документация OpenClaw: https://docs.clawd.bot/

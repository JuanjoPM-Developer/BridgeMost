# TeleGhost 👻

**Telegram ↔ Mattermost Transparent Bridge**

TeleGhost makes your Telegram messages appear natively in Mattermost — as your real user, with your avatar and name. Bot responses from Mattermost are relayed back to Telegram instantly.

Unlike Matterbridge, webhooks, or n8n integrations that post with prefixes like `[User]` or from a bot account, TeleGhost posts as **your actual Mattermost user** via Personal Access Token. Nobody in Mattermost can tell you're writing from Telegram.

## ✨ Features

- **Transparent identity** — Messages appear as your real MM user (avatar, name, everything)
- **Full media support** — Photos, documents, audio, video, voice messages, stickers — bidirectional
- **Multi-bot routing** — Talk to multiple MM bots; switch with `/bot name`
- **Markdown conversion** — MM markdown automatically converted to Telegram MarkdownV2
- **Retry with backoff** — Exponential backoff on failures, error notifications via Telegram
- **Health endpoint** — HTTP health check at `/health` for monitoring
- **Message splitting** — Long messages automatically split for Telegram's 4096-char limit
- **Lightweight** — ~55MB RAM, ~250ms latency, asyncio-based

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- A Mattermost server (self-hosted)
- A Telegram bot token (free from [@BotFather](https://t.me/BotFather))
- A Mattermost Personal Access Token

### Installation

```bash
git clone https://github.com/YOUR_USER/teleghost.git
cd teleghost
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Configuration

```bash
cp config.example.yaml config.yaml
# Edit config.yaml with your tokens
```

### Run

```bash
python3 -m teleghost
```

### Systemd Service (recommended)

```bash
sudo cp teleghost.service.example /etc/systemd/system/teleghost.service
# Edit paths in the service file
sudo systemctl enable --now teleghost
```

## ⚙️ Configuration

```yaml
telegram:
  bot_token: "YOUR_TELEGRAM_BOT_TOKEN"

mattermost:
  url: "http://localhost:8065"
  bot_token: "MM_BOT_TOKEN"          # Any bot token (for reading responses)
  bot_user_id: "BOT_USER_ID"         # User ID of the bot above

users:
  - telegram_id: 123456789           # Your Telegram user ID
    telegram_name: "Your Name"
    mm_user_id: "your_mm_user_id"
    mm_token: "YOUR_PERSONAL_ACCESS_TOKEN"
    bots:
      - name: "MyBot"
        mm_bot_id: "bot_user_id"
        default: true
      - name: "AnotherBot"
        mm_bot_id: "another_bot_user_id"

health:
  port: 9191
```

### Getting your tokens

1. **Telegram Bot Token**: Message [@BotFather](https://t.me/BotFather) → `/newbot`
2. **Telegram User ID**: Message [@userinfobot](https://t.me/userinfobot)
3. **MM Personal Access Token**: Mattermost → Profile → Security → Personal Access Tokens
4. **MM User/Bot IDs**: Mattermost API or `mmctl user search`

## 🤖 Multi-Bot Routing

Configure multiple bots and switch between them from Telegram:

```
/bot           → List available bots and show active one
/bot MyBot     → Switch to MyBot
/bot AnotherBot → Switch to AnotherBot
```

Messages from non-active bots are prefixed with `[BotName]` for clarity.

## 📊 Health Endpoint

```bash
curl http://localhost:9191/health
```

```json
{
  "status": "ok",
  "version": "0.1.0",
  "uptime": "2h15m30s",
  "messages": {
    "tg_to_mm": 42,
    "mm_to_tg": 38,
    "errors": 0
  }
}
```

## 🏗️ Architecture

```
┌──────────┐     ┌──────────────┐     ┌──────────────┐
│ Telegram │◄───►│  TeleGhost   │◄───►│  Mattermost  │
│  (User)  │     │  (Bridge)    │     │  (Bot + User)│
└──────────┘     └──────────────┘     └──────────────┘
     │                  │                     │
     │  Bot API         │  REST API           │
     │  (push)          │  (poll/post)        │
     └──────────────────┴─────────────────────┘
```

1. **TG → MM**: User sends message via Telegram → TeleGhost posts it to MM as the user's real account
2. **MM → TG**: Bot responds in MM → TeleGhost polls the DM channel → relays response to Telegram

## 📋 Roadmap

- [x] Bidirectional text + media relay
- [x] Retry with exponential backoff
- [x] Markdown MM → Telegram conversion
- [x] Health endpoint
- [x] Multi-bot routing (`/bot` command)
- [x] Edit/delete synchronization
- [x] WebSocket for MM (replace polling)
- [x] Reactions relay
 (multiple TG users)

## 🛡️ Security

- `config.yaml` contains secrets — **never commit it** (it's in `.gitignore`)
- Personal Access Tokens have full user permissions — use dedicated accounts if concerned
- Health endpoint binds to `127.0.0.1` by default
- Telegram bot restricted via `telegram_id` allowlist in config

## 📄 License

MIT — see [LICENSE](LICENSE)

## 🙏 Credits

Built with:
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
- [aiohttp](https://github.com/aio-libs/aiohttp)

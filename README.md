# BridgeMost 👻

[![CI](https://github.com/JuanjoPM-Developer/BridgeMost/actions/workflows/ci.yml/badge.svg)](https://github.com/JuanjoPM-Developer/BridgeMost/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/bridgemost)](https://pypi.org/project/bridgemost/)

**Multi-Platform ↔ Mattermost Transparent Bridge**

BridgeMost makes your messages from **Telegram, Google Chat, or any supported platform** appear **natively** in Mattermost — as your real user, with your avatar and name. Bot responses relay back instantly via WebSocket.

Unlike Matterbridge or webhooks that post with `[User]` prefixes, BridgeMost posts as **your actual Mattermost account** using Personal Access Tokens. Nobody in Mattermost can tell you're writing from another platform.

## 🔌 Supported Platforms (Adapters)

| Platform | Status | Description |
|----------|--------|-------------|
| **Telegram** | ✅ Production | Full support — text, media, voice, reactions, edits, deletes |
| **Google Chat** | ✅ v2.1.0 | Workspace ghost mode via Service Account + domain-wide delegation |
| **Slack** | 🔜 Planned | User token impersonation |
| **Matrix** | 🔜 Planned | Application Service ghost mode |

> **Plugin architecture (v2.0+):** Each platform is an independent adapter module. Adding a new platform = one Python file implementing `BaseAdapter`. Zero changes to the core engine.

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🪪 Transparent identity | Posts as your real MM user (avatar, name, everything) |
| 📁 Full media | Photos, documents, audio, video, voice — bidirectional |
| 🎤 Voice-to-text | Voice messages auto-transcribed via Whisper API |
| 🤖 Multi-bot routing | Talk to multiple MM bots; switch with `/bot name` |
| ⚡ Real-time WebSocket | Responses arrive instantly (no polling) |
| ✏️ Edit & delete sync | Edits and deletes stay in sync both ways |
| 😀 Reactions | Emoji reactions synced bidirectionally |
| ⌨️ Typing indicator | Synthetic "Bot is typing..." on the chat side |
| 📝 Markdown | MM markdown auto-converted to platform format |
| 🔒 Startup checks | Validates tokens + discovers channels before starting |
| 💾 Persistent mapping | SQLite store for message IDs (survives restarts) |
| 🩺 Health endpoint | HTTP `/health` on configurable port |
| 👥 Multi-user | Multiple users, each with their own identity and bot routing |
| 🐳 Docker | Multi-stage image, ~55 MB |

~55 MB RAM · ~250 ms latency · asyncio-based · Python 3.11+

> **Multi-user ready:** Multiple people can use the same BridgeMost instance — each with their own chat account, Mattermost identity, and bot routing. Add users to `config.yaml` and they appear as themselves in Mattermost. No shared accounts, no impersonation.

---

## 🏗️ Architecture (v2.0+)

```
┌──────────────┐
│   Telegram   │─┐
├──────────────┤ │         ┌──────────────┐         ┌──────────────┐
│ Google Chat  │─┼────────►│  BridgeMost  │◄───────►│  Mattermost  │
├──────────────┤ │         │  Core Engine  │  WS+API │   (Bots)     │
│    Slack     │─┤         └──────────────┘         └──────────────┘
├──────────────┤ │          Adapters │ Core │ MM
│    Matrix    │─┘
└──────────────┘
```

Three layers:
1. **Adapters** — Platform-specific plugins (`telegram.py`, `googlechat.py`, etc.)
2. **Core Engine** — Routing, mapping, sync, retry, health — platform-agnostic
3. **Mattermost Connector** — WebSocket, REST API, file upload

Each adapter implements `BaseAdapter` (8 methods: start, stop, send_message, edit, delete, react, typing, clear_reactions).

---

## 🚀 Installation — Step by Step

### What you need

| # | Item | Where to get it |
|---|------|----------------|
| 1 | **Mattermost server** (self-hosted) | You must be admin or have an admin enable PAT support |
| 2 | **Chat platform bot token** | Telegram: [@BotFather](https://t.me/BotFather) → `/newbot` |
| 3 | **Your platform user ID** | Telegram: message [@userinfobot](https://t.me/userinfobot) |
| 4 | **Python 3.11+** | `python3 --version` to check |
| 5 | **Git** | `git --version` to check |

### Step 1 — Enable Personal Access Tokens on Mattermost

> ⚠️ **This step is REQUIRED.** Without it, BridgeMost cannot post as your user.

**Option A — Via Mattermost UI (admin):**
1. Go to **System Console → Authentication → Token Access**
2. Set **Enable Personal Access Tokens** to `true`
3. Save

**Option B — Via command line (requires access to the server):**
```bash
# If mmctl is available:
mmctl --local config set ServiceSettings.EnableUserAccessTokens true

# Or via REST API with admin token:
curl -X PUT http://localhost:8065/api/v4/config/patch \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"ServiceSettings": {"EnableUserAccessTokens": true}}'
```

### Step 2 — Clone and install

```bash
git clone https://github.com/JuanjoPM-Developer/BridgeMost.git
cd BridgeMost
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Or via PyPI:
```bash
pip install bridgemost
```

Or via Docker:
```bash
docker compose up -d
```

### Step 3 — Configure

**Option A — Interactive wizard (recommended for Telegram):**

```bash
python3 -m bridgemost setup
```

The wizard will:
1. Connect to your Mattermost server
2. Log you in (password is NOT stored)
3. Auto-create a Personal Access Token for BridgeMost
4. List all bots on the server — you pick which ones to bridge
5. Ask for your platform bot token and user ID
6. Generate `config.yaml` automatically

**Option B — Manual configuration:**

```bash
cp config.example.yaml config.yaml
```

Then edit `config.yaml` — see the [Configuration Reference](#-configuration-reference) below.

### Step 4 — Run

```bash
# Foreground (for testing):
python3 -m bridgemost

# Or as a systemd service (recommended for production):
sudo cp bridgemost.service.example /etc/systemd/system/bridgemost.service
# Edit the service file — update paths to match your installation
sudo systemctl daemon-reload
sudo systemctl enable --now bridgemost
```

### Step 5 — Test

1. Send a message from your chat platform to the BridgeMost bot
2. The message should appear in Mattermost as **your real user**
3. When the MM bot responds, the response should appear in your chat

---

## ⚙️ Configuration Reference

### Minimal config.yaml (Telegram adapter)

```yaml
telegram:
  bot_token: "123456:ABC-DEF..."        # From @BotFather

mattermost:
  url: "http://localhost:8065"           # Your MM server URL (http or https)
  bot_token: "abc123..."                 # Any bot's access token (for WebSocket)
  bot_user_id: "a1b2c3d4..."            # User ID of that bot

users:
  - telegram_id: 123456789              # Your numeric platform user ID
    telegram_name: "Your Name"           # Display name (for logs only)
    mm_user_id: "x1y2z3..."             # Your Mattermost user ID
    mm_token: "your-pat-here"           # Your Personal Access Token
    bots:
      - name: "mybot"                   # Friendly name (used with /bot command)
        mm_bot_id: "bot-user-id-here"   # The bot's Mattermost user ID
        mm_dm_channel: ""               # Leave empty — auto-discovered at startup
        default: true                   # First bot to talk to when bridge starts
```

### How to find each value

| Field | How to get it |
|-------|--------------|
| `telegram.bot_token` | [@BotFather](https://t.me/BotFather) → `/newbot` → copy the token |
| `telegram_id` | Send any message to [@userinfobot](https://t.me/userinfobot) |
| `mattermost.url` | The URL you use to open Mattermost in your browser |
| `mattermost.bot_token` | MM → Integrations → Bot Accounts → pick any bot → copy token. Or ask your admin. |
| `mattermost.bot_user_id` | `mmctl user search <botname>` → copy `id`. Or: `curl http://YOUR_MM/api/v4/users/username/<botname> -H "Authorization: Bearer TOKEN"` → `"id"` |
| `mm_user_id` | Same as above with your own username |
| `mm_token` (PAT) | MM → Profile → Security → Personal Access Tokens → Create. Or wizard creates it. |
| `mm_bot_id` | The Mattermost user ID of each bot you want to talk to |
| `mm_dm_channel` | **Leave empty** — auto-discovered at startup. |

### Optional sections

```yaml
# Voice-to-text transcription (requires a Whisper-compatible API)
voice_to_text:
  url: "http://localhost:9000"          # Whisper endpoint
  api_key: ""                           # For OpenAI/Groq; empty for local Whisper
  model: "large-v3"                     # large-v3, whisper-1, whisper-large-v3-turbo
  language: ""                          # "es", "en", or "" for auto-detect
  keep_audio: true                      # Also attach audio file alongside transcript

# Health monitoring endpoint
health:
  port: 9191                            # HTTP health check on this port

# Message persistence
storage:
  data_dir: ""                          # SQLite DB location; empty = working directory

# Logging
logging:
  level: "INFO"                         # DEBUG, INFO, WARNING, ERROR
  file: ""                              # Log file path, or "" for stdout only
```

---

## 🤖 Chat Commands (Telegram adapter)

| Command | Description |
|---------|-------------|
| `/bot` | List all available bots and show which one is active |
| `/bot name` | Switch to a different bot |
| `/bots` | Show all bots with live 🟢/⚫ online status |
| `/status` | Detailed info about the active bot |

---

## 🎤 Voice-to-Text

When `voice_to_text` is configured, voice messages are transcribed before posting:

> 🎤 Hello, this is what I said in the voice message

If `keep_audio: true`, the original audio file is also attached.

Compatible APIs:
- [OpenAI Whisper API](https://platform.openai.com/docs/guides/speech-to-text) (`whisper-1`)
- [Groq Whisper](https://console.groq.com/) (`whisper-large-v3-turbo` — free tier)
- [faster-whisper-server](https://github.com/fedirz/faster-whisper-server) (self-hosted, any model)
- Any endpoint accepting `POST` with `multipart/form-data` and returning `{"text": "..."}`

---

## 📊 Health Endpoint

```bash
curl http://localhost:9191/health
```

```json
{
  "status": "ok",
  "version": "2.0.1",
  "transport": "websocket",
  "uptime": "2h15m30s",
  "messages": { "tg_to_mm": 42, "mm_to_tg": 38, "errors": 0 },
  "store": { "persistent_mappings": 156 }
}
```

---

## 🔧 Troubleshooting

| Problem | Solution |
|---------|----------|
| `FATAL: Token validation FAILED` | PAT is invalid/expired. Create a new one in MM → Profile → Security → PAT. Also verify `EnableUserAccessTokens` is `true`. |
| `⚠️ Token expirado` alert | Same — renew PAT, update `mm_token` in config.yaml, restart. |
| `Zero DM channels discovered` | Make sure you've DM'd each bot in MM at least once. Verify `mm_bot_id` values are correct (26 alphanumeric chars). |
| `WS auth rejected (CLOSE on connect)` | The `mattermost.bot_token` is invalid. Get a valid one from Integrations → Bot Accounts. |
| `OSError: [Errno 98] address already in use` | Another process on health port. Change `health.port` in config. |
| `[BotName]` prefix on messages | Normal in multi-bot mode to identify which bot responded. Single bot = no prefix. |
| Voice not transcribed | Check `voice_to_text.url` is reachable. For OpenAI/Groq, verify `api_key`. |
| `EnableUserAccessTokens` keeps resetting | Something is toggling it. Lock the setting and audit admin access. |

---

## 🛡️ Security

- **`config.yaml` contains secrets** — it's in `.gitignore`, never commit it
- PATs have your full user permissions — use a dedicated account if concerned
- Health endpoint binds to `127.0.0.1` (not exposed externally)
- Only users whose ID is in config can use the bridge
- Message mappings stored in local SQLite (30-day auto-prune)

---

## 🔌 Writing a Custom Adapter

Create a new file in `src/bridgemost/adapters/` that implements `BaseAdapter`:

```python
from bridgemost.adapters.base import BaseAdapter, InboundMessage, OutboundMessage

class MyPlatformAdapter(BaseAdapter):
    async def start(self): ...
    async def stop(self): ...
    async def send_message(self, chat_id, msg: OutboundMessage) -> int | None: ...
    async def edit_message(self, chat_id, msg_id, text): ...
    async def delete_message(self, chat_id, msg_id): ...
    async def set_reaction(self, chat_id, msg_id, emoji): ...
    async def clear_reactions(self, chat_id, msg_id): ...
    def start_typing_loop(self, chat_id): ...
    def stop_typing_loop(self, chat_id): ...
```

The core engine handles all Mattermost interaction, message tracking, retry, and health monitoring.

---

## 📋 Changelog

| Version | Date | Highlight |
|---------|------|-----------|
| v2.1.0 | 2026-03-25 | **Google Chat adapter** — Service Account ghost mode, polling, edit/delete/reactions |
| v2.0.2 | 2026-03-25 | README rewritten for multi-platform architecture |
| v2.0.1 | 2026-03-25 | Audit cleanup: platform-agnostic emoji names, encapsulation fix |
| v2.0.0 | 2026-03-25 | **Plugin adapter architecture** — Telegram extracted as adapter, core engine separated |
| v1.0.0 | 2026-03-25 | **Stable release** — PyPI, CI/CD, full test suite |
| v0.9.x | 2026-03-24/25 | Stickers, locations, polls, file relay, Docker, 71 tests |
| v0.8.x | 2026-03-24 | SQLite store, WS jitter, rate limiter, bot commands |
| v0.7.0 | 2026-03-24 | 7-bug audit, PAT health check, error alerts |
| v0.6.0 | 2026-03-24 | Interactive setup wizard |
| v0.5.0 | 2026-03-24 | Startup resilience, token validation |
| v0.4.0 | 2026-03-24 | Voice-to-text via Whisper |
| v0.3.x | 2026-03-24 | Multi-bot routing, synthetic typing |
| v0.2.0 | 2026-03-24 | Emoji/reaction relay |
| v0.1.x | 2026-03-24 | WebSocket transport, edit/delete sync |
| v0.0.5 | 2026-03-24 | First public release |

See [CHANGELOG.md](CHANGELOG.md) for full details.

---

## 📄 License

MIT — see [LICENSE](LICENSE)

## 🙏 Built with

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) (Telegram adapter)
- [aiohttp](https://github.com/aio-libs/aiohttp) (MM WebSocket + HTTP)

"""Tests for the BridgeMost /bridge command namespace."""

import asyncio
from types import SimpleNamespace

from bridgemost.adapters.telegram import TelegramAdapter


class _FakeMessage:
    def __init__(self):
        self.replies = []

    async def reply_text(self, text, parse_mode=None):
        self.replies.append({"text": text, "parse_mode": parse_mode})


def _make_update(user_id: int = 12345):
    return SimpleNamespace(effective_user=SimpleNamespace(id=user_id), effective_message=_FakeMessage())


def test_bridge_command_without_args_returns_help():
    adapter = TelegramAdapter("123:ABC")
    update = _make_update()

    async def _on_command(cmd, args, user_id):
        raise AssertionError("core command handler should not be called for bare /bridge")

    adapter._on_command = _on_command

    asyncio.run(adapter._cmd_bridge(update, SimpleNamespace(args=[])))

    assert update.effective_message.replies
    reply = update.effective_message.replies[0]
    assert "/bridge bot" in reply["text"]
    assert reply["parse_mode"] == "Markdown"


def test_bridge_status_delegates_to_core_status_command():
    adapter = TelegramAdapter("123:ABC")
    update = _make_update()
    captured = {}

    async def _on_command(cmd, args, user_id):
        captured["cmd"] = cmd
        captured["args"] = args
        captured["user_id"] = user_id
        return "estado ok"

    adapter._on_command = _on_command

    asyncio.run(adapter._cmd_bridge(update, SimpleNamespace(args=["status"])))

    assert captured == {"cmd": "status", "args": [], "user_id": 12345}
    assert update.effective_message.replies[0]["text"] == "estado ok"

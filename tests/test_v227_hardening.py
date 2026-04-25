import asyncio
import logging
from types import SimpleNamespace

import bridgemost.adapters.telegram as telegram_mod
from bridgemost.adapters.base import OutboundMessage
from bridgemost.adapters.telegram import TelegramAdapter
from bridgemost.core import should_notify_validation_failure
from bridgemost.__main__ import setup_logging
from bridgemost.telegram_presentation import (
    PendingTelegramPresentation,
    TelegramPresentationConfig,
    TelegramPresentationMixin,
)


class RecordingUpdater:
    def __init__(self):
        self.start_kwargs = None

    async def start_polling(self, *args, **kwargs):
        self.start_kwargs = kwargs

    async def stop(self):
        return None


class DummyBot:
    async def send_message(self, *args, **kwargs):
        return None


class RecordingApp:
    def __init__(self):
        self.handlers = []
        self.error_handlers = []
        self.updater = RecordingUpdater()
        self.bot = DummyBot()

    def add_handler(self, handler):
        self.handlers.append(handler)

    def add_error_handler(self, handler):
        self.error_handlers.append(handler)

    async def initialize(self):
        return None

    async def start(self):
        return None

    async def stop(self):
        return None

    async def shutdown(self):
        return None


class RecordingBuilder:
    def __init__(self):
        self.app = RecordingApp()

    def token(self, _token):
        return self

    def build(self):
        return self.app


def test_telegram_adapter_wires_configured_polling_timeout(monkeypatch):
    builder = RecordingBuilder()
    monkeypatch.setattr(telegram_mod, "ApplicationBuilder", lambda: builder)

    adapter = TelegramAdapter("123:ABC", allowed_user_ids=[63492743], polling_timeout=7)
    asyncio.run(adapter.start())
    try:
        assert builder.app.updater.start_kwargs["poll_interval"] == 0.5
        assert builder.app.updater.start_kwargs["timeout"] == 7
    finally:
        asyncio.run(adapter.stop())


def test_telegram_adapter_rejects_non_private_and_forwarded_updates():
    adapter = TelegramAdapter("123:ABC", allowed_user_ids=[63492743])
    private_update = SimpleNamespace(effective_chat=SimpleNamespace(type="private"))
    private_msg = SimpleNamespace(
        sender_chat=None,
        forward_origin=None,
        forward_from=None,
        forward_from_chat=None,
        forward_date=None,
    )
    group_update = SimpleNamespace(effective_chat=SimpleNamespace(type="group"))
    forwarded_msg = SimpleNamespace(
        sender_chat=None,
        forward_origin=object(),
        forward_from=None,
        forward_from_chat=None,
        forward_date=None,
    )

    assert adapter._is_secure_update(private_update, private_msg) is True
    assert adapter._is_secure_update(group_update, private_msg) is False
    assert adapter._is_secure_update(private_update, forwarded_msg) is False


class FailingStreamAdapter:
    def __init__(self):
        self.sent = []
        self.stream_calls = []

    async def stream_edit_message(self, user_id, platform_msg_id, new_text, chunk_size=180, interval=0.18):
        self.stream_calls.append((user_id, platform_msg_id, new_text, chunk_size, interval))
        return False

    async def edit_message(self, user_id, platform_msg_id, new_text):
        return False

    async def send_message(self, user_id, msg: OutboundMessage):
        self.sent.append((user_id, msg.text))
        return 99


class PresentationHarness(TelegramPresentationMixin):
    def __init__(self):
        self.config = SimpleNamespace(
            adapter="telegram",
            telegram_presentation=TelegramPresentationConfig(
                enabled=True,
                show_placeholder=True,
                stream_final_response=True,
                stream_chunk_chars=10,
                stream_edit_interval=0,
            ),
        )
        self.adapter = FailingStreamAdapter()
        self._presentation = {"chan": PendingTelegramPresentation(placeholder_msg_id=42)}
        self.tracked = []

    def _track_pair(self, platform_id, mm_post_id):
        self.tracked.append((platform_id, mm_post_id))


def test_placeholder_edit_failure_falls_back_to_new_message_and_tracks_new_id():
    harness = PresentationHarness()

    sent_id = asyncio.run(harness._present_visible_text("chan", 63492743, "mm-post", "final answer"))

    assert sent_id == 99
    assert harness.adapter.stream_calls
    assert harness.adapter.sent == [(63492743, "final answer")]
    assert harness.tracked == [(99, "mm-post")]


def test_validation_failure_notifications_are_debounced_for_availability_but_not_auth():
    assert should_notify_validation_failure("availability", 1) is False
    assert should_notify_validation_failure("availability", 2) is True
    assert should_notify_validation_failure("availability", 3) is False
    assert should_notify_validation_failure("availability", 8) is True
    assert should_notify_validation_failure("auth", 1) is True


def test_setup_logging_suppresses_logging_internal_tracebacks():
    logging.raiseExceptions = True
    setup_logging("INFO")
    assert logging.raiseExceptions is False


def test_setup_logging_survives_unusable_file_handler(monkeypatch):
    def raise_oserror(_path):
        raise OSError("disk full")

    monkeypatch.setattr(logging, "FileHandler", raise_oserror)

    setup_logging("INFO", "/var/log/bridgemost.log")
    assert logging.raiseExceptions is False

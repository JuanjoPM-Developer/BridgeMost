"""Backward-compatible bridge module.

Since v2.0.0, the real logic lives in core.py + adapters/.
This module provides BridgeMostBridge as a drop-in wrapper
so existing code (including __main__.py) works unchanged.
"""

from .adapters.telegram import TelegramAdapter
from .config import Config
from .core import BridgeMostCore


class BridgeMostBridge:
    """Legacy-compatible bridge class.

    Instantiates a TelegramAdapter + BridgeMostCore under the hood.
    """

    def __init__(self, config: Config):
        self.config = config
        # Create Telegram adapter with allowed user IDs
        allowed_ids = [u.telegram_id for u in config.users] if config.users else None
        self._adapter = TelegramAdapter(
            bot_token=config.tg_bot_token,
            allowed_user_ids=allowed_ids,
        )
        self._core = BridgeMostCore(config=config, adapter=self._adapter)

    async def start(self):
        """Start the bridge."""
        await self._core.start()

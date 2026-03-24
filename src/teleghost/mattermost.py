"""Mattermost API client for TeleGhost."""

import logging
import aiohttp
from pathlib import Path

logger = logging.getLogger("teleghost.mm")


class MattermostClient:
    """Async Mattermost REST API client."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self._session

    def _headers(self, token: str) -> dict:
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    async def post_message(
        self, token: str, channel_id: str, message: str, file_ids: list[str] | None = None
    ) -> dict:
        """Post a message to a channel as the token owner."""
        session = await self._get_session()
        payload: dict = {
            "channel_id": channel_id,
            "message": message,
        }
        if file_ids:
            payload["file_ids"] = file_ids

        async with session.post(
            f"{self.base_url}/api/v4/posts",
            json=payload,
            headers=self._headers(token),
        ) as resp:
            data = await resp.json()
            if resp.status not in (200, 201):
                logger.error("MM post failed (%d): %s", resp.status, data)
            else:
                logger.debug("MM post OK: %s", data.get("id"))
            return data

    async def upload_file(
        self, token: str, channel_id: str, file_path: str, filename: str
    ) -> str | None:
        """Upload a file and return the file_id."""
        session = await self._get_session()
        form = aiohttp.FormData()
        form.add_field("channel_id", channel_id)

        # FIX #1: Proper file handle management with context manager
        with open(file_path, "rb") as fh:
            form.add_field(
                "files",
                fh,
                filename=filename,
            )

            headers = {"Authorization": f"Bearer {token}"}
            async with session.post(
                f"{self.base_url}/api/v4/files",
                data=form,
                headers=headers,
            ) as resp:
                data = await resp.json()
                if resp.status in (200, 201):
                    file_infos = data.get("file_infos", [])
                    if file_infos:
                        fid = file_infos[0]["id"]
                        logger.debug("MM file uploaded: %s → %s", filename, fid)
                        return fid
                logger.error("MM upload failed (%d): %s", resp.status, data)
                return None

    async def get_dm_channel(self, token: str, user_id: str, other_id: str) -> str:
        """Get or create a DM channel between two users."""
        session = await self._get_session()
        async with session.post(
            f"{self.base_url}/api/v4/channels/direct",
            json=[user_id, other_id],
            headers=self._headers(token),
        ) as resp:
            data = await resp.json()
            return data.get("id", "")

    async def get_posts_after(
        self, token: str, channel_id: str, after_id: str
    ) -> list[dict]:
        """Get posts in a channel after a given post ID."""
        session = await self._get_session()
        params = {"after": after_id} if after_id else {"per_page": "1"}
        async with session.get(
            f"{self.base_url}/api/v4/channels/{channel_id}/posts",
            params=params,
            headers=self._headers(token),
        ) as resp:
            data = await resp.json()
            if resp.status != 200:
                logger.error("MM get_posts failed (%d): %s", resp.status, data)
                return []

            order = data.get("order", [])
            posts = data.get("posts", {})
            return [posts[pid] for pid in reversed(order) if pid in posts]

    async def download_file(self, token: str, file_id: str, dest: str) -> str:
        """Download a file from MM to local path."""
        session = await self._get_session()
        headers = {"Authorization": f"Bearer {token}"}
        async with session.get(
            f"{self.base_url}/api/v4/files/{file_id}",
            headers=headers,
        ) as resp:
            if resp.status == 200:
                with open(dest, "wb") as f:
                    f.write(await resp.read())
                return dest
            logger.error("MM download failed (%d)", resp.status)
            return ""

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

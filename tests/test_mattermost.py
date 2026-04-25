"""Tests for Mattermost client — non-network tests only."""

import asyncio
from pathlib import Path

from bridgemost.mattermost import MattermostClient


class FakeResponse:
    def __init__(self, status: int, payload: dict):
        self.status = status
        self._payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def json(self):
        return self._payload

    async def text(self):
        return str(self._payload)


class BadJsonResponse(FakeResponse):
    async def json(self):
        raise ValueError("not json")

    async def text(self):
        return "plain error body"


class FailingPostContext:
    def __init__(self, exc: BaseException):
        self.exc = exc

    async def __aenter__(self):
        raise self.exc

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakeSession:
    def __init__(self, *, get_response=None, post_response=None):
        self.get_response = get_response
        self.post_response = post_response
        self.closed = False

    def get(self, *args, **kwargs):
        return self.get_response

    def post(self, *args, **kwargs):
        return self.post_response


class TestClientInit:
    """Test MattermostClient initialization."""

    def test_base_url_normalization(self):
        client = MattermostClient("http://localhost:8065/")
        assert client.base_url == "http://localhost:8065"

    def test_base_url_no_trailing_slash(self):
        client = MattermostClient("http://localhost:8065")
        assert client.base_url == "http://localhost:8065"

    def test_headers_built(self):
        client = MattermostClient("http://localhost:8065")
        # Client should be usable without immediate errors
        assert client.base_url is not None


def test_validate_token_records_http_failure_metadata():
    client = MattermostClient("http://localhost:8065")
    client._session = FakeSession(get_response=FakeResponse(500, {"message": "backend exploded"}))

    info = asyncio.run(client.validate_token("pat-123"))

    assert info is None
    assert client.last_validate_error == {
        "kind": "http",
        "status": 500,
        "message": "backend exploded",
    }


def test_post_message_exception_returns_structured_error_instead_of_raising():
    client = MattermostClient("http://localhost:8065")
    client._session = FakeSession(post_response=FailingPostContext(TimeoutError("mattermost timeout")))

    result = asyncio.run(client.post_message("pat-123", "channel123", "hola", None))

    assert result["error_type"] == "TimeoutError"
    assert "mattermost timeout" in result["message"]


def test_post_message_non_json_error_returns_plain_body():
    client = MattermostClient("http://localhost:8065")
    client._session = FakeSession(post_response=BadJsonResponse(502, {}))

    result = asyncio.run(client.post_message("pat-123", "channel123", "hola", None))

    assert result["error_type"] == "HTTPError"
    assert result["status_code"] == 502
    assert result["message"] == "plain error body"


def test_upload_file_transport_exception_returns_none(tmp_path: Path):
    path = tmp_path / "voice.ogg"
    path.write_bytes(b"fake audio")
    client = MattermostClient("http://localhost:8065")
    client._session = FakeSession(post_response=FailingPostContext(TimeoutError("upload timeout")))

    result = asyncio.run(client.upload_file("pat-123", "channel123", str(path), "voice.ogg"))

    assert result is None

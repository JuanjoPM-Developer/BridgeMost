"""Version consistency tests."""

from pathlib import Path

from bridgemost import __version__


def test_version_is_2_2_4():
    assert __version__ == "2.2.4"


def test_changelog_mentions_2_2_4():
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")
    assert "## v2.2.4" in changelog

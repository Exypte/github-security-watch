from datetime import datetime, timezone
from pathlib import Path

from watch.changelog import merge, parse_feed

FEED = (Path(__file__).parent / "fixtures" / "changelog_feed.xml").read_bytes()
EPOCH = datetime(2000, 1, 1, tzinfo=timezone.utc)


def test_label_feed_keeps_every_entry():
    items = parse_feed(FEED, "actions", EPOCH)
    assert len(items) == 10
    assert all(i["labels"] == ["actions"] for i in items)
    assert all(i["url"].startswith("https://github.blog/changelog/") for i in items)


def test_main_feed_is_keyword_filtered():
    items = parse_feed(FEED, None, EPOCH)
    assert 0 < len(items) <= 10
    titles = [i["title"] for i in items]
    assert "Bulk migrate branch protections to rulesets for a repository" in titles


def test_since_excludes_older_entries():
    assert parse_feed(FEED, "actions", datetime(2100, 1, 1, tzinfo=timezone.utc)) == []


def test_merge_dedupes_and_combines_labels():
    a = {"url": "u", "title": "t", "published": "2026-01-01T00:00:00+00:00", "labels": ["actions"], "text": ""}
    b = dict(a, labels=["application-security"])
    c = dict(a, url="v", published="2026-02-01T00:00:00+00:00", labels=[])
    merged = merge([a, b, c])
    assert [m["url"] for m in merged] == ["v", "u"]
    assert merged[1]["labels"] == ["actions", "application-security"]

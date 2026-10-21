"""Collect GitHub Changelog entries about Actions and security."""
from __future__ import annotations

import calendar
import html
import re
from datetime import datetime, timezone

import feedparser
import httpx

# Label feeds: every entry in them is relevant.
LABEL_FEEDS = {
    "actions": "https://github.blog/changelog/label/actions/feed/",
    "application-security": "https://github.blog/changelog/label/application-security/feed/",
    "supply-chain-security": "https://github.blog/changelog/label/supply-chain-security/feed/",
}
# Main feed: only entries whose title or text matches KEYWORDS.
MAIN_FEED = "https://github.blog/changelog/feed/"

KEYWORDS = re.compile(
    r"\b(actions?|workflows?|runners?|security|code scanning|secret scanning|"
    r"push protection|dependabot|advanced security|supply chain|codeql|"
    r"attestations?|oidc|vulnerabilit(y|ies)|advisor(y|ies)|sbom|rulesets?|"
    r"2fa|two-factor|passkeys?|tokens?)\b",
    re.IGNORECASE,
)

TAG_RE = re.compile(r"<[^>]+>")


def _text(fragment: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(TAG_RE.sub(" ", fragment or ""))).strip()


def _published(entry) -> datetime | None:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if not parsed:
        return None
    return datetime.fromtimestamp(calendar.timegm(parsed), tz=timezone.utc)


def parse_feed(raw: bytes | str, label: str | None, since: datetime) -> list[dict]:
    """Return entries published after `since`. Main-feed entries (label=None) are keyword-filtered."""
    items = []
    for entry in feedparser.parse(raw).entries:
        published = _published(entry)
        if published is None or published <= since:
            continue
        content = entry.get("content", [{}])[0].get("value", "") or entry.get("summary", "")
        text = _text(content)
        if label is None and not KEYWORDS.search(f"{entry.get('title', '')} {text}"):
            continue
        items.append(
            {
                "title": entry.get("title", "").strip(),
                "url": entry.get("link", ""),
                "published": published.isoformat(),
                "labels": [label] if label else [],
                "text": text[:4000],
            }
        )
    return items


def merge(items: list[dict]) -> list[dict]:
    """Deduplicate by URL, combining labels; newest first."""
    by_url: dict[str, dict] = {}
    for item in items:
        existing = by_url.get(item["url"])
        if existing:
            existing["labels"] = sorted(set(existing["labels"]) | set(item["labels"]))
        else:
            by_url[item["url"]] = dict(item)
    return sorted(by_url.values(), key=lambda i: i["published"], reverse=True)


def collect(since: datetime, client: httpx.Client) -> list[dict]:
    items = []
    feeds = [(label, url) for label, url in LABEL_FEEDS.items()] + [(None, MAIN_FEED)]
    for label, url in feeds:
        resp = client.get(url, follow_redirects=True)
        resp.raise_for_status()
        items.extend(parse_feed(resp.content, label, since))
    return merge(items)

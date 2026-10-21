"""Nightly entry point: collect changes, summarize, write data/reports/YYYY-MM-DD.json."""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

from . import changelog, docs, summarize

DATA = Path("data")
STATE = DATA / "state.json"
REPORTS = DATA / "reports"
DEFAULT_WINDOW = timedelta(hours=24)


def window_start(now: datetime, state_path: Path = STATE) -> datetime:
    try:
        last = datetime.fromisoformat(json.loads(state_path.read_text())["last_run"])
    except (FileNotFoundError, KeyError, ValueError):
        return now - DEFAULT_WINDOW
    return min(last, now - timedelta(minutes=1))


def _client() -> httpx.Client:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "github-security-watch"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return httpx.Client(headers=headers, timeout=30)


def run(now: datetime | None = None) -> Path:
    now = now or datetime.now(timezone.utc)
    since = window_start(now)
    with _client() as client:
        entries = changelog.collect(since, client)
        doc_changes = docs.collect(since, client)

    REPORTS.mkdir(parents=True, exist_ok=True)
    path = REPORTS / f"{now.date().isoformat()}.json"
    report = {
        "date": now.date().isoformat(),
        "since": since.isoformat(),
        "summary": None,
        "note": None,
        "changelog": entries,
        "docs": doc_changes,
    }
    # A second run on the same day extends that day's report instead of replacing it.
    if path.exists():
        previous = json.loads(path.read_text())
        report["since"] = previous["since"]
        report["summary"], report["note"] = previous.get("summary"), previous.get("note")
        seen = {e["url"] for e in entries}
        report["changelog"] += [e for e in previous["changelog"] if e["url"] not in seen]
        seen = {c["sha"] for c in doc_changes}
        report["docs"] += [c for c in previous["docs"] if c["sha"] not in seen]
    report["generated_at"] = now.isoformat()

    if entries or doc_changes or (report["summary"] is None and (report["changelog"] or report["docs"])):
        report["summary"], report["note"] = summarize.summarize(report["changelog"], report["docs"])
    elif not (report["changelog"] or report["docs"]):
        report["note"] = "No changes since the last run."

    path.write_text(json.dumps(report, indent=2) + "\n")
    STATE.write_text(json.dumps({"last_run": now.isoformat()}, indent=2) + "\n")
    print(f"{path}: {len(report['changelog'])} changelog entries, {len(report['docs'])} docs commits")
    if report["note"]:
        print(report["note"])
    return path


if __name__ == "__main__":
    run()

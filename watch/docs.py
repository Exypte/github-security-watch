"""Collect changed GitHub Docs pages about Actions and security from the github/docs repo."""
from __future__ import annotations

from datetime import datetime

import httpx

REPO = "github/docs"
API = "https://api.github.com"
DOC_PATHS = ("content/actions", "content/code-security")
MAX_PATCH_CHARS = 1500
MAX_COMMITS_PER_PATH = 100


def doc_url(path: str) -> str | None:
    """Map a repo path like content/actions/x/y.md to its docs.github.com URL."""
    if not path.startswith("content/") or not path.endswith(".md"):
        return None
    slug = path[len("content/") : -len(".md")]
    if slug.endswith("/index"):
        slug = slug[: -len("/index")]
    elif slug == "index":
        slug = ""
    return f"https://docs.github.com/en/{slug}".rstrip("/")


def _relevant(path: str) -> bool:
    return any(path.startswith(p + "/") for p in DOC_PATHS)


def _list_commits(client: httpx.Client, path: str, since: datetime) -> list[dict]:
    resp = client.get(
        f"{API}/repos/{REPO}/commits",
        params={"path": path, "since": since.isoformat(), "per_page": MAX_COMMITS_PER_PATH},
    )
    resp.raise_for_status()
    return resp.json()


def summarize_commit(commit: dict) -> dict | None:
    """Reduce a commit API payload to the relevant changed docs pages."""
    files = []
    for f in commit.get("files", []):
        filename = f.get("filename", "")
        if not _relevant(filename) and not _relevant(f.get("previous_filename", "")):
            continue
        files.append(
            {
                "path": filename,
                "status": f.get("status", ""),
                "url": doc_url(filename) if f.get("status") != "removed" else None,
                "additions": f.get("additions", 0),
                "deletions": f.get("deletions", 0),
                "patch": (f.get("patch") or "")[:MAX_PATCH_CHARS],
            }
        )
    if not files:
        return None
    message = commit["commit"]["message"]
    return {
        "sha": commit["sha"],
        "title": message.split("\n", 1)[0],
        "url": commit["html_url"],
        "date": commit["commit"]["committer"]["date"],
        "files": files,
    }


def collect(since: datetime, client: httpx.Client) -> list[dict]:
    shas: dict[str, str] = {}
    for path in DOC_PATHS:
        for c in _list_commits(client, path, since):
            shas[c["sha"]] = c["commit"]["committer"]["date"]
    changes = []
    for sha in sorted(shas, key=shas.get, reverse=True):
        resp = client.get(f"{API}/repos/{REPO}/commits/{sha}")
        resp.raise_for_status()
        summary = summarize_commit(resp.json())
        if summary:
            changes.append(summary)
    return changes

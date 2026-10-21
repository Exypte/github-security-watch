"""Build the static GitHub Pages site from data/reports/*.json into _site/."""
from __future__ import annotations

import html
import json
import shutil
from datetime import datetime
from email.utils import format_datetime
from pathlib import Path

import markdown

REPORTS = Path("data/reports")
TEMPLATE = Path("templates/base.html")
OUT = Path("_site")
SITE_URL = "https://exypte.github.io/github-security-watch"

e = html.escape


def _md(text: str) -> str:
    return markdown.markdown(text, extensions=["sane_lists"])


def _fmt_date(iso: str) -> str:
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).strftime("%b %d, %Y %H:%M UTC")


def render_report(report: dict) -> str:
    parts = [
        f"<h1>Report for {e(report['date'])}</h1>",
        f"<p class='meta'>Changes since {e(_fmt_date(report['since']))} · "
        f"generated {e(_fmt_date(report['generated_at']))}</p>",
    ]
    if report.get("summary"):
        parts.append(f"<section class='summary'><h2>AI summary</h2>{_md(report['summary'])}</section>")
    if report.get("note"):
        parts.append(f"<p class='note'>{e(report['note'])}</p>")

    parts.append(f"<h2>Changelog <span class='count'>{len(report['changelog'])}</span></h2>")
    if report["changelog"]:
        parts.append("<ul class='items'>")
        for item in report["changelog"]:
            labels = "".join(f"<span class='label'>{e(l)}</span>" for l in item["labels"])
            parts.append(
                f"<li><a href='{e(item['url'])}'>{e(item['title'])}</a> {labels}"
                f"<div class='meta'>{e(_fmt_date(item['published']))}</div></li>"
            )
        parts.append("</ul>")
    else:
        parts.append("<p class='empty'>No new entries.</p>")

    parts.append(f"<h2>Docs changes <span class='count'>{len(report['docs'])}</span></h2>")
    if report["docs"]:
        parts.append("<ul class='items'>")
        for c in report["docs"]:
            files = []
            for f in c["files"]:
                name = e(f["path"].removeprefix("content/"))
                link = f"<a href='{e(f['url'])}'>{name}</a>" if f["url"] else name
                files.append(
                    f"<li>{link} <span class='status {e(f['status'])}'>{e(f['status'])}</span> "
                    f"<span class='diff'>+{f['additions']} −{f['deletions']}</span></li>"
                )
            parts.append(
                f"<li><a href='{e(c['url'])}'>{e(c['title'])}</a>"
                f"<div class='meta'>{e(_fmt_date(c['date']))}</div><ul class='files'>{''.join(files)}</ul></li>"
            )
        parts.append("</ul>")
    else:
        parts.append("<p class='empty'>No docs changes.</p>")
    return "\n".join(parts)


def render_archive(reports: list[dict], prefix: str) -> str:
    rows = "".join(
        f"<li><a href='{prefix}reports/{e(r['date'])}.html'>{e(r['date'])}</a> "
        f"<span class='meta'>{len(r['changelog'])} changelog · {len(r['docs'])} docs</span></li>"
        for r in reports
    )
    return f"<h1>Archive</h1><ul class='archive'>{rows}</ul>"


def page(template: str, title: str, body: str, prefix: str) -> str:
    return template.replace("{{title}}", e(title)).replace("{{body}}", body).replace("{{prefix}}", prefix)


def render_feed(reports: list[dict]) -> str:
    items = "".join(
        f"<item><title>GitHub security watch — {e(r['date'])}</title>"
        f"<link>{SITE_URL}/reports/{e(r['date'])}.html</link>"
        f"<guid>{SITE_URL}/reports/{e(r['date'])}.html</guid>"
        f"<pubDate>{format_datetime(datetime.fromisoformat(r['generated_at']))}</pubDate>"
        f"<description>{e(_md(r['summary']) if r.get('summary') else (r.get('note') or ''))}</description></item>"
        for r in reports[:30]
    )
    return (
        "<?xml version='1.0' encoding='UTF-8'?><rss version='2.0'><channel>"
        f"<title>GitHub security watch</title><link>{SITE_URL}/</link>"
        "<description>Nightly digest of GitHub Changelog and Docs changes about Actions and security.</description>"
        f"{items}</channel></rss>\n"
    )


def build() -> None:
    template = TEMPLATE.read_text()
    reports = sorted(
        (json.loads(p.read_text()) for p in REPORTS.glob("*.json")), key=lambda r: r["date"], reverse=True
    )
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "reports").mkdir(parents=True)

    for r in reports:
        (OUT / "reports" / f"{r['date']}.html").write_text(
            page(template, f"Report {r['date']}", render_report(r), "../")
        )
    latest = render_report(reports[0]) if reports else "<p class='empty'>No reports yet.</p>"
    (OUT / "index.html").write_text(page(template, "GitHub security watch", latest, ""))
    (OUT / "archive.html").write_text(page(template, "Archive", render_archive(reports, ""), ""))
    (OUT / "feed.xml").write_text(render_feed(reports))
    (OUT / ".nojekyll").write_text("")
    print(f"Built {OUT}/ with {len(reports)} reports")


if __name__ == "__main__":
    build()

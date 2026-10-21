# github-security-watch

Nightly digest of GitHub platform changes about **Actions** and **security**, published to
GitHub Pages: https://exypte.github.io/github-security-watch/

## What it checks

- **GitHub Changelog**: the `actions`, `application-security` and `supply-chain-security`
  label feeds, plus the main feed filtered by security/Actions keywords.
- **GitHub Docs**: commits to [`github/docs`](https://github.com/github/docs) touching
  `content/actions` and `content/code-security`, with links to the changed docs pages.
- **AI summary**: Claude (`claude-opus-5-5`) turns the raw changes into a short report:
  TL;DR, action required, security improvements, and docs changes worth reading.

## How it runs

`.github/workflows/nightly.yml` runs every day at 02:00 UTC (and on manual dispatch):

1. `python -m watch.main` collects everything since the last run (`data/state.json`)
   and writes `data/reports/YYYY-MM-DD.json`.
2. The data is committed back to `main`, so the archive grows over time.
3. `python -m watch.site` renders `_site/` (latest report, archive, RSS feed) and the
   site is deployed to GitHub Pages.

If the Claude call fails or no key is set, the report is still published, without the summary.

## Setup

- Secret `ANTHROPIC_API_KEY` on the repository.
- Pages → Source: **GitHub Actions**.

## Local development

```sh
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest -q
GITHUB_TOKEN=$(gh auth token) .venv/bin/python -m watch.main   # ANTHROPIC_API_KEY optional
.venv/bin/python -m watch.site && open _site/index.html
```

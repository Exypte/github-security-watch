import json
from pathlib import Path

from watch.docs import doc_url, summarize_commit

COMMIT = json.loads((Path(__file__).parent / "fixtures" / "docs_commit.json").read_text())


def test_doc_url_page():
    assert doc_url("content/actions/how-tos/x.md") == "https://docs.github.com/en/actions/how-tos/x"


def test_doc_url_index():
    assert doc_url("content/code-security/secret-scanning/index.md") == (
        "https://docs.github.com/en/code-security/secret-scanning"
    )


def test_doc_url_non_markdown():
    assert doc_url("content/actions/foo.yml") is None
    assert doc_url("data/reusables/x.md") is None


def test_summarize_commit_keeps_relevant_files():
    s = summarize_commit(COMMIT)
    assert s["sha"] == COMMIT["sha"]
    assert s["files"][0]["url"] == (
        "https://docs.github.com/en/actions/how-tos/manage-workflow-runs/disable-and-enable-workflows"
    )
    assert len(s["files"][0]["patch"]) <= 1500


def test_summarize_commit_ignores_other_paths():
    other = dict(COMMIT, files=[{"filename": "content/pages/x.md", "status": "modified"}])
    assert summarize_commit(other) is None

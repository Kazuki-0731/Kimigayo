"""
scripts/project-issue.py の冪等の判定のテスト

2026-10-15: Issue と非公開の Project を一緒に作る・直す仕組みにした。
何度実行しても同じ結果になること（重複して作らない・足し直さない）を、
gh を呼ばない部分で固定する。
"""

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("project_issue", ROOT / "scripts" / "project-issue.py")
pi = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pi)

pytestmark = pytest.mark.unit


def item(number=None, state="OPEN", priority=None, status=None, type="ISSUE", title=None, repo=pi.REPO,
         id=None, body=None):
    return {"id": id or f"I{number or title}", "type": type, "number": number, "state": state, "body": body,
            "repo": repo if type == "ISSUE" else None, "draft_id": "D" if type == "DRAFT_ISSUE" else None,
            "title": title, "priority": priority, "status": status}


def test_find_open_issue_matches_exact_title():
    issues = [{"number": 1, "title": "🔒 A"}, {"number": 2, "title": "🔒 A を直す"}]
    assert pi.find_open_issue(issues, "🔒 A") == 1
    assert pi.find_open_issue(issues, " 🔒 A を直す ") == 2
    assert pi.find_open_issue(issues, "🔒") is None


def test_find_draft_ignores_issues():
    items = [item(5, title="X"), item(type="DRAFT_ISSUE", title="X")]
    assert pi.find_draft(items, "X")["type"] == "DRAFT_ISSUE"
    assert pi.find_draft(items, "Y") is None


def test_sync_adds_missing_and_reports_priority():
    plan = pi.sync_plan([1, 2], [item(1, priority="High", status="未着手")])
    assert plan["add"] == [2]
    assert plan["no_priority"] == [2]
    assert plan["done"] == [] and plan["todo"] == []


def test_sync_is_idempotent_when_aligned():
    items = [item(1, priority="High", status="未着手"), item(9, state="CLOSED", priority="Low", status="完了")]
    assert pi.sync_plan([1], items) == {"add": [], "done": [], "todo": [], "no_priority": []}


def test_sync_marks_closed_done_and_fills_status():
    items = [item(1, priority="Low"), item(3, state="CLOSED", status="対応中")]
    plan = pi.sync_plan([1], items)
    assert plan["todo"] == ["I1"]
    assert plan["done"] == ["I3"]


def test_sync_ignores_drafts_and_other_repos():
    items = [item(type="DRAFT_ISSUE", title="secret"), item(1, repo="someone/else", state="CLOSED")]
    plan = pi.sync_plan([], items)
    assert plan == {"add": [], "done": [], "todo": [], "no_priority": []}


def test_duplicate_drafts_keep_oldest_with_newest_body():
    items = [
        item(type="DRAFT_ISSUE", title="X", id="a", body="old"),
        item(1, title="X"),                                   # Issue は対象外
        item(type="DRAFT_ISSUE", title="Y", id="y"),
        item(type="DRAFT_ISSUE", title=" X ", id="b", body="mid"),
        item(type="DRAFT_ISSUE", title="X", id="c", body="new"),
    ]
    (keep, extra), = pi.duplicate_drafts(items)
    assert keep["id"] == "a"
    assert [e["id"] for e in extra] == ["b", "c"]
    assert extra[-1]["body"] == "new"


def test_no_duplicates_is_noop():
    items = [item(type="DRAFT_ISSUE", title="X"), item(type="DRAFT_ISSUE", title="Y")]
    assert pi.duplicate_drafts(items) == []


@pytest.mark.parametrize("current, priority, add, remove", [
    ([], "High", ["priority: high"], []),
    (["security", "priority: high"], "High", [], []),
    (["priority: low", "bug"], "Middle", ["priority: middle"], ["priority: low"]),
    (["priority: low", "priority: high"], "High", [], ["priority: low"]),
])
def test_label_changes(current, priority, add, remove):
    assert pi.label_changes(current, priority) == (add, remove)


def test_priority_from_labels():
    assert pi.priority_from_labels(["bug", "priority: middle"]) == "Middle"
    assert pi.priority_from_labels(["bug"]) is None
    assert pi.priority_from_labels(["priority: low", "priority: high"]) is None


def lbl(*names):
    return [{"name": n} for n in names]


def test_label_plan_follows_project_priority():
    issues = [{"number": 1, "labels": lbl("security")},
              {"number": 2, "labels": lbl("priority: high")},
              {"number": 3, "labels": lbl("priority: low")}]
    items = [item(1, priority="High"), item(2, priority="High"), item(3, priority="Middle")]
    plan = pi.label_plan(issues, items)
    assert plan["labels"] == [(1, ["priority: high"], []), (3, ["priority: middle"], ["priority: low"])]
    assert plan["adopt"] == []


def test_label_plan_adopts_label_when_project_has_none():
    issues = [{"number": 4, "labels": lbl("priority: middle")}, {"number": 5, "labels": []}]
    items = [item(4)]                       # #5 は Project にまだ無い
    plan = pi.label_plan(issues, items)
    assert plan["adopt"] == [(4, "Middle")]
    assert plan["labels"] == []


def test_label_plan_is_idempotent():
    issues = [{"number": 1, "labels": lbl("priority: low")}]
    assert pi.label_plan(issues, [item(1, priority="Low")]) == {"labels": [], "adopt": []}

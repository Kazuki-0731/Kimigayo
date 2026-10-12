"""
.claude/hooks/memo-paths.py（メモ扱いのパスの判定）の回帰テスト

2026-10-13: memo-paths.py 自身が接頭辞の規則（memo-）に一致して
メモ扱いになり、編集・コミットを guard-memo-files.sh に止められていた。
"""

import importlib.util
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / ".claude" / "hooks" / "memo-paths.py"


def _load():
    spec = importlib.util.spec_from_file_location("memo_paths", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


memo_paths = _load()

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("path", [
    "TODO.md", "NEXT.md", "todo", "next.txt",
    ".claude/question.md", ".claude/error.md", "./.claude/anything.md",
    "MEMO.md", "memo-2026.md", "MEMO_x.txt", "memo-1",
    "notes.md", "notes-2026.md", "NOTES_2026.txt",
    "scratch.md", "wip.md", "draft-plan.md", "ideas.md", "IDEA-1.md",
    "docs/x-memo.md", "plan_draft.txt",
    ".claude/settings.local.json", "config.local.yaml",
])
def test_memo_names_are_caught(path):
    assert memo_paths.is_memo_path(path)


@pytest.mark.parametrize("path", [
    ".claude/hooks/memo-paths.py",       # このファイル自身
    "memo-paths.py", "scripts/memo.sh", "todo_parser.py", "next-step.sh",
    "RELEASE_NOTES.md", "docs/RELEASE_NOTES.md",
    "src/benchmark/memory_benchmark.py", "scripts/benchmark-memory.sh",
    "memory.py", ".claude/settings.json", ".claude/agents/foo.md",
    ".claude/skills/release/SKILL.md", "README.md",
])
def test_non_memo_names_pass(path):
    assert not memo_paths.is_memo_path(path)


def test_no_tracked_file_is_classified_as_memo():
    """CLAUDE.md の手順: git ls-files | memo-paths.py が何も出さないこと"""
    files = subprocess.run(["git", "-c", "safe.directory=*", "-C", str(ROOT), "ls-files"],
                           capture_output=True, text=True, check=True).stdout
    hits = [p for p in files.splitlines() if p and memo_paths.is_memo_path(p)]
    assert hits == []

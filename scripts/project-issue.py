#!/usr/bin/env python3
"""Issue と非公開の Project（Kimigayo Security）を、いつも一緒に作る・直す。

Issue だけ作って Project に入れ忘れる、Project と Issue のラベルで優先度が
食い違う、を手順ではなくこのスクリプトで防ぐ（2026-10-15 に決定）。
優先度の正本は Project の Priority で、Issue には同じ値のラベル
（priority: high / middle / low）を付ける。
何度実行しても同じ結果になる（冪等）:

  - 同じタイトルの開いている Issue があれば、作らずにそれを直す
  - Project に既にある Issue は足し直さない（項目の値だけ合わせる）
  - 同じタイトルの下書きがあれば、作らずに本文を差し替える

Project の一覧への反映は数分遅れる（2026-10-15 に実測、5 分以上かかることもある）。
その間に同じ下書きをもう一度作ると重複するので、sync が同じタイトルの下書きを
1 件にまとめる（いちばん古い項目に最新の本文を移し、残りを消す）。

使い方:
  # 公開の Issue を作る（または直す）。Project に入れて Priority / Status を付ける
  python3 scripts/project-issue.py issue --title "..." --body-file body.md \\
      --label security --priority Middle

  # セキュリティに関するものは Issue にせず、Project の下書きにする
  # （CLAUDE.md「セキュリティに関するものは Issue にしない」節）
  python3 scripts/project-issue.py draft --title "..." --body-file body.md --priority High

  # 既存の Issue の優先度・状態を変える
  python3 scripts/project-issue.py set 122 --priority High --status 対応中

  # 全部をそろえる: 開いている Issue を Project に入れ、閉じた Issue を Done にし、
  # Issue の優先度のラベルを Project の Priority に合わせる。Priority が無く
  # ラベルだけある Issue は、ラベルを Project に写す。どちらも無い Issue を一覧にする
  # （on-issue-sync-private-project.yml が Issue の変化のたびに回す）
  python3 scripts/project-issue.py sync

Project を書き換えるので、gh のトークンに project スコープが要る。
手元の gh が環境変数 GITHUB_TOKEN（project スコープ無し）を使っているときは
`env -u GITHUB_TOKEN python3 scripts/project-issue.py ...` で、キーチェーンの
ログインを使わせる（docs/maintainer/ACCOUNT_SECURITY.md）。
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

OWNER = "Kazuki-0731"
REPO = "Kazuki-0731/Kimigayo"
PROJECT_NUMBER = 3          # https://github.com/users/Kazuki-0731/projects/3
PRIORITIES = ("High", "Middle", "Low")
# Issue に付ける優先度のラベル（Project の Priority と同じ値）
PRIORITY_LABELS = {p: f"priority: {p.lower()}" for p in PRIORITIES}
LABEL_COLORS = {"High": ("d73a4a", "優先度: 高（先に着手する）"),
                "Middle": ("fbca04", "優先度: 中"),
                "Low": ("f9a03f", "優先度: 低（手が空いたら）")}
# Status は Project 側と同じ日本語。「リリース待ち」= 修正は main に入り、
# 次のリリース（公開）を待っている状態（対応中＝修正中と区別。2026-10-16）。
STATUSES = ("未着手", "対応中", "リリース待ち", "完了")


# ---------------------------------------------------------------------------
# gh
# ---------------------------------------------------------------------------

def gh(*args: str, input: str | None = None, issues: bool = False) -> str:
    """issues=True は Issue とラベルの書き換え。CI では Project 用のトークン
    （project スコープだけ）では書けないので、KIMIGAYO_ISSUES_TOKEN があればそれを使う。"""
    env = None
    if issues and os.environ.get("KIMIGAYO_ISSUES_TOKEN"):
        env = {**os.environ, "GH_TOKEN": os.environ["KIMIGAYO_ISSUES_TOKEN"]}
    r = subprocess.run(["gh", *args], capture_output=True, text=True, input=input, env=env)
    if r.returncode != 0:
        msg = r.stderr.strip()
        if "INSUFFICIENT_SCOPES" in msg or "missing required scopes" in msg:
            msg += ("\n→ gh のトークンに project スコープが無い。"
                    "`env -u GITHUB_TOKEN python3 scripts/project-issue.py ...` で試す")
        raise SystemExit(f"gh {' '.join(args[:2])} が失敗した:\n{msg}")
    return r.stdout


def graphql(query: str, **variables) -> dict:
    args = ["api", "graphql", "-f", f"query={query}"]
    for k, v in variables.items():
        args += ["-F" if isinstance(v, int) else "-f", f"{k}={v}"]
    return json.loads(gh(*args))["data"]


# ---------------------------------------------------------------------------
# Project
# ---------------------------------------------------------------------------

class Project:
    """Project の ID・単一選択の項目（Priority / Status）を名前で引く。"""

    def __init__(self, data: dict):
        self.id = data["id"]
        self.url = data["url"]
        self.fields = {}
        for f in data["fields"]["nodes"]:
            if f and "options" in f:
                self.fields[f["name"]] = (f["id"], {o["name"]: o["id"] for o in f["options"]})

    @classmethod
    def load(cls) -> "Project":
        d = graphql("""
          query($owner: String!, $n: Int!) {
            user(login: $owner) { projectV2(number: $n) {
              id url
              fields(first: 50) { nodes { ... on ProjectV2SingleSelectField { id name options { id name } } } }
            } }
          }""", owner=OWNER, n=PROJECT_NUMBER)
        return cls(d["user"]["projectV2"])

    def option(self, field: str, name: str) -> tuple[str, str]:
        if field not in self.fields:
            raise SystemExit(f"Project に項目 {field} が無い")
        fid, options = self.fields[field]
        if name not in options:
            raise SystemExit(f"{field} に {name} が無い（あるのは {', '.join(options)}）")
        return fid, options[name]

    def set(self, item: str, field: str, name: str | None) -> None:
        if not name:
            return
        fid, oid = self.option(field, name)
        graphql("""
          mutation($p: ID!, $i: ID!, $f: ID!, $o: String!) {
            updateProjectV2ItemFieldValue(input: {projectId: $p, itemId: $i, fieldId: $f,
              value: {singleSelectOptionId: $o}}) { projectV2Item { id } }
          }""", p=self.id, i=item, f=fid, o=oid)

    def items(self) -> list[dict]:
        """全項目: {id, type, number, state, title, priority, status}"""
        out, after = [], None
        while True:
            d = graphql("""
              query($p: ID!, $after: String) { node(id: $p) { ... on ProjectV2 {
                items(first: 100, after: $after) {
                  pageInfo { hasNextPage endCursor }
                  nodes {
                    id type
                    content {
                      ... on Issue { number state title repository { nameWithOwner } }
                      ... on DraftIssue { id title body }
                    }
                    priority: fieldValueByName(name: "Priority") { ... on ProjectV2ItemFieldSingleSelectValue { name } }
                    status: fieldValueByName(name: "Status") { ... on ProjectV2ItemFieldSingleSelectValue { name } }
                  }
                } } } }""", p=self.id, **({"after": after} if after else {}))
            page = d["node"]["items"]
            for n in page["nodes"]:
                c = n["content"] or {}
                out.append({
                    "id": n["id"], "type": n["type"],
                    "number": c.get("number"), "state": c.get("state"),
                    "repo": (c.get("repository") or {}).get("nameWithOwner"),
                    "draft_id": c.get("id") if n["type"] == "DRAFT_ISSUE" else None,
                    "title": c.get("title"),
                    "body": c.get("body") if n["type"] == "DRAFT_ISSUE" else None,
                    "priority": (n["priority"] or {}).get("name"),
                    "status": (n["status"] or {}).get("name"),
                })
            if not page["pageInfo"]["hasNextPage"]:
                return out
            after = page["pageInfo"]["endCursor"]

    def add_issue(self, number: int) -> str:
        """Issue を Project に入れて項目の ID を返す。既に入っていれば同じ ID が返る。"""
        node = graphql("""
          query($owner: String!, $name: String!, $n: Int!) {
            repository(owner: $owner, name: $name) { issue(number: $n) { id } }
          }""", owner=REPO.split("/")[0], name=REPO.split("/")[1], n=number)
        issue_id = node["repository"]["issue"]["id"]
        d = graphql("""
          mutation($p: ID!, $c: ID!) {
            addProjectV2ItemById(input: {projectId: $p, contentId: $c}) { item { id } }
          }""", p=self.id, c=issue_id)
        return d["addProjectV2ItemById"]["item"]["id"]


# ---------------------------------------------------------------------------
# 冪等の判定（テストしやすいよう gh から切り離す）
# ---------------------------------------------------------------------------

def find_open_issue(issues: list[dict], title: str) -> int | None:
    """同じタイトルの開いている Issue の番号。前後の空白だけは無視する。"""
    for i in issues:
        if i["title"].strip() == title.strip():
            return i["number"]
    return None


def find_draft(items: list[dict], title: str) -> dict | None:
    for i in items:
        if i["type"] == "DRAFT_ISSUE" and (i["title"] or "").strip() == title.strip():
            return i
    return None


def duplicate_drafts(items: list[dict]) -> list[tuple[dict, list[dict]]]:
    """同じタイトルの下書きの組。(残す項目 = いちばん古い, 消す項目)。

    一覧は作った順に並ぶ。残す項目には、消すうちいちばん新しいものの本文を移す
    （反映待ちの間に差し替えた本文が新しい方に入っているため）。"""
    groups: dict[str, list[dict]] = {}
    for i in items:
        if i["type"] == "DRAFT_ISSUE":
            groups.setdefault((i["title"] or "").strip(), []).append(i)
    return [(g[0], g[1:]) for g in groups.values() if len(g) > 1]


def sync_plan(open_issues: list[int], items: list[dict]) -> dict:
    """そろえるために何をするか。open: 足す番号、done: Done にする項目、todo: Todo にする項目、
    no_priority: Priority の無い開いている Issue の番号。"""
    ours = {i["number"]: i for i in items if i["type"] == "ISSUE" and i["repo"] == REPO}
    plan = {"add": [], "done": [], "todo": [], "no_priority": []}
    for n in open_issues:
        item = ours.get(n)
        if item is None:
            plan["add"].append(n)
            plan["no_priority"].append(n)
            continue
        if not item["status"]:
            plan["todo"].append(item["id"])
        if not item["priority"]:
            plan["no_priority"].append(n)
    for n, item in ours.items():
        if item["state"] == "CLOSED" and item["status"] != "完了":
            plan["done"].append(item["id"])
    return plan


def label_changes(current: list[str], priority: str) -> tuple[list[str], list[str]]:
    """Issue のラベルを Priority に合わせるための (足す, 外す)。"""
    want = PRIORITY_LABELS[priority]
    add = [] if want in current else [want]
    remove = [l for l in current if l in PRIORITY_LABELS.values() and l != want]
    return add, remove


def priority_from_labels(current: list[str]) -> str | None:
    """優先度のラベルがちょうど 1 つならその Priority。無い・複数なら None。"""
    found = [p for p, l in PRIORITY_LABELS.items() if l in current]
    return found[0] if len(found) == 1 else None


def label_plan(issues: list[dict], items: list[dict]) -> dict:
    """labels: [(番号, 足す, 外す)]、adopt: [(番号, Priority)]（ラベルを Project に写す）。
    Project の Priority が正本。Priority が無いときだけラベルを採る。"""
    ours = {i["number"]: i for i in items if i["type"] == "ISSUE" and i["repo"] == REPO}
    plan = {"labels": [], "adopt": []}
    for issue in issues:
        current = [l["name"] for l in issue.get("labels", [])]
        item = ours.get(issue["number"])
        priority = item and item["priority"]
        if not priority:
            from_label = priority_from_labels(current)
            if from_label:
                plan["adopt"].append((issue["number"], from_label))
            continue
        add, remove = label_changes(current, priority)
        if add or remove:
            plan["labels"].append((issue["number"], add, remove))
    return plan


# ---------------------------------------------------------------------------
# サブコマンド
# ---------------------------------------------------------------------------

def open_issues() -> list[dict]:
    return json.loads(gh("issue", "list", "--repo", REPO, "--state", "open",
                         "--limit", "1000", "--json", "number,title,labels"))


def ensure_labels() -> None:
    """優先度のラベルを作る（あれば色と説明をそろえる。何度呼んでも同じ）。"""
    for p, name in PRIORITY_LABELS.items():
        color, desc = LABEL_COLORS[p]
        gh("label", "create", name, "--repo", REPO, "--color", color,
           "--description", desc, "--force", issues=True)


def apply_priority_label(number: int, current: list[str], priority: str) -> bool:
    add, remove = label_changes(current, priority)
    if not add and not remove:
        return False
    args = ["issue", "edit", str(number), "--repo", REPO]
    for l in add:
        args += ["--add-label", l]
    for l in remove:
        args += ["--remove-label", l]
    gh(*args, issues=True)
    return True


def issue_labels(number: int) -> list[str]:
    d = json.loads(gh("issue", "view", str(number), "--repo", REPO, "--json", "labels"))
    return [l["name"] for l in d["labels"]]


def cmd_issue(a) -> None:
    project = Project.load()
    # 値は先に確かめる（Issue だけできて Project で止まる、を避ける）
    project.option("Priority", a.priority)
    if a.status:
        project.option("Status", a.status)
    body = open(a.body_file, encoding="utf-8").read() if a.body_file else None

    number = find_open_issue(open_issues(), a.title)
    created = number is None
    if created:
        if body is None:
            raise SystemExit("新しく作るときは --body-file が要る")
        args = ["issue", "create", "--repo", REPO, "--title", a.title, "--body-file", a.body_file]
        for l in a.label:
            args += ["--label", l]
        number = int(gh(*args).strip().rsplit("/", 1)[-1])
        print(f"作成: #{number} {a.title}")
    else:
        changes = []
        if body is not None:
            changes += ["--body-file", a.body_file]
        for l in a.label:
            changes += ["--add-label", l]
        if changes:
            gh("issue", "edit", str(number), "--repo", REPO, *changes)
        print(f"既存: #{number} {a.title}（作らずに直した）")

    item = project.add_issue(number)
    project.set(item, "Priority", a.priority)
    ensure_labels()
    apply_priority_label(number, issue_labels(number), a.priority)
    # 既存の Issue の Status は、指定されたときだけ変える（In Progress を Todo に戻さない）
    status = a.status or ("未着手" if created else None)
    project.set(item, "Status", status)
    print(f"Project: Priority={a.priority}" + (f" Status={status}" if status else "") + f"  {project.url}")


def cmd_draft(a) -> None:
    project = Project.load()
    project.option("Priority", a.priority)
    body = open(a.body_file, encoding="utf-8").read()
    found = find_draft(project.items(), a.title)
    if found:
        graphql("""
          mutation($d: ID!, $t: String!, $b: String!) {
            updateProjectV2DraftIssue(input: {draftIssueId: $d, title: $t, body: $b}) { draftIssue { id } }
          }""", d=found["draft_id"], t=a.title, b=body)
        item = found["id"]
        print(f"既存の下書きを差し替えた: {a.title}")
    else:
        d = graphql("""
          mutation($p: ID!, $t: String!, $b: String!) {
            addProjectV2DraftIssue(input: {projectId: $p, title: $t, body: $b}) { projectItem { id } }
          }""", p=project.id, t=a.title, b=body)
        item = d["addProjectV2DraftIssue"]["projectItem"]["id"]
        print(f"下書きを作った: {a.title}")
    project.set(item, "Priority", a.priority)
    project.set(item, "Status", a.status or ("未着手" if not found else None))
    print(f"Project: {project.url}")


def cmd_set(a) -> None:
    if not a.priority and not a.status:
        raise SystemExit("--priority か --status を指定する")
    project = Project.load()
    item = project.add_issue(a.number)
    project.set(item, "Priority", a.priority)
    project.set(item, "Status", a.status)
    if a.priority:
        ensure_labels()
        apply_priority_label(a.number, issue_labels(a.number), a.priority)
    print(f"#{a.number}: " + " ".join(f"{k}={v}" for k, v in
                                       (("Priority", a.priority), ("Status", a.status)) if v))


def cmd_sync(a) -> int:
    project = Project.load()
    items = project.items()
    for keep, extra in duplicate_drafts(items):
        graphql("""
          mutation($d: ID!, $b: String!) {
            updateProjectV2DraftIssue(input: {draftIssueId: $d, body: $b}) { draftIssue { id } }
          }""", d=keep["draft_id"], b=extra[-1]["body"] or "")
        for e in extra:
            graphql("""
              mutation($p: ID!, $i: ID!) { deleteProjectV2Item(input: {projectId: $p, itemId: $i}) { deletedItemId } }
            """, p=project.id, i=e["id"])
        print(f"重複した下書きをまとめた: {keep['title']}（{len(extra)} 件を消した）")
    issues = open_issues()
    plan = sync_plan([i["number"] for i in issues], items)
    for n in plan["add"]:
        item = project.add_issue(n)
        project.set(item, "Status", "未着手")
        print(f"Project に足した: #{n}")
    for item in plan["todo"]:
        project.set(item, "Status", "未着手")
    for item in plan["done"]:
        project.set(item, "Status", "完了")
    if plan["todo"] or plan["done"]:
        print(f"Status をそろえた: Todo {len(plan['todo'])} 件 / Done {len(plan['done'])} 件")

    # 優先度: Project の Priority を正本にして Issue のラベルを合わせる。
    # Priority が無くラベルだけある Issue（Web でラベルを付けた）は、ラベルを Project に写す
    lp = label_plan(issues, items)
    if lp["labels"] or lp["adopt"]:
        ensure_labels()
    for n, p in lp["adopt"]:
        project.set(project.add_issue(n), "Priority", p)
        print(f"#{n}: ラベルの優先度 {p} を Project に写した")
    for n, add, remove in lp["labels"]:
        gh("issue", "edit", str(n), "--repo", REPO,
           *sum((["--add-label", l] for l in add), []),
           *sum((["--remove-label", l] for l in remove), []), issues=True)
        print(f"#{n}: 優先度のラベルを Project に合わせた（+{','.join(add) or '-'} -{','.join(remove) or '-'}）")
    adopted = {n for n, _ in lp["adopt"]}
    plan["no_priority"] = [n for n in plan["no_priority"] if n not in adopted]
    if plan["no_priority"]:
        nums = " ".join(f"#{n}" for n in plan["no_priority"])
        print(f"Priority が無い Issue: {nums}")
        print("  → python3 scripts/project-issue.py set <番号> --priority High|Middle|Low")
        return 1 if a.strict else 0
    print("そろっている")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("issue", help="公開の Issue を作る（または直す）と同時に Project に入れる")
    s.add_argument("--title", required=True)
    s.add_argument("--body-file")
    s.add_argument("--label", action="append", default=[])
    s.add_argument("--priority", required=True, choices=PRIORITIES)
    s.add_argument("--status", choices=STATUSES)

    s = sub.add_parser("draft", help="Issue にせず Project の下書きにする（セキュリティに関するもの）")
    s.add_argument("--title", required=True)
    s.add_argument("--body-file", required=True)
    s.add_argument("--priority", required=True, choices=PRIORITIES)
    s.add_argument("--status", choices=STATUSES)

    s = sub.add_parser("set", help="Issue の Priority / Status を変える（Project に無ければ入れる）")
    s.add_argument("number", type=int)
    s.add_argument("--priority", choices=PRIORITIES)
    s.add_argument("--status", choices=STATUSES)

    s = sub.add_parser("sync", help="開いている Issue を Project に入れ、閉じた Issue を Done にする")
    s.add_argument("--strict", action="store_true", help="Priority の無い Issue があれば終了コード 1")

    a = p.parse_args(argv)
    if a.cmd == "issue":
        cmd_issue(a)
    elif a.cmd == "draft":
        cmd_draft(a)
    elif a.cmd == "set":
        cmd_set(a)
    else:
        return cmd_sync(a)
    return 0


if __name__ == "__main__":
    sys.exit(main())

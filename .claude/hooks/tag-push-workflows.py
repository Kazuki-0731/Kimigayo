#!/usr/bin/env python3
"""タグを push したときに起動するワークフローを、**そのタグのコミット時点**で列挙する。

なぜこれが必要か（2026-10-09 に実際に事故った）:
  タグ push で走るワークフローは、いまの main にあるものではなく
  **そのタグが指すコミットの .github/workflows/** で決まる。

  release.yml を `gh workflow disable` で止めて v0.1.1 を push したが、
  v0.1.1 のコミット（2025-12-22）には当時の別ワークフロー
  "Docker Build and Push" があり、それが走って
  **Docker Hub の latest を含む公開イメージが差し替わった。**
  いまの main にそのファイルは無いので `gh workflow list` にも出ず、
  現在のワークフロー一覧を見るだけでは気づけなかった。

  `gh workflow disable` はワークフロー ID 単位なので、古いコミットに
  しか無いワークフローは止められない（そもそも ID が存在しない）。

使い方:
  python3 tag-push-workflows.py v0.1.1 v1.0.0 ...
  -> タグごとに、push で起動するワークフローと一致したパターンを出す
  -> 1件でも見つかれば終了コード 1
"""
import re
import subprocess
import sys

try:
    import yaml
except ImportError:
    yaml = None


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True)


def workflow_files(ref):
    r = git("ls-tree", "-r", "--name-only", ref, ".github/workflows/")
    if r.returncode != 0:
        return []
    return [p for p in r.stdout.split("\n") if p.endswith((".yml", ".yaml"))]


def tag_patterns(text):
    """on.push.tags のパターン一覧を返す。tags 指定が無ければ None。"""
    if yaml is not None:
        try:
            d = yaml.safe_load(text)
        except Exception:
            d = None
        if isinstance(d, dict):
            # YAML 1.1 では `on:` が真偽値 True に化ける
            on = d.get("on", d.get(True))
            if isinstance(on, dict) and isinstance(on.get("push"), dict):
                tags = on["push"].get("tags") or on["push"].get("tags-ignore")
                if tags:
                    return [str(t) for t in (tags if isinstance(tags, list) else [tags])]
            return None
    # PyYAML が無い環境では行ベースで拾う（取りこぼすより出しすぎる側に倒す）
    if re.search(r"^\s*tags:", text, re.M):
        return ["(tags: 指定あり。PyYAML が無いのでパターン未解析)"]
    return None


def name_of(text, path):
    m = re.search(r"^name:\s*(.+)$", text, re.M)
    return m.group(1).strip().strip("'\"") if m else path


def matches(pattern, tag):
    """GitHub のタグパターン（* と ** のグロブ）をざっくり判定する。"""
    p = re.escape(pattern).replace(r"\*\*", ".*").replace(r"\*", "[^/]*")
    return re.fullmatch(p, tag) is not None


def main() -> int:
    tags = sys.argv[1:]
    if not tags:
        print("使い方: tag-push-workflows.py <tag> [<tag>...]", file=sys.stderr)
        return 2

    found_any = False
    for tag in tags:
        short = tag.replace("refs/tags/", "")
        if git("rev-parse", "--verify", "--quiet", short + "^{commit}").returncode != 0:
            print("  %s: ローカルに存在しないタグ（確認できない）" % short)
            continue

        commit = git("rev-list", "-n1", short).stdout.strip()[:10]
        date = git("log", "-1", "--format=%ad", "--date=short", short).stdout.strip()
        hits = []
        for path in workflow_files(short):
            text = git("show", "%s:%s" % (short, path)).stdout
            pats = tag_patterns(text)
            if pats is None:
                continue
            hit = [p for p in pats if matches(p, short)] or \
                  (pats if any("指定あり" in p for p in pats) else [])
            if hit:
                hits.append((name_of(text, path), path, hit))

        print("  %s (%s, %s)" % (short, commit, date))
        if not hits:
            print("      タグ push で起動するワークフローなし")
            continue
        found_any = True
        for wf_name, path, pats in hits:
            print("      ★ %s" % wf_name)
            print("          %s  パターン: %s" % (path, ", ".join(pats)))

    return 1 if found_any else 0


if __name__ == "__main__":
    sys.exit(main())

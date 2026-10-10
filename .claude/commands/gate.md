---
description: 外に出す前の品質ゲートを回す（pytest / shellcheck / YAML / 作業ツリー / 文書の突合）
allowed-tools: Bash(python3 -m pytest:*), Bash(make shellcheck-scan), Bash(python3 -I -c:*), Bash(git status:*), Bash(git ls-files:*), Bash(git diff:*), Bash(ls:*), Bash(for:*), Bash(do:*), Bash(done), Task
---

ローカルで変更したものを外に出す前の最低ラインを確認する。

## pytest（522 件）

!`python3 -m pytest tests/unit tests/property -q 2>&1 | tail -15`

## ShellCheck（scripts/ と .claude/hooks/）

!`make shellcheck-scan 2>&1 | tail -10`

## ワークフローとプロジェクト設定の YAML / JSON が壊れていないか

!`python3 -I -c "
import glob, json, sys
try:
    import yaml
except ImportError:
    print('(PyYAML が無いので YAML は未検査)'); yaml = None
bad = 0
if yaml:
    for f in sorted(glob.glob('.github/workflows/*.yml')) + ['docker-compose.yml']:
        try:
            yaml.safe_load(open(f, encoding='utf-8')); print('OK  ' + f)
        except Exception as e:
            print('NG  ' + f + ': ' + str(e)); bad += 1
for f in sorted(glob.glob('.claude/*.json')):
    try:
        json.load(open(f, encoding='utf-8')); print('OK  ' + f)
    except Exception as e:
        print('NG  ' + f + ': ' + str(e)); bad += 1
sys.exit(1 if bad else 0)
"`

## 作業ツリー

!`git status --short; echo '--- 未追跡 ---'; git ls-files --others --exclude-standard | head -20`

## まだ push していない変更が、どのファイルに入っているか

!`git diff --name-only origin/main...HEAD 2>/dev/null; echo '--- 未コミット ---'; git diff --name-only HEAD 2>/dev/null`

---

結果を**合格/不合格だけ**で短く報告してください。

- 落ちたものがあれば、何が落ちたかと出力の該当部分を示す。
  **勝手に直さないこと**（自分が今回のセッションで壊したものは除く）
- 未追跡ファイルがあれば、コミットするか `.gitignore` に入れるかを
  その場で決めるよう促す
- **`make ci-build-local` と `make security-scan` はここに含めていません**
  （前者は macOS で通らず、後者は Trivy のダウンロードが走るため）。
  必要なら別に回すことを伝える

**落ちたテストを `|| true` や `-Wno-error` で通すのは「直した」では
ありません。** そういう提案はしないこと。

---

## 最後に: 文書と実態の突合

**上のチェックは「壊れていないか」しか見ていません。**
数値やバージョンが**実態と食い違っていても全部通ります。**

> 2026-10-10 の実例: README が「Docker Hub 上のイメージは v2.0.1 のまま」と
> 書いたまま v3.0.0 を公開していた。`pytest` も `shellcheck` も
> `check-links` も通る。読んだ人だけが騙される。

変更に次のどれかが含まれていたら、**`docs-reconciler` subagent を起動して
突合させてください**（Task ツール、`subagent_type: docs-reconciler`）。

| 含まれていたら起動する | 理由 |
| --- | --- |
| `*.md`（README・docs・CHANGELOG・RELEASE_NOTES） | 数値・版・リンクが実態とずれる |
| `versions.mk` / `scripts/build-*.sh` | 版の表記が各所に散る |
| `scripts/benchmark-*.sh` / 計測の実施 | 数値の着地先がずれる |
| リリース直後 | 公開状態を書いた記述が古くなる |

渡すプロンプトの例:

```
今回の変更は <変更したファイル> です。
README・docs・CHANGELOG・RELEASE_NOTES に書かれた数値・バージョン・
公開状態が実態と合っているか突合してください。
直さず、食い違いだけ報告してください。
```

**該当しなければ起動しません**（毎回起動すると `/gate` が重くなります）。
起動しなかった場合は「文書に関わる変更が無いので突合は省略した」と
一行で報告してください。

> `.github/workflows/` を触ったときは `workflow-auditor`、
> `SPECIFICATION.md` を触ったときは `spec-auditor` も同じ要領で使えます。

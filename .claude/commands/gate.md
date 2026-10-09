---
description: 外に出す前の品質ゲートを回す（pytest / shellcheck / YAML / 作業ツリー）
allowed-tools: Bash(python3 -m pytest:*), Bash(make shellcheck-scan), Bash(python3 -I -c:*), Bash(git status:*), Bash(git ls-files:*), Bash(ls:*), Bash(for:*), Bash(do:*), Bash(done)
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

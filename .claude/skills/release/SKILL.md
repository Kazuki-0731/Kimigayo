---
name: release
description: リリースの準備と実行。タグを打つ前に揃えるもの、成果物の検査、承認の取り方、タグ後に起きること。リリースしたい、タグを打ちたい、Docker Hub に出したいときに使う。
---

# リリース

**`git tag v*.*.*` を push した瞬間に `.github/workflows/release.yml` が走り、
Docker Hub の公開イメージ（`latest` を含む）が差し替わります。**

**タグ・push・リリースは毎回ユーザーの明示的な承認を取ります**
（CLAUDE.md「指示の範囲を超えない > 実行・運用・リリース」節）。
このスキルは**準備を整えて承認を求めるところまで**を担います。
承認なしでタグを打たないこと。`.claude/hooks/guard-bash.sh` がブロックします。

---

## 0. 出せる状態か確認する

**過去に「出してはいけないものを出した」実績があります。**
v0.1.0 から v2.0.1 までの**公開済み4タグすべて**で次が同時に起きていました。

- OpenRC のバイナリが1つも入っていない（**売りである Init が無い**）
- musl の `libc.so` が無く `/lib/ld-musl-*.so.1` がリンク切れ
- `/tmp`・`/run`・`/var/log` などが無い
- それでも smoke テストは通っていた

**だからリリース前の検査は「イメージが起動するか」では足りません。**
`rootfs-verifier` subagent に**両アーキテクチャ・全バリアント**を検査させます。

---

## 1. 品質ゲート

```bash
python3 -m pytest tests/unit tests/property -q     # 522 件
make shellcheck-scan                               # scripts/ と .claude/hooks/
make security-scan                                 # Trivy + ShellCheck
make ci-build-local                                # Linux ホストのみ
```

macOS では `make ci-build-local` が通りません（musl の `configure` が
`unsupported long double type` で落ちる）。CI の結果で代替します。

**CI を見ます。** `ci.yml` は 3 バリアント × 2 アーキテクチャの 6 ジョブ。
`fail-fast: false` なので、1つ落ちても他が走ります
（以前は `fail-fast` が兄弟ジョブを**キャンセル**して真の失敗を隠していました）。

```bash
gh run list --limit 5
gh run view <id>
```

---

## 2. 成果物を検査する

`rootfs-verifier` subagent に投げる。最低限、人が見るべきもの:

```bash
# 両アーキテクチャで実際に実行する
for a in amd64 arm64; do
  echo "=== $a ==="
  docker run --rm --platform "linux/$a" kimigayo-os:standard-${a/amd64/x86_64} /bin/sh -c '
    echo "arch: $(uname -m)"
    echo "applets: $(busybox --list | wc -l)"
    ls -ld /tmp /run /var/tmp
    for b in openrc openrc-run rc-update start-stop-daemon; do
      printf "%-20s %s\n" "$b" "$(/sbin/$b --version 2>&1 | head -1)"
    done'
done
```

**`Error relocating ...: symbol not found` が出たら出せません。**
片方のアーキテクチャで通っても、もう片方を必ず確かめます。

---

## 3. 記録を揃える（タグを打つ前に）

**2026-10-09 まで `CHANGELOG.md` が 0.1.0 止まりで、v2.0.1 までの
2回のリリースが抜けていました。**

| ファイル | 何を書くか |
| --- | --- |
| `CHANGELOG.md` | `[Unreleased]` を新しい版見出しに移す。`make changelog` で生成も可 |
| `RELEASE_NOTES.md` | 利用者向けの要点 |
| `versions.mk` | 構成要素の版（プロジェクト版は `git describe` 由来） |
| `Dockerfile` の `LABEL version` | 実態とずれていた前例あり |
| `README.md` | 数値・バージョン表記（**英語セクションも**） |
| `SPECIFICATION.md` | 仕様の変更があれば |

**破壊的変更・既知の問題を隠さないこと。** 前の版に無かった制約
（例: イメージサイズが 1.17MB → 2.78MB になった理由は
**v2.0.1 に Init も libc も入っていなかったから**）は明記します。

`docs-reconciler` subagent で突合できます。

---

## 4. 承認を求める

3行で出します。長々と説明しない。

```
<版> を出せる状態になりました。
品質ゲート: <結果>。成果物検査: <結果>。記録: <更新したファイル>。
既知の問題: <あれば>。
タグを打って Docker Hub に出してよいですか？
```

**ユーザーが「まだ出せない」と言うことがあります。** その場合は
コミットまでで止め、`TODO.md` に保留として記録します
（2026-10-09 時点では「まだリリースタグ切って、docker hub にpushはできません。
CIは回せますけど」という状態でした）。

---

## 5. 承認を得てから

```bash
git tag -a v<X.Y.Z> -m "<日本語の説明>"
git push origin v<X.Y.Z>
```

**`release.yml` が走り、Docker Hub の `latest` を含む公開イメージを
差し替えます。** 走り始めたら監視して報告します。

```bash
gh run watch
```

失敗したときは**作戦を勝手に変えないこと**。状況を報告して指示を待ちます。

---

## タグを間違えたとき

```bash
git tag -d <tag>                    # ローカル
git push origin :refs/tags/<tag>    # リモート（要承認）
```

**Docker Hub に出てしまったイメージは消しても取り戻せません。**
出てしまったことを前提に、次の版で直す方針をユーザーと決めます。

> 前例: `git tag --list` の打ち間違いで `list` というローカルタグが
> できていた（`origin` には無かったので影響なし）。
> `scripts/get-version.sh` は `--match 'v[0-9]*'` でリリースタグだけを見ます。

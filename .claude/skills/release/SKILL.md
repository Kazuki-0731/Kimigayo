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
| `CHANGELOG.md` | `[Unreleased]` を新しい版見出しに移す。**手で書く**（`make changelog` は `build/` に下書きを出すだけ。`CHANGELOG.md` は書き換えない） |
| `RELEASE_NOTES.md` | 利用者向けの要点 |
| `versions.mk` | 構成要素の版（プロジェクト版は `git describe` 由来） |
| `Dockerfile` の `LABEL version` | 実態とずれていた前例あり |
| `README.md` | 数値・バージョン表記（**英語セクションも**） |
| `SPECIFICATION.md` | 仕様の変更があれば |

### 公開面の文書が実装と合っているか

**`DOCKERHUB_README.md` は Docker Hub の Overview にそのまま出ます。**
CI は中身を検証しないので、実装していない機能が宣伝されたまま残ります。

```bash
# 宣伝している仕組みの「受け取り側」があるか
grep -rn 'seccomp' scripts/ configs/ Dockerfile*          # プロファイルは rootfs に入るか
grep -rn -i 'cosign\|content trust' .github/workflows/release.yml
grep -rn 'REPRODUCIBLE_BUILD' Makefile build-system/Makefile scripts/
# 案内しているタグが実在するか
curl -s 'https://hub.docker.com/v2/repositories/ishinokazuki/kimigayo-os/tags/?page_size=100' |
    python3 -I -c 'import json,sys; print(sorted(t["name"] for t in json.load(sys.stdin)["results"]))'
```

> 2026-10-11 に削除したもの: 「seccomp-BPF をデフォルトで有効化」
> 「再現可能ビルド＝ビット同一」「`stable` / `edge` タグ」
> 「Minimal はカーネル込み」。**どれも一度も実装されていません。**
> セキュリティパッチの期限も、`SECURITY_POLICY.md`（Critical 7日）より
> 厳しい「24〜48時間」を公開面だけで約束していました。
>
> **Cosign は 2026-10-11 に実装しました**（`release.yml` の `sign`
> ジョブ、キーレス署名）。**効くのは v3.0.2 以降で、v3.0.1 以前の
> 公開イメージは未署名です。** 「署名されている」と書くときは、
> どの版からかを必ず添えてください。

**`CHANGELOG.md` を `make changelog` で上書きしないこと。**
このコマンドは `build/CHANGELOG.generated.md` に下書きを出すだけです
（2026-10-11 まで `cat > CHANGELOG.md` で全消しする作りでした）。

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

## 6. 公開されたものを実際に引いて確かめる

**`release.yml` が成功した = 中身が正しい、ではありません。**
ワークフローは「渡された値」でイメージを作るだけなので、
渡す値が間違っていても緑になります（→ `workflow-auditor`）。
**Docker Hub から実際に pull して中身を見ます。**

```bash
# 1) タグが揃ったか。count フィールドは当てにならないので行数で数える
curl -s 'https://hub.docker.com/v2/repositories/ishinokazuki/kimigayo-os/tags/?page_size=100' |
    python3 -I -c 'import json,sys; d=json.load(sys.stdin); print(len(d["results"]), "件"); [print(t["name"], t["last_updated"][:19]) for t in sorted(d["results"], key=lambda x: x["name"])]'
```

`latest` 系は **12 タグ**です（`latest` / `latest-amd64` / `latest-arm64` /
`latest-{minimal,standard,extended}` / `latest-{minimal,standard,extended}-{amd64,arm64}`）。
**全部が今回のリリース時刻に更新されていること。**

```bash
# 2) マルチアーキのマニフェストが両方を指しているか
docker buildx imagetools inspect ishinokazuki/kimigayo-os:latest | grep -E 'Platform|MediaType'

# 3) 中身がタグどおりか（両アーキでやる）
for plat in amd64 arm64; do
    docker pull -q --platform "linux/$plat" ishinokazuki/kimigayo-os:latest
    docker image inspect ishinokazuki/kimigayo-os:latest \
        --format '{{index .Config.Labels "version"}} / {{index .Config.Labels "io.kimigayo.variant"}} / {{.Architecture}}'
    docker run --rm --platform "linux/$plat" ishinokazuki/kimigayo-os:latest /bin/sh -c '
        . /etc/os-release; echo "$VERSION_ID $VERSION_CODENAME"
        etype=$(dd if=/bin/busybox bs=1 skip=16 count=2 2>/dev/null | od -d | head -1 | awk "{print \$2}")
        [ "$etype" = 3 ] && echo "busybox: PIE ✓" || echo "busybox: PIE ではない ✗"
        /sbin/openrc default >/dev/null 2>&1 && echo "init: rc=0 ✓" || echo "init: 失敗 ✗"
    '
done
```

**確認すること:**

| | 一致していること |
| --- | --- |
| イメージタグ | `3.0.0` |
| `LABEL version` | `3.0.0` |
| `/etc/os-release` の `VERSION_ID` | `3.0.0` |
| `LABEL io.kimigayo.variant` | そのタグのバリアント |
| `/bin/busybox` の ELF type | `3`（DYN = PIE）|
| `openrc default` | 終了コード 0 |

**一致していなければ、タグ名だけ合っていて中身が違う状態です。**
v0.1.0〜v2.0.1 の公開イメージは全部この状態でした（`0.1.0` と名乗っていた）。

### 署名を検証する（v3.0.2 以降）

**「署名ジョブが緑」ではなく、実際に `cosign verify` が通ることを見ます。**

```bash
cosign verify "ishinokazuki/kimigayo-os:<X.Y.Z>" \
  --certificate-identity-regexp '^https://github.com/Kazuki-0731/Kimigayo/' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com
```

**`latest` 系も含めて確認します。** `sign` ジョブはタグを全部並べて
ダイジェストに解決し、重複を落としてから署名します。
**新しいタグを `create-manifest` に足したら `sign` の `tags` にも足すこと。**
片方だけだと「署名されていないタグ」が混ざり、利用者の検証が落ちます。

### GitHub Release も見る

```bash
gh release view v<X.Y.Z> --json tagName,isDraft,assets
```

tarball 6本（3バリアント × 2アーキ）と `SHA256SUMS` / `SHA512SUMS` の
**計8ファイル**が付いていること。draft のままになっていないこと。

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

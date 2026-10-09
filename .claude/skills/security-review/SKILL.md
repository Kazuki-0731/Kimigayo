---
name: security-review
description: Kimigayo OS のセキュリティを点検する。脆弱性（CVE）の追跡、強化フラグが成果物に効いているかの検証、イメージの攻撃面、ビルド経路の完全性、脆弱性報告への対応。セキュリティを確認したい・監査したい・CVE を調べたい・強化したい・脆弱性報告が来たときに使う。
---

# セキュリティ点検

**最初に読むこと: このプロジェクトでは一般的なコンテナ脆弱性スキャナが
機能しません。** それを知らずに `make security-scan` の「✅ 完了」を
信じると、何も検査していない状態を安全だと誤認します。

---

## 0. なぜ普通のスキャナが効かないか（実測）

```
$ trivy image --scanners vuln kimigayo-os:standard-x86_64
┌────────┬──────┬─────────────────┐
│ Target │ Type │ Vulnerabilities │
├────────┼──────┼─────────────────┤
│   -    │  -   │        -        │
└────────┴──────┴─────────────────┘
Legend:  - '-': Not scanned

$ trivy image --format json ... | jq '.Metadata.OS, (.Results|length)'
null
0
```

**Trivy は「脆弱性 0 件」ではなく「スキャンしていない」と言っています。**

理由: Kimigayo は `scratch` 上に手でビルドした rootfs を置いただけで、
**パッケージデータベースが存在しません**（`/lib/apk/db` も
`/var/lib/dpkg` も無い）。Trivy の OS パッケージスキャナは
データベースから版を読んで CVE 表と突合する仕組みなので、
データベースが無い＝対象を1つも識別できません。
`Metadata.OS: null` がその証拠です。

**これはパッケージマネージャーを持たない設計の必然的な代償です。**
欠陥ではありませんが、**代わりの手段を人が用意しないと脆弱性管理が
ゼロになります。**

`make trivy-fs-scan`（ファイルシステムスキャン）は別物で、
**リポジトリ側**の依存（`requirements-dev.txt` など）を見るので意味があります。
`make trivy-scan`（イメージスキャン）に意味はありません。

> **着地させるべき構造的な対策: SBOM を出す。**
> SPDX か CycloneDX で構成要素（musl / BusyBox / OpenRC とその版）を
> 宣言すれば、利用者側のスキャナが突合できるようになります。
> 現在このリポジトリは SBOM を生成していません。
> 提案するときは「やりますか？」で止めること（スコープ拡大）。

---

## 1. 攻撃面を正しく捉える

| 層 | イメージに入るか | 誰の責任で直すか |
| --- | --- | --- |
| musl libc | **入る**（`/usr/lib/libc.so`） | 版を上げて再ビルド・再リリース |
| BusyBox | **入る**（`/bin/busybox` + 約400アプレット） | 同 |
| OpenRC | **入る**（`/sbin/*`、`librc.so.1`、`libeinfo.so.1`） | 同 |
| Linux カーネル | **入らない** | ホスト側。ベアメタル／QEMU 検証のときだけ自前 |
| Alpine ビルド環境 | **入らない** | ビルド時のみの露出 |
| 利用者が `COPY` するもの | 入る | 利用者 |

**カーネルの CVE はコンテナ利用者にとってはホストの問題です。**
「カーネルを強化している」ことをコンテナの安全性として語らないこと。

**ビルド環境の CVE は成果物に乗りません。** `Dockerfile`（Alpine ベース）の
脆弱性と `Dockerfile.runtime`（scratch）の脆弱性を混同しないこと。
ただしビルド環境が汚染されれば成果物も汚染されるので、別の種類の
リスク（供給網）として扱います。

---

## 2. CVE を追跡する（手で、版ごとに）

スキャナが使えないので、**構成要素の版を自分で突合します。**
版は `versions.mk` が単一の真実の源。

```bash
make print-versions
```

| 構成要素 | 一次情報 |
| --- | --- |
| musl | `https://musl.libc.org/releases.html`、oss-security ML、Alpine の secdb |
| BusyBox | NVD で `cpe:/a:busybox:busybox`、`https://bugs.busybox.net/` |
| OpenRC | GitHub の `OpenRC/openrc` の Security Advisories、aports |
| Linux カーネル | `https://www.kernel.org/releases.json`（**EOL も見る**）、CVE アナウンス |
| Alpine（ビルド環境） | `https://security.alpinelinux.org/` |

```bash
# Alpine の secdb は musl / busybox の修正版を arch 別に持っている
curl -s https://secdb.alpinelinux.org/v3.24/main.json |
  python3 -I -c '
import json,sys
d=json.load(sys.stdin)
for p in d["packages"]:
    n=p["pkg"]["name"]
    if n in ("musl","busybox","openrc"):
        print(n, p["pkg"]["secfixes"])'
```

**「影響あり」と書く前に、その機能が有効になっているかを確かめます。**
BusyBox の CVE はアプレット単位のことが多く、`CONFIG_<applet>=n` なら
そのコードはバイナリに入っていません。

```bash
# minimal / standard / extended のどれで有効か
grep -n 'CONFIG_<APPLET>' src/busybox/config/*.config
docker run --rm --platform linux/<arch> <image> busybox --list | grep -x '<applet>'
```

**バリアントごとに結論が変わります。** minimal 370 / standard 403 /
extended 413 アプレット。1つの答えで済ませないこと。

`version-auditor` subagent に上流の新版調査を任せられます。

---

## 3. 強化フラグが成果物に効いているかを検証する

**`config.mk` に書いてあることは宣言で、検証ではありません。**

```makefile
SECURITY_CFLAGS  := -fPIE -fstack-protector-strong -D_FORTIFY_SOURCE=2
SECURITY_LDFLAGS := -Wl,-z,relro -Wl,-z,now -Wl,-z,noexecstack
```

成果物の ELF を見て確かめます。

```bash
# ビルド環境のコンテナに readelf があるので、tarball から取り出して見る
for b in bin/busybox sbin/openrc sbin/start-stop-daemon sbin/supervise-daemon; do
  echo "--- $b ---"
  docker run --rm --platform linux/amd64 -v "$PWD/output:/o:ro" \
    kimigayo-os-build:latest sh -c "
      mkdir -p /x && tar xzf /o/kimigayo-standard-latest-x86_64.tar.gz -C /x ./$b &&
      readelf -lWdh /x/$b | grep -E 'GNU_RELRO|GNU_STACK|BIND_NOW|NEEDED|Type:'"
done
```

**合格の形**（2026-10-09 に x86_64 standard で確認済み）:

| 項目 | 見るもの | 期待 |
| --- | --- | --- |
| Full RELRO | `GNU_RELRO` セグメント + `FLAGS BIND_NOW` | 両方あること |
| NX（実行不可スタック） | `GNU_STACK` の権限 | `RW`（`E` が無いこと） |
| PIE | `readelf -h` の `Type` | `DYN`（`EXEC` ではない） |
| 不要な動的依存が無い | `NEEDED` | musl と OpenRC 自身の lib だけ。**`libcap.so.2` が出たら不合格**（静的リンクしているはず） |

**スタックカナリアは `readelf` では直接見えません。** strip 済みなので
`__stack_chk_fail` シンボルも消えています。ビルドログで
`-fstack-protector-strong` が渡っていることを確認します。

**両アーキテクチャで見ます。** 片方だけ通ることが実際にあります
（arm64 で `__letf2` 未解決により動的リンクのバイナリが全滅していた）。

---

## 4. イメージそのものの攻撃面

```bash
docker run --rm --platform linux/<arch> <image> /bin/sh -c '
  echo "uid=$(id -u) gid=$(id -g)"
  ls -l /etc/passwd /etc/shadow /etc/group
  echo "--- setuid/setgid ---"
  find / -xdev \( -perm -4000 -o -perm -2000 \) -exec ls -l {} \;
  echo "--- 誰でも書けるファイル ---"
  find / -xdev -type f -perm -0002 -exec ls -l {} \;
'
```

2026-10-09 時点の実測:

- **uid=0（root）で動く。`Dockerfile.runtime` に `USER` が無い。**
  distroless は `nonroot`（65532）を用意している。
  **これは設計判断としてユーザーに確認する事項**で、勝手に変えないこと
  （`USER` を入れると既存利用者のイメージが壊れる可能性がある）
- `/etc/shadow` は 0600、`/etc/passwd` と `/etc/group` は 0644（妥当）
- **setuid/setgid バイナリは0件**（良い）

機密が混入していないかも見ます。

```bash
docker run --rm <image> /bin/sh -c 'ls -la /root /home 2>/dev/null'
grep -rIl 'DOCKER_HUB\|ACCESS_TOKEN\|BEGIN .*PRIVATE KEY' build/rootfs 2>/dev/null
find build/rootfs -name '._*' | head   # macOS の AppleDouble（実測458個の前例）
```

---

## 5. ビルド経路の完全性（供給網）

**ここが一番壊れやすく、壊れても動いてしまいます。**

### チェックサム

```bash
# チェックサムが無い版は警告だけ出して通ってしまう
grep -rn 'SHA256\|sha256' scripts/download-*.sh | head
```

- **自分でダウンロードして `shasum` を取るだけでは駄目**。
  「ダウンロードしたものと同じ」しか言えません
- カーネル・BusyBox は上流の公開値と突合
- **musl と OpenRC は公式の SHA256 一覧が無い** → **Alpine aports の
  `sha512sums` と突合**
- OpenRC の tarball は GitHub の**自動生成アーカイブ**で、理論上バイト列が
  変わりうる。合わなくなったら改竄だけでなく再生成も疑う

### apk の署名検証

Alpine はアーキテクチャごとに別の鍵で署名しています。
x86_64 のイメージには x86_64 用の鍵しか入りません。

```dockerfile
apk fetch --arch aarch64 --keys-dir /usr/share/apk/keys/aarch64 ...
```

**`--allow-untrusted` で黙らせないこと。** 署名検証は維持します。
これは「エラーを黙らせる変更」の一種で、提案に留める対象です。

> 前例: `apk fetch` は**依存を解決しません**（`apk add` と違う）。
> Alpine 3.24 の `libcap` は中身の無いメタパッケージ（1301バイト）で、
> 実体は `libcap2`。しかもコピー失敗を `2>/dev/null || true` が
> 握り潰していたため、sysroot のライブラリがリンク切れのまま進んでいた。
> **握り潰しはセキュリティ上の問題でもあります**（検証の不在が見えなくなる）。

### GitHub Actions

```bash
grep -rn 'uses:' .github/workflows/ | grep -v '@v\|@[0-9a-f]\{40\}' | grep -v '\./'
```

**`@master` 参照は供給網のリスクかつ再現性がありません。**
tag か SHA で固定します（2026-10-09 に `trivy-action@v0.36.0`・
`action-shellcheck@2.0.0` を固定しました）。

### 機密

`.env`（`DOCKER_HUB_ACCESS_TOKEN`）は `.gitignore` 済み。
**`.claude/` は共有するのでそこにも置かない。**
`.claude/hooks/guard-bash.sh` が `git add .env` をブロックします。

```bash
git log --all --diff-filter=A --name-only | grep -x '.env' && echo "過去にコミットされた形跡あり"
```

---

## 6. 定期的に動いている仕組み

| ワークフロー | いつ | 何をするか |
| --- | --- | --- |
| `security.yml` | 毎日 02:00 UTC | 構成要素の版確認・脆弱性スキャン・Issue 起票 |
| `base-image-update.yml` | 毎週月曜 03:00 UTC | 上流の更新を検知して PR |
| `dependency-review.yml` | PR、毎週月曜 04:00 UTC | `fail-on-severity: high` |

**これらが作る PR / Issue は「上流が動いた」という一次情報**なので、
バージョン更新の起点として先に見ます。

```bash
gh issue list --label security --limit 10
gh pr list --limit 10
```

---

## 7. 脆弱性報告が来たとき

手順の正本は [docs/security/VULNERABILITY_REPORTING.md](../../../docs/security/VULNERABILITY_REPORTING.md)。
方針は [SECURITY_POLICY.md](../../../docs/security/SECURITY_POLICY.md)、
テンプレートは `SECURITY_ADVISORY_TEMPLATE.md` と `AUDIT_REPORT_TEMPLATE.md`。

**公開の場（Issue・PR・コミットメッセージ）に未公表の脆弱性の詳細を
書かないこと。** 報告者の連絡先も書かない。

### パッケージマネージャーが無いことの帰結

**利用者は `apk upgrade` で直せません。** 対応は必ずこの形になります。

1. `versions.mk` で構成要素の版を上げる（→ `version-bump` skill）
2. 再ビルド
3. `rootfs-verifier` で成果物を検査
4. 新しいタグを切って Docker Hub に出す（→ `release` skill、**要承認**）
5. 利用者に再 pull と再ビルドを案内する

**「次のリリースまで待てない」種類の脆弱性では、暫定の回避策
（アプレットを無効にする、該当機能を使わない設定）を先に案内します。**

影響範囲は必ず**バリアント × アーキテクチャ × 版**で書きます。
「Kimigayo に影響あり」では利用者が判断できません。

---

## 8. やってはいけないこと

- **強化フラグを緩める変更を勝手に入れない。** `-Wno-error`・`|| true`・
  `2>/dev/null`・`--allow-untrusted` はすべて提案に留める対象です
  （CLAUDE.md「指示の範囲を超えない > 開発」節）。
  **既に同種のものがあることは、増やしてよい理由になりません**
- **「異常だ」と書く前に仕様でないかを確かめる。**
  パッケージマネージャーが無いのは**意図した設計**であって欠落ではない。
  シェル（BusyBox `sh`）が入っているのも設計（distroless と違う点）
- **スキャナの沈黙を安全と読まない。** 第0節のとおりです
- **片方のアーキテクチャの結果で結論を出さない**

---

## 9. 着地させる

点検して報告するだけで終わらせない（CLAUDE.md「数値を出したら反映まで」節）。

| 着地先 | 何をするか |
| --- | --- |
| `docs/security/` | `SECURITY_AUDIT.md`・`HARDENING_GUIDE.md` に結果を追記 |
| config | カーネル / BusyBox config、`configs/sysctl/` を実際に変える（または外す） |
| CI | 退行を検知したいならワークフローか回帰テストに落とす |
| Hook | 機械的に止められるものは `.claude/hooks/` へ |
| `CHANGELOG.md` | 修正した脆弱性と、取り消した誤った安全性の主張 |

**「着地先なし」も結論として選べます。** その場合は**なぜ活かせないのか・
何が揃えば活かせるのか**を書き残します。

コミットは 🔒（セキュリティ）。

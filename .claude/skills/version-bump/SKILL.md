---
name: version-bump
description: 構成要素（musl / Linux カーネル / BusyBox / OpenRC / Alpine）のバージョンを上げる。上流の調査からチェックサムの突合、パッチの当て直し、ビルド検証、ドキュメント反映までの手順。バージョンを上げたい・上げられるか調べたいときに使う。
---

# 構成要素のバージョンを上げる

**バージョン変更は「提案に留める」対象です**（CLAUDE.md「指示の範囲を
超えない > 開発」節）。ユーザーの明示的な指示がある場合だけ実行に進みます。
指示がなければ **調査して判断材料を出すところで止めます。**

2026-10-09 の更新（カーネル 6.6.11→6.18.55 / musl 1.2.4→1.2.6 /
BusyBox 1.36.1→1.38.0 / OpenRC 0.52.1→0.63.2 / Alpine 3.23→3.24）で
**実際に踏んだ罠を全部ここに畳んであります。**

---

## 1. 現状を確定させる

```bash
make print-versions
git describe --tags --match 'v[0-9]*'
for c in musl busybox openrc; do
  printf '%-10s %s\n' "$c" \
    "$(find build -maxdepth 2 -name '.kimigayo-build-version' \
        -path "*${c}-install-*" -exec cat {} \; 2>/dev/null)"
done
ls build/kernel/output/vmlinuz-* 2>/dev/null
```

`versions.mk` の宣言と、**実際にビルドされている版**を区別します。
`version-auditor` subagent に投げてもよい。

## 2. 上流の現在値を自力で取る

**ユーザーに「ページを開いて貼ってください」と頼まないこと。**

| 欲しいもの | 取得元 |
| --- | --- |
| カーネルの最新版・LTS・EOL | `curl -s https://www.kernel.org/releases.json` |
| カーネルのチェックサム | `https://cdn.kernel.org/pub/linux/kernel/v6.x/sha256sums.asc` |
| BusyBox | `https://busybox.net/downloads/`、`busybox-<ver>.tar.bz2.sha256` |
| musl | `https://musl.libc.org/releases.html` |
| OpenRC | aports の `main/openrc/APKBUILD` の `pkgver` |
| Alpine | `https://alpinelinux.org/releases/` |

**カーネルは EOL も確認します。** LTS を選び、EOL が近いものに上げない。

## 3. 上流の破壊的変更を先に調べる（ここを飛ばすと必ず詰まる）

**上流のビルドオプションは消えます。**

- **OpenRC / meson** — `meson_options.txt` を取得して、こちらが渡している
  オプションが全部残っているか突合する。0.52.1 → 0.63.2 で
  `os`・`capabilities`・`rootprefix`・`split-usr`・`termcap` が削除され、
  `-Dos=Linux` を渡していた `build-openrc.sh` が "Unknown options" で落ちた
- **オプションが消えると、任意だった依存が必須になる。** libcap は
  `dependency('libcap', required: get_option('capabilities'))` から
  無条件の `dependency('libcap', version: '>=2.33')` になり、
  **無効化できなくなった**
- **BusyBox** — `make oldconfig` の差分を見る
- **カーネル** — `make olddefconfig` の出力を見る
- **`NEWS.md` / `Changelog` を読む。** OpenRC 0.62 では `ready` → `notify` の
  リネームと、キャッシュ位置の `libexec` → `/var/cache/rc` 変更があった

## 4. versions.mk だけを変える

```makefile
KERNEL_VERSION  ?= 6.18.55   # LTS, EOL 2028-12
MUSL_VERSION    ?= 1.2.6
BUSYBOX_VERSION ?= 1.38.0
OPENRC_VERSION  ?= 0.63.2
ALPINE_VERSION  ?= 3.24
```

**他の場所に数字を書かない。** 書いたら次の更新で必ず漏れます。

## 5. 同じターンでチェックサムを更新する

`scripts/download-*.sh` のチェックサム表を直します。

**自分でダウンロードして `shasum` を取っただけでは駄目です。**
それは「ダウンロードしたものと同じ」しか言えません。

- カーネル・BusyBox → 上流の公開値と突合
- **musl・OpenRC は公式の SHA256 一覧が無い** → **Alpine aports の
  `sha512sums` と突合する**（2026-10-09 はこの方法で musl 1.2.6 と
  OpenRC 0.63.2 を検証した）
- OpenRC の tarball は GitHub の**自動生成アーカイブ**。
  `releases/download/...` は全バージョンで 404（実測）。合わなくなったら
  改竄だけでなく再生成も疑い、aports と突合する

**チェックサムが無いバージョンは警告だけ出して通ってしまいます。**
「警告が出たまま」を放置しないこと。

## 6. パッチを確認する

```bash
# 当たるかを先に dry-run で見る
cd build/busybox-<新版> && patch -p1 --dry-run < ../../src/busybox/patches/<p>.patch
```

**`apply-*-patches.sh` は当たらないパッチを `log_warn` して `return 0` します。**
黙ってスキップされ、ビルドは成功したように見えます。

```bash
grep -iE 'skipped: [1-9]|not applicable' build/kernel-patches.log build/busybox-patches.log
```

出たら「上流が取り込んだので不要」か「当て直しが必要」かを判断します。
**消す前に、なぜ存在するかを調べます**（`src/kernel/patches/README.md`、
`docs/development/`、`git log --follow <patch>`）。

> **前例**: カーネル 6.6 用の `0002-disable-retpoline-realmode.patch` ほか
> 3本は `-std=gnu11` 回避策で、6.18 では上流が取り込んだため削除した。
> ただし `0003`/`0004` を消したあと `build-kernel.sh` の
> `REALMODE_CFLAGS` 上書きが残っていて
> `undefined reference to '__x86_return_thunk'` でリンクが落ちた。
> **上流の変数を「置き換える」と、その変数が持つ他の定義まで落ちます。**

## 7. build/ の残骸を疑う

版を上げると、2通りの形で事故になります。**2026-10-09 は両方踏みました。**

1. **黙って古いものが使われる（危険）** — BusyBox 1.36.1 が 1.38.0 の
   つもりで残り、`✅ build completed` と報告された
2. **後段で意味の分かりにくいエラー** — 古い meson の
   `openrc-build-*/meson-private/build.dat` が
   `references functions or classes that don't exist` で `meson setup` を止めた

いまは `.kimigayo-build-version` で突合して作り直しますが、
**妙な挙動をしたら `make clean-<component>` を試します**
（`clean-musl` / `clean-kernel` / `clean-busybox` / `clean-openrc`）。
`make clean-all` は約150MBの再取得を招くので最後の手段です。

**BusyBox のスタンプは版＋バリアント**（`1.38.0+standard`）。
バリアントを切り替えて測るときはスキップされていないことを確認します。

## 8. ビルドして検証する

**フルビルドは GitHub Actions で回します**（CLAUDE.md
「フルビルドは x86_64 / arm64 とも GitHub Actions で回す（既定）」節）。
開発機は Apple Silicon で `docker-compose.yml` が amd64 を強制するため、
カーネルのフルビルドは QEMU 経由で非現実的です。

```bash
# 手元でやるのは段を絞ったビルドまで
docker compose run --rm kimigayo-build sh -c \
  'cd /build/kimigayo && ARCH=x86_64 IMAGE_TYPE=standard bash scripts/build-rootfs.sh'
```

**arm64 のクロスビルドを手元で回すなら compose を使わない**
（`memory: 2G` で `meson setup` が OOM kill される）:

```bash
docker run --rm --platform linux/amd64 --memory 8g \
  -v "$PWD:/build/kimigayo:rw" \
  -v kimigayo-downloads:/build/kimigayo/build/downloads \
  -w /build/kimigayo kimigayo-os-build:latest \
  sh -c 'ARCH=arm64 IMAGE_TYPE=standard bash scripts/build-rootfs.sh'
```

**成果物は `rootfs-verifier` subagent に検査させます。**
「ビルドが成功した」は「成果物が正しい」ではありません。
**両アーキテクチャで実際に実行して確かめること**（arm64 だけ
`__letf2` 未解決で動的リンクのバイナリが全滅していた前例があります）。

## 9. ドキュメントに反映する（ここまでで1セット）

- `CHANGELOG.md` の `[Unreleased]`（タグを打つ前に必ず）
- `README.md`・`docs/` のバージョン表記と数値
- 捨てた古い値が残っていないか:

```bash
git diff versions.mk | grep '^-[A-Z]' | grep -oE '[0-9]+\.[0-9.]+' | sort -u |
while read -r v; do
  hits=$(grep -rn --fixed-strings "$v" \
    --include='*.mk' --include='Makefile' --include='Dockerfile*' \
    --include='*.sh' --include='*.py' --include='*.yml' . \
    | grep -v '^\./versions.mk' || true)
  [ -n "$hits" ] && { echo "--- 旧値 $v がまだ残っている:"; echo "$hits"; }
done
```

チェックサム表とコメント内の経緯は残っていて正しい。それ以外を直します。

## 10. 踏んだ罠を記録に落とす

**会話で説明して終わりにしないこと。** 次のセッションは会話を読みません。

| 種類 | 置き場所 |
| --- | --- |
| 版上げで壊れた箇所 | `TODO.md`、`CHANGELOG.md` |
| パッチの経緯 | `src/{kernel,busybox}/patches/README.md` |
| 同じ罠の再発防止 | `docs/troubleshooting/` に追記 |
| コードレベルのミス | `tests/unit/`・`tests/property/` に回帰テスト |
| 機械的に止められるもの | `verify_rootfs`・`.claude/hooks/`・CI |

**人の判断が絡まないミスは文章にしない。構造かチェックにします**
（CLAUDE.md「手段の選び方」節）。

## コミットの切り方

1修正=1コミット。日本語、先頭に絵文字1つ、テキスト prefix は付けない。
依存・バージョン更新は ⬆️、修正は 🐛、記録は 📝。

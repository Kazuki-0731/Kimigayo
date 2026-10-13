# Kimigayo OS 開発ガイド

## プロジェクト構造

```
Kimigayo/
├── .github/
│   └── workflows/          # CI/CD設定
├── build/                  # ビルド作業ディレクトリ（Git 管理外）
├── build-system/           # ビルドコンテナ内で使う Makefile（kernel / musl / busybox などのターゲット）
├── docs/                   # ドキュメント
├── examples/               # ベースイメージとしての使用例（python / nginx / nodejs）
├── src/                    # ソースコード
│   ├── kernel/             # カーネル設定（config/README.md のみ）・パッチ
│   ├── libc/patches/       # musl の CVE パッチ
│   └── busybox/            # BusyBox設定・パッチ
├── tests/                  # テストコード
│   ├── unit/               # 単体テスト（pytest）
│   └── integration/        # 統合テスト（シェル）
├── scripts/                # ビルドスクリプト
├── output/                 # ビルド出力
├── Dockerfile              # ビルド環境
├── docker-compose.yml      # Docker Compose設定
├── Makefile                # ビルドシステム
├── versions.mk             # 構成要素のバージョン（単一の真実の源）
├── CLAUDE.md               # 作業ルールとプロジェクト固有の勘所
└── SPECIFICATION.md        # 仕様書
```

## 開発環境

### Docker環境の使用

すべての開発はDockerコンテナ内で行うことを推奨します:

```bash
# ビルド環境イメージを構築
make docker-build

# シェルに入る（推奨。ビルドの進捗がリアルタイムで見える）
make shell

# 直接叩く場合
docker compose run --rm kimigayo-build /bin/bash
```

### ローカル環境（上級者向け）

Alpine Linux以外の環境で開発する場合:

必要なものの正本はビルド環境の `Dockerfile`（Alpine の `apk add` 一覧）。
Ubuntu/Debian で揃えるときの目安（この一覧で通るかは検証していない）:

```bash
sudo apt-get install build-essential gcc g++ make cmake meson ninja-build \
  musl-dev musl-tools linux-headers-generic libcap-dev \
  clang lld llvm bison flex bc gawk cpio \
  python3 python3-pip git
```

macOS では `make ci-build-local` は通らない（musl の `configure` が落ちる）。

## ビルドシステム

### Makefileターゲット

全量は `make help`。

```bash
# ヘルプを表示（これが最新の一覧）
make help

# OSをビルド（コンテナ内で musl -> kernel -> BusyBox -> OpenRC）
make build

# カーネル抜き（開発機ではこちらを推奨。イメージにカーネルは入らない）
docker compose run --rm kimigayo-build make build-no-kernel TARGET_ARCH=x86_64 IMAGE_TYPE=standard

# アーキテクチャ指定ビルド
# **ホストの `make build` に ARCH= を渡しても効かない。**
# `docker compose run --rm kimigayo-build make build` へ転送していないため
# （Makefile の build ターゲット）。build-system/Makefile が読むのは TARGET_ARCH
# （ARCH= も受け付けるが非推奨で、警告を出して TARGET_ARCH に読み替える）。
# arch を変えるならコンテナに直接渡す
# （IMAGE_TYPE の既定は standard。何を作るか読み手に分かるよう明示を勧める）:
docker compose run --rm kimigayo-build make build TARGET_ARCH=x86_64 IMAGE_TYPE=standard
docker compose run --rm kimigayo-build make build TARGET_ARCH=arm64 IMAGE_TYPE=standard

# ホストの ARCH= が効くのは ci-build-local 系だけ
make ci-build-local ARCH=arm64

# テスト実行
make test

# どこまで完了したか / ビルド設定
make status
make info

# クリーン（clean=成果物のみ / clean-cache=ダウンロードキャッシュ /
#   clean-all=Docker のボリュームとビルド環境イメージ。ホストの build/ は消さない。
#   コンテナ内の make clean-all は build/（downloads を除く）と output/ を消す）
make clean

# セキュリティスキャン（scan-image + Trivy FS + ShellCheck）
make security-scan

# rootfs から Docker イメージまで（GitHub Actions 相当）
make ci-build-local
```

**ISO イメージ生成（`make iso`）は無い。**
Kimigayo OS はコンテナ向けで、成果物は rootfs の tarball と Docker イメージ。

### ビルドプロセス

1. **musl libcビルド**: クロスコンパイル対応
2. **カーネルビルド**: `make build` のときだけ（`make build-no-kernel` では飛ばす）
3. **BusyBoxビルド**: カスタマイズ可能
4. **Initシステムビルド**: OpenRCベース
5. **ルートファイルシステム構築**
6. **イメージ生成**: rootfs tarball（`output/*.tar.gz`）→ Docker イメージ

**Docker イメージに入るのは rootfs だけで、カーネルは含まれない**
（コンテナはホストのカーネルで動く）。カーネルをビルドするのは
ベアメタル／QEMU 検証のため。

## テスト戦略

### 単体テスト

`tests/unit/` の pytest。BusyBox の config・リンク検査・Hook の判定規則を見ます
（3 ファイル 65 件、2026-10-14 時点。→ [tests/README.md](tests/README.md)）。

```bash
# 依存をインストール
pip install -r requirements-dev.txt

# 全部
python3 -m pytest tests -q

# 特定のテストを実行
pytest tests/unit/test_check_links.py -v

# マーカーで絞る（unit / integration / slow / security）
pytest -m "not slow" -q
```

### 統合テスト

システム全体をテスト:

```bash
# rootfs tarball ができたかの確認（ホスト）
make test-integration

# Dockerイメージの起動テスト
make test-docker

# 機能テスト（BusyBox, Network）
make test-func

# QEMU でのカーネル起動テスト
ARCH=x86_64 bash scripts/test-kernel-qemu.sh
```

## デバッグ

### QEMUでのデバッグ

`make qemu-debug` / `make qemu-test` というターゲットは無い（ビルドコンテナ側にあった
「Phase 4 で実装」と表示するだけの空ターゲットは 2026-10-13 に消した）。スクリプトを直接使う。

```bash
# QEMUでカーネルを起動
ARCH=x86_64 TIMEOUT=30 bash scripts/test-kernel-qemu.sh

# ビルド済みカーネルイメージの場所
ls build/kernel/output/

# GDBアタッチ（QEMU 側に -s -S を渡して起動した場合）
gdb -ex "target remote :1234" build/kernel-src/linux-$(make -s print-kernel)/vmlinux
```

### ログ確認

```bash
# 各コンポーネントのビルドログ（最新100行）
make log-kernel
make log-musl
make log-openrc   # build/logs/openrc-build.log

# パッチ適用の結果（版上げ後は必ず見る）
grep -i 'skipped\|not applicable' build/kernel-patches.log build/busybox-patches.log

# 生ログ
ls build/logs/
```

## セキュリティ

### セキュリティチェック

`scripts/build-{musl,busybox,openrc}.sh` が次のフラグを渡します:

- **PIE**: Position Independent Executables
- **RELRO**: `-Wl,-z,relro -Wl,-z,now`（Full RELRO）
- **非実行スタック**: `-Wl,-z,noexecstack`
- **Stack Protection**: `-fstack-protector-strong` — 両アーキの全構成要素に渡す。
  **v3.0.2 の arm64 の OpenRC には付いていない**（`build-openrc.sh` が arm64 だけ
  外していた。main で修正済み、次のリリースから付く。`verify-image.sh` が検査する）
- **FORTIFY_SOURCE**: `-D_FORTIFY_SOURCE=2` — **x86_64 だけ効いている。**
  x86_64 はビルド環境の Alpine のヘッダを使い、`fortify-headers` が前に入る。
  arm64 は自前の musl のヘッダだけを `-isystem` で見ており、musl は FORTIFY を
  実装しないので効かない（2026-10-13 にテストプログラムで実測。公開中の
  3.0.2 の arm64 の BusyBox にも検査コードが無い）

成果物に効いているかは `scripts/verify-image.sh` が見る。イメージを
`docker export` した tar を `scripts/check-elf-hardening.py` が読み、
**イメージ内のすべての ELF** について PIE・RELRO・BIND_NOW・非実行スタック・
スタック保護（libc から 20 個以上の関数を取り込む動的 ELF が `__stack_chk_fail`
を参照しているか）を検査する（以前は `/bin/busybox` が PIE かどうかだけだった）。

`verify-image.sh` の「セキュリティの回帰」ではほかに次を見る:

- **出荷物の構成要素の版** — イメージ内のバイナリを実行して読んだ
  BusyBox / musl / OpenRC の版を `versions.mk` と突合する
  （`scripts/lib/image-components.sh`）。古いビルド結果が残って
  宣言と違う版が出荷されるのを止める
- **cpio のパストラバーサル** — `../` を含むアーカイブを実際に展開し、
  展開先の外に書き出さないこと（`CONTAINED`）を確かめる。
  v3.0.1 の公開イメージはここで `ESCAPED` になる（修正前の状態）

### セキュリティスキャン

```bash
# 総合（scan-image + Trivy FS + ShellCheck）
make security-scan

# 個別
make scan-image          # 出荷物の CVE 照合（SBOM + Grype）と秘密情報スキャン
make trivy-fs-scan       # リポジトリ側の依存
make shellcheck-scan
make trivy-scan          # Kimigayo は識別されない（下記）
```

**`make scan-image` は出荷するイメージそのものを検査する**
（`scripts/scan-image.sh`。対象は `kimigayo-os:$(VARIANT)-$(ARCH)` なので、
先にイメージをビルドしておく）。

- **CVE 照合（`vuln`）** — イメージ内のバイナリから読んだ版で CycloneDX の
  SBOM を作り、Grype（`anchore/grype:v0.120.1`）で NVD の CPE と照合する。
  CPE は `busybox:busybox` / `musl-libc:musl` / `openrc_project:openrc`
- **秘密情報（`secret`）** — Trivy の secret スキャナで rootfs のファイルを見る
- grype / trivy がホストに無ければ、版を固定した公式 Docker イメージで動かす

| 環境変数 | 既定 | 意味 |
| --- | --- | --- |
| `SCANS` | `secret vuln` | 実行する検査。片方だけなら `SCANS=secret` など |
| `SBOM_OUT` | `build/sbom/kimigayo-<variant>-<arch>.cdx.json` | SBOM の出力先 |
| `FAIL_ON` | `low` | この深刻度以上の CVE で失敗する（Grype の `--fail-on`） |

> **v3.0.1 の公開イメージでは CVE 照合が失敗する。**
> 2026-10-11 に 5 件を検出し、`main` で 5 件ともパッチを当てた。
> パッチ済みの CVE は照合結果から除外される（`/.kimigayo-build-info` の
> `PATCHED_CVES`）。→ [docs/security/SECURITY_AUDIT.md](docs/security/SECURITY_AUDIT.md)

> **`make trivy-scan`（イメージスキャン）は実質何も検査していない。**
> Kimigayo は `scratch` 上の手組み rootfs でパッケージデータベースを
> 持たないため、Trivy は対象を 1 つも識別できない
> （`Target: -` / `Not scanned` / `Results: 0`）。
> **「脆弱性 0 件」ではなく「スキャンしていない」。**
> そのため 2026-10-11 に `security-scan` から外し、脆弱性の検査は
> `scan-image` に置き換えた。
> **`make trivy-fs-scan` はリポジトリ側の依存を見るので有効。**

CI 側では次のように回る:

- **ビルドごと** — `build-workflow.yml` の verify-image ジョブが
  `scan-image.sh` で CVE と秘密情報を見る（失敗すればジョブも落ちる）。
  `release.yml` も Docker Hub への push 前に同じものを走らせる
- **毎週月曜 04:00 UTC と手動** — `dependency-review.yml` の
  `published-image-scan` ジョブが Docker Hub の `latest` を pull し、
  `scan-image.sh`（CVE + 秘密情報）を回す。定期実行で失敗したときだけ
  `create-security-issue` が Issue を起票する（手動実行では起票しない）
- **PR** — `dependency-review.yml` の依存レビュー。リポジトリの Trivy FS スキャン
  （`vulnerability-scan`）は PR と定期の両方で走る

## パフォーマンス測定

### 起動時間測定

```bash
make benchmark-startup
```

### メモリ使用量測定

```bash
make benchmark-memory
```

全ベンチマークは `make benchmark`。
**取った数値は README とベンチマークドキュメントに反映するまでが1セット**
（→ [CLAUDE.md](CLAUDE.md)「数値を出したら反映まで」節）。

### ベンチマーク

```bash
# 総合ベンチマーク
make benchmark
```

## トラブルシューティング

### ビルドエラー

```bash
# クリーンビルド（成果物のみ削除。ダウンロードキャッシュは残る）
make clean && make build

# Docker のボリュームごと消す（ダウンロードキャッシュも消える。再取得は約150MB）
# ホストの build/ の成果物は残るので、make clean も合わせて叩く
make clean && make clean-all && make build

# 個別のコンポーネントだけやり直す
# **ホストの Makefile に clean-<component> も kernel も無い**
# （どれも build-system/Makefile 側）。ホストで叩くと
# No rule to make target になるので、コンテナに渡す:
docker compose run --rm kimigayo-build make clean-kernel kernel
docker compose run --rm kimigayo-build make clean-musl clean-busybox clean-openrc
# または make shell で入ってから叩く
```

**版を上げた直後にビルドが通らないときは、まずパッチの適用結果を見る。**
当たらなかったパッチは黙ってスキップされる:

```bash
grep -i 'skipped\|not applicable' build/kernel-patches.log build/busybox-patches.log
```

### Dockerエラー

```bash
# イメージ再ビルド
make docker-rebuild

# コンテナ停止・削除
make down

# ボリューム（ダウンロードキャッシュ・出力）も削除
docker compose down -v
```

**開発機が Apple Silicon（arm64）の場合、`docker-compose.yml` が
`platform: linux/amd64` を固定しているため QEMU エミュレーションになる。**
musl / BusyBox / OpenRC は許容範囲だが、カーネルのフルビルドは
非現実的なので GitHub Actions に任せる（→ [CLAUDE.md](CLAUDE.md)
「フルビルドは x86_64 / arm64 とも GitHub Actions で回す（既定）」節）。

## リリースプロセス

### バージョニング

セマンティックバージョニング（MAJOR.MINOR.PATCH）:

- **MAJOR**: 互換性のない変更
- **MINOR**: 後方互換性のある機能追加
- **PATCH**: 後方互換性のあるバグ修正

### リリース手順

**`develop` ブランチは存在しない。** 作業は `main` で行う
（`ci.yml` のトリガーからも 2026-10-13 に外した）。

1. すべてのテストが通ることを確認（`make test` / `make shellcheck-scan`）
2. 成果物を検査（`rootfs-verifier` subagent、`scripts/verify-image.sh`）
3. **`CHANGELOG.md` と `RELEASE_NOTES.md` を手で更新**
   （`make changelog` は `build/` に下書きを出すだけで `CHANGELOG.md` は
   書き換えない）
4. README・docs の数値とバージョン表記を突合
5. **ユーザーの明示的な承認を取る**
6. タグ作成と push: `git tag -a v<版> -m "..." && git push origin v<版>`
7. `release.yml` が走り Docker Hub と GitHub Release を公開
8. **公開物を pull して中身を検証**

> **`v*.*.*` タグを push した瞬間に Docker Hub の `latest` を含む
> 公開イメージが差し替わり、取り消せない。**
> タグとリリースは毎回承認が必須（`.claude/hooks/guard-bash.sh` が
> 機械的に止める）。詳細は `release` skill。

## 参考資料

- [SPECIFICATION.md](./SPECIFICATION.md) - プロジェクト仕様
- [CONTRIBUTING.md](./CONTRIBUTING.md) - 貢献ガイド
- [Alpine Linux](https://alpinelinux.org/) - 参考ディストリビューション
- [musl libc](https://musl.libc.org/) - Cライブラリ
- [BusyBox](https://busybox.net/) - コアユーティリティ
- [OpenRC](https://github.com/OpenRC/openrc) - Initシステム

## サポート

- **Issues**: バグ報告、機能リクエスト
  （https://github.com/Kazuki-0731/Kimigayo/issues）
- **Discussions**: 質問、アイデア共有
  （https://github.com/Kazuki-0731/Kimigayo/discussions）

**ドキュメントの正本はこのリポジトリの `docs/` 配下**です
（Wiki ではありません）。

---

Happy Hacking! 🚀

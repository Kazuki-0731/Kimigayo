# Changelog

All notable changes to Kimigayo OS will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [Unreleased]

（次のリリースに入る変更をここに書く）

---

## [3.0.1] "Himawari" (向日葵) - 2026-10-11

**イメージから「あってはいけないもの」を2種類落とした版。**
パッケージマネージャー（BusyBox の `dpkg` / `rpm`）と、
Kimigayo では絶対に実行され得ない init スクリプト9本。
残りは計測スクリプトの修正と、仕様書・ドキュメントの訂正。

### Removed

- **`dpkg` / `dpkg-deb` / `rpm` をイメージから外した。**
  `SPECIFICATION.md` 2.2 / 3.5 は「パッケージマネージャーを意図的に排除」と
  書いているのに、v3.0.0 までの公開イメージには `/bin/dpkg`・`/bin/dpkg-deb`・
  `/bin/rpm` が入っており、**実際に `dpkg -i` でパッケージをインストールできた**。

  原因は config の書き忘れ。BusyBox の `archival/Config.in` は
  `DPKG`・`DPKG_DEB`・`RPM` をいずれも `default y` にしており、
  `scripts/build-busybox.sh` は config の断片をコピーしたあと
  `make oldconfig` を回すため、**書いていない項目には既定値が入る**。
  3バリアントとも dpkg が有効になっていた（`extended.config` だけ
  `CONFIG_RPM=n` を書いていたので rpm は無かった）。

  `rpm2cpio` は展開専用でインストール機能が無いため extended に残している。

- **Kimigayo では実行され得ない init スクリプト9本をイメージから外した。**
  OpenRC はどのディストリでも使えるよう一式を同梱しているが、
  次の9本は Kimigayo（VPS / クラウド上の Docker コンテナ）では
  1度も実行されない。

  | スクリプト | 落とした理由 |
  | --- | --- |
  | `agetty` | `/sbin/agetty` がイメージに無い（端末ログイン） |
  | `consolefont` | `/usr/bin/setfont` が無い |
  | `numlock` | `/usr/bin/setleds` が無い |
  | `runsvdir` | `/usr/bin/runsvdir` が無い（runit 用） |
  | `s6-svscan` | s6（別の Init）の監視を起動するもの |
  | `user` | ユーザー単位の OpenRC セッション |
  | `net-online` | ネットワーク疎通待ち（コンテナでは不要） |
  | `osclock` | 「時計は OS 任せ」と宣言するだけ |
  | `swclock` | RTC が無いマシンで時計を合わせる |

  **どれもランレベルに登録されていない。** 削除版をビルドして実測し、
  `openrc sysinit`/`boot`/`default` がいずれも rc=0、起動サービス数、
  `rc-update show` の行数、`--privileged` での `sysctl` 適用まで
  v3.0.0 と完全に一致することを確認した。15 本が持つ `after clock`
  （`osclock`/`swclock` が `provide`）は順序指定で必須依存ではないため、
  提供元を消しても依存解決は壊れない。

  **サイズ目的ではない**（約 12KB）。目的は root で解釈・実行される
  シェルスクリプトを減らすことと、`/etc/init.d` に実際に動くものだけが
  並んでいる状態にすること。`keyword -docker` が付いているだけのもの
  （`fsck`・`hwclock`・`modules`・`localmount` など 24 本）は**残している**
  （ベアメタルや特権コンテナでは正規に機能するため）。
  init スクリプトは 36 本 → **27 本**になった。

- **仕様書から「独自パッケージマネージャ」前提の記述を落とした。**
  当初は独自のパッケージマネージャを作る計画だったが取り下げた
  （2026-10-11 決定）。要件の「Distroless + Alpine のハイブリッド
  アプローチ」と両立しない。
  - `SPECIFICATION.md` 7 の「Phase 2: パッケージシステム」（設計・実装・
    ベースパッケージ・リポジトリシステム）
  - 同 5.3「パッケージセキュリティ」の Ed25519 / GPG 署名検証。
    パッケージという配布単位が無いので検証対象が存在しない
  - 同 12.1 の「独自のパッケージマネージャによる高速化」
    「東アジア圏のミラーサーバー最適化」（どちらも存在しない）
  - 同 3.1 / 3.3 / 3.4 の「または独自マイクロカーネル」「または独自実装」
    「または独自軽量initシステム」
  - `scripts/build-status.sh` のコンポーネント `pkg`（Package Manager）。
    ビルドする処理が無く、`make status` に永久に pending として出ていた

- **`build-system/Makefile` の `iso` / `docker-image` ターゲットを削除した。**
  どちらも `echo "... will be implemented in Phase 8"` だけのスタブで
  何も生成しないのに、`make help` が機能として案内していた。
  ISO はベアメタル起動が前提で対象外（2026-10-10 決定）。

### Fixed

- **起動時間とメモリのベンチマークが測るものを間違えていたのを直した。**
  `scripts/benchmark-startup.sh` は `docker run -d <image> sleep 5` の
  **終了まで**を測っており、正常なイメージほど必ず約 5,600ms になっていた
  （公開していた 439ms はこの `sleep` が成立しなかった値で、
  **イメージが壊れているほど速く見える**計測だった）。
  いまは `docker run --rm <image> /bin/true` の実時間を測り、
  `MODE=init` で `openrc default` の完走までも測れる
- **`scripts/benchmark-memory.sh` の単位換算を直した。**
  `KiB` を `0.001` に置換したうえ整数 MB に丸めており、
  **1MB 未満を 0 としか表せなかった**（公開していた 0.2MB）。
  単位を見て KB に正規化するようにし、KB で保持する。
  どちらも `PLATFORM` を受け取れるようにした（arm64 ネイティブで測るため）
- **`scripts/benchmark-comparison.sh` が既定で v2.0.1 のイメージを引いていた。**
  `KIMIGAYO_VERSION` の既定値が `2.0.1` に直書きされており、環境変数を
  渡さずに実行すると、新しい版を測っているつもりで v2.0.1 を pull して
  比較していた。`scripts/get-version.sh` から取るようにした
- **`scripts/benchmark-all.sh` が全部落ちても「完了」と言っていた。**
  6 ステップすべてが `|| true` で終わっており、6 本とも失敗しても
  「✓ 全ベンチマーク完了」と表示して終了コード 0 を返していた。
  最後まで走らせたうえで、落ちたものを名指しして非ゼロで終わるようにした
- **README が「Docker Hub 上のイメージは v2.0.1 のまま」と書いていた。**
  v3.0.0 を公開したあとも残っており、`latest` タグを案内する表のすぐ下に
  あったため「このタグを引くと v2.0.1 が来る」と読めた
- **README の目標値が `SPECIFICATION.md` 8.3 と食い違っていた。**
  仕様は Minimal 5MB / Standard 15MB / Extended 50MB と分けているのに、
  README は 3 バリアントとも `< 5MB` を分母に達成率を出していた
- **`SPECIFICATION.md` 9.2 が ISO イメージを作ると書いていた。**
  ISO はベアメタル起動が前提で、2026-10-10 に対象外と決めている
- **`make kernel` をホストのコマンドとして書いていた。**
  `kernel`・`musl`・`busybox`・`init`・`rootfs` が定義されているのは
  `build-system/Makefile` で、ホストの `Makefile` には無い。
  正しくは `docker compose run --rm kimigayo-build make kernel`。
  `CLAUDE.md`・`SPECIFICATION.md`・`BUILD_GUIDE.md` を訂正した
- **Docker Hub の説明文に、実装していない機能が並んでいた。**
  - 「seccomp-BPF をデフォルトで有効化」— 成果物は rootfs だけで
    カーネルを含まず、seccomp を適用するのはホストの runtime 側
  - 「再現可能ビルド: ビット同一なビルド出力」— `config.mk` の
    `REPRODUCIBLE_FLAGS` は `REPRODUCIBLE_BUILD=yes` のときだけ効くが、
    この変数をどこも設定していない。ビット同一性の検証記録も無い
  - 「イメージ署名: Docker Content Trust / Cosign」— `release.yml` に
    署名工程が無い
  - 「Trivy でイメージを自動スキャン」— パッケージデータベースを
    持たないため対象を1つも識別できない
  - 「Minimal は カーネル + musl libc + BusyBox」— カーネルは入らない
  - タグ例が `0.1.0`。存在しない `stable` / `edge` と、存在しない形式
    （`3.0.0-amd64`）を案内していた
- **`docs/deployment/DOCKERHUB_SETUP.md` に説明文の写しが2か所あった。**
  二重管理していたため、両方が上記の古い宣伝を抱えていた。
  `DOCKERHUB_README.md` への参照にした
- **`docs/developer/BUILD_GUIDE.md` が生成されないファイルを並べていた**
  （`.sig`・ISO・`build-report.json`）。存在しない `make bootloader` /
  `make create-image` も削除

### Added

- **起動時間・メモリ・コマンド性能の実測値**（2026-10-11、arm64 ネイティブ、
  中央値10回）。Standard は起動 **0.61秒** / 常駐 **232KB**（37標本すべて
  同値）/ BusyBox は Alpine 比 **0.96〜1.01x**。
  OpenRC の `default` 完走までは 0.77 秒。
  同じセッションでの比較: Alpine 0.62秒 / 276KB、
  Ubuntu 24.04 **0.59秒** / 312KB
- **「起動時間はイメージでは変わらない」という結論**を README に明記した。
  **100MB の Ubuntu がいちばん速い。** 0.6 秒のほとんどは Docker の
  コンテナ生成なので、**軽さを起動時間の速さとして宣伝しない**
- **サイズとアプレット数**（2026-10-11、v3.0.1）:
  Minimal 367 applets / **2.62MB**（arm64 2.98MB）、
  Standard 400 / **2.76MB**（3.13MB）、
  Extended 411 / **2.78MB**（3.17MB）。
  dpkg / dpkg-deb / rpm を外したぶん v3.0.0 より小さい
- **コンテナライフサイクルの実測値**（`docs/benchmarks/lifecycle.md`）。
  `docker run --rm` 696ms / `docker run -d` 556ms / `docker rm` 298ms。
  **`docker stop` は 10,365ms** で、これは Docker が PID 1 に SIGTERM を
  送って 10 秒待つ猶予時間（カーネルは PID 1 のハンドラ無しシグナルを
  無視する）。**Alpine も 10,379ms** で、SIGTERM を扱うプロセスなら
  両者 665ms。イメージの性質ではない
- **`verify-image.sh` に検査を2つ追加**（27 → 29 項目）。
  落としたはずの init スクリプトが復活していないか、
  パッケージマネージャーが入っていないか。どちらも
  「config に書き忘れる」「コピー順を変える」で黙って戻るため
- **Subagent 2つ**: `spec-auditor`（仕様と実装・成果物の突合）、
  `workflow-auditor`（ワークフローが build-arg / 環境変数を渡しているか）。
  2026-10-10 に「CI が緑なのに成果物のメタデータが違う」事故を3件踏んだため

### 移行時の注意

- **`dpkg` / `rpm` が無くなる。** v3.0.0 までのイメージでこれらを
  使っていた場合は動かなくなる。Kimigayo は設計上
  パッケージマネージャーを持たないので、**必要なものはビルド時に
  マルチステージビルドで入れる**（`SPECIFICATION.md` 3.5）

---

## [3.0.0] "Himawari" (向日葵) - 2026-10-10

**このバージョンで初めて、Kimigayo OS は Init が動く OS になった。**
v0.1.0 から v2.0.1 までの公開イメージには OpenRC のバイナリも musl の
`libc.so` も `/tmp` も入っておらず、Init は1つもサービスを起動できなかった。
BusyBox は static-pie で動くため `/bin/sh` は動き、smoke テストは通っていた。

コードネームの運用もここから始まる（体系は
[SPECIFICATION.md](SPECIFICATION.md) の「10.3 リリース名」）。

### 実測値（2026-10-10、macOS / Apple Silicon ホスト）

| バリアント | x86_64 | arm64 | アプレット |
| --- | --- | --- | --- |
| Minimal | **2.65MB** | 3.02MB | 370 |
| Standard | **2.78MB** | 3.16MB | 403 |
| Extended | **2.81MB** | 3.20MB | 413 |

比較（同じホスト・同じ platform で実測）:
`gcr.io/distroless/static-debian12` 2.11MB /
`alpine:latest` 8.42MB / `ubuntu:24.04` 78.2MB。

**6 バリアントすべてが `scripts/verify-image.sh` の 27 項目を通過。**
起動時間とメモリはリリース時点では計測方法に問題があるため未測定だった
（下記）。**2026-10-10 中に計測方法を直して実測した** → [Unreleased]。

### Changed

- **構成要素をまとめて最新化**（約9か月ぶんの滞留を解消）
  - Linux カーネル 6.6.11 → **6.18.55**（LTS。EOL 2027-12 → 2028-12）
  - musl libc 1.2.4 → **1.2.6**
  - BusyBox 1.36.1 → **1.38.0**
  - OpenRC 0.52.1 → **0.63.2**
  - ビルド環境の Alpine 3.23 → **3.24**（LLVM 21 → 22）
- **バージョンを `versions.mk` に集約**（単一の真実の源）。
  以前は `config.mk`・`scripts/download-*.sh`・`scripts/build-*.sh`・
  `scripts/apply-kernel-patches.sh`・`src/kernel/build.py` の5箇所に散り、
  値も一致していなかった
- `Dockerfile` が aarch64 の `.apk` をバージョンごと URL 直打ちしていたのを
  `apk fetch` に変更（Alpine を上げるたび 404 になっていた）
- `Dockerfile` の `/usr/lib/llvm21/...` 直書きを `clang -print-resource-dir` に変更
- `Dockerfile` / `Dockerfile.runtime` / `docker-compose.yml` の Alpine 版と
  プロジェクト版を build arg 化（`ALPINE_VERSION` / `KIMIGAYO_VERSION`）
- `Dockerfile` の `LABEL version` と `org.opencontainers.image.base.name` が
  それぞれ `0.1.0` / `alpine:3.19` のまま実態とずれていたのを修正
- Python のテスト依存を `requirements-dev.txt` に1本化
  （`Dockerfile`・`Makefile`・CI がそれぞれ別に並べていた）
- 外部 GitHub Action の `@master` 参照を tag 固定
  （`trivy-action@v0.36.0`・`action-shellcheck@2.0.0`）
- **README とドキュメントの性能数値を実測値に差し替えた。**
  Standard（x86_64）は **2.78MB**。比較対象も同じホスト・同じ platform で
  測り直した（`gcr.io/distroless/static-debian12` 2.11MB /
  `alpine:latest` 3.24.2 が 8.42MB / `ubuntu:24.04` 78.2MB）。
  **v2.0.1 の 1.17MB は Init も `libc.so` も入っていないイメージの値**なので、
  現在の値と同じものを測った数字ではない
- **起動時間 439ms とメモリ 0.2MB を撤回した。**
  `scripts/benchmark-startup.sh` は `docker run -d <image> sleep 5` の
  終了までを測っており、正常なイメージでは約 5,600ms になる。
  439ms はこの `sleep` が成立しなかった場合の値で、起動時間ではない。
  計測方法を決め直すまで「未測定」と記載する
- 「完全静的リンク・依存関係ゼロ」という記述を実態に合わせた。
  BusyBox は static-pie だが、OpenRC は musl と自身の
  `librc` / `libeinfo` に動的リンクする

### Added

- **`CLAUDE.md`** — Claude Code 向けの作業ルールとプロジェクト固有の勘所
- **`versions.mk`** / `scripts/lib/versions.sh` — 構成要素のバージョンの
  単一の真実の源と、シェル側のローダ
- **`TODO.md`** / **`NEXT.md`** — 手元の作業メモ（`.gitignore` 済み、追跡しない）
- **`requirements-dev.txt`** — 開発・テスト用の Python 依存
- **`.coveragerc`** — カバレッジ設定（`pytest.ini` に書いても効かないため）
- `make print-versions` / `print-kernel` 等 — versions.mk の値を単発で取り出す
- **`src/kernel/patches/README.md`** — 各パッチが存在する理由と、
  版上げ時に当たらなくなったパッケージの扱い
- カーネル tarball の SHA-256 照合（これまで計算して表示するだけだった）
- OpenRC tarball の SHA-256 照合（これまで「展開できたら OK」だった）
- `make show-version` に構成要素のバージョン表示を追加

### Fixed
- **Init（OpenRC）が1つもサービスを起動できなかった。**
  init スクリプトの shebang は `#!/usr/sbin/openrc-run`（OpenRC の prefix が
  `/usr`）だが、rootfs には `/sbin/openrc-run` しか置いていなかったため、
  37 本のうち 36 本が
  `unable to exec '/etc/init.d/<name>': No such file or directory`
  になっていた。`execve(2)` はインタプリタが見つからないとき `ENOENT` を
  返すので、エラーは「スクリプトが無い」と読めるが実際に無いのは
  インタプリタ。ファイルは存在し `rc-update show` も通るため気づけなかった。
  `/usr/sbin` 側にシンボリックリンクを張って解決（サイズ増はほぼゼロ）
- **OpenRC の `sysctl` サービスが毎回失敗していた。**
  上流の init スクリプトは GNU procps を前提に `sysctl --system` を呼ぶが、
  BusyBox の `sysctl` に `--system` は無く
  `/sbin/sysctl: unrecognized option: system` で落ちていた。
  BusyBox の `-p FILE...` に置き換え、**`/etc/sysctl.d/` の設定が初めて
  実際に適用されるようになった**（`--privileged` 付きのコンテナで
  `kernel.pid_max = 32768` / `vm.swappiness = 0` を実測）。
  非特権コンテナでは `/proc/sys` が read-only なので、失敗ではなく
  「ホストの担当」として抜ける。`bootmisc` の `mount --bind` も
  `mount -o bind` に置き換えた
- **arm64 の BusyBox だけ PIE でなく ASLR が効いていなかった**
  （ELF Type=EXEC）。x86_64 は Alpine の gcc が default-PIE なので同じ
  config から DYN (PIE) + BIND_NOW になっており、**片方だけ弱い状態に
  気づけなかった**。musl は static-PIE 用の start file（`rcrt1.o`）を
  持つので両立する。`-fPIE` と `-static-pie` を渡すようにし、
  `-fno-stack-protector` も外した（`__stack_chk_fail` は musl の `libc.a`
  にある）。`CONFIG_PIE` は BusyBox の Kconfig が `depends on !STATIC` に
  しているため使えず、`-static-pie` を `EXTRA_LDFLAGS` に入れると
  `ld -r` の部分リンクにも渡って落ちるので、最終リンクだけに効く
  `CFLAGS_busybox` で渡している
- **`/etc/os-release` が `0.1.0` と名乗っていた**（v1.0.0 / v2.0.1 を
  公開したあとのイメージも同じ）。`/etc/motd`・`/.kimigayo-build-info`・
  `Dockerfile.runtime` の `ARG VERSION` 既定値も `0.1.0` 直書きで、
  `Makefile` は `--build-arg VERSION` を渡していなかった。
  **タグ名だけ合っていて中身のメタデータがずれる**ので `docker images` では
  気づけない。いま版は `git describe` から1箇所で決まり、
  `verify_rootfs` が `/etc/os-release` と突合する
- **カーネルモジュールが arch と版で絞られずコピーされていた** —
  x86_64 / 6.6.11 のモジュールが arm64 の rootfs に入っていた
  （`minimal-arm64` が `standard-arm64` より大きいという不自然な結果で発覚）
- **`release.yml` が `latest-amd64` / `latest-arm64` を更新していなかった** —
  2025-12-21 から公開済みで `docs/RELEASE_CHECKLIST.md` が案内しているのに
  manifest ジョブが作っておらず、何度リリースしても古い内容のままだった
- **`security.yml` の Trivy イメージスキャンが一度も走っていなかった** —
  `if` が `schedule == '0 2 * * *' && ... && schedule == '0 2 * * 0'` という
  自己矛盾した条件になっていた
- **Markdown のリンク切れ 23 件**（`README.md` → 追跡していない `TODO.md` など）。
  `.gitignore` されたファイルは手元に存在するため、ローカルではリンクを
  辿れてしまい気づけない種類だった

- **arm64 の動的リンクバイナリが1つも動かなかった。**
  `/lib/ld-musl-aarch64.so.1`（musl の `libc.so`）自身が `__letf2` を
  解決できず、OpenRC の実行ファイル4つすべてが
  `Error relocating ...: __letf2: symbol not found` で起動しなかった。
  `__letf2` は aarch64 の 128-bit `long double` を扱うコンパイラ
  ランタイム関数で、x86_64 は `long double` が 80-bit でハードウェア
  命令を使うため同じ問題が出ない。BusyBox は static-pie なので
  影響を受けず smoke テストは通っていた。
  `scripts/build-musl.sh` が LDFLAGS に共有の `-lgcc_s` を渡しており、
  静的な `LIBCC` を打ち消していたのが原因。あわせて upstream が付けない
  SONAME（`libc.musl-aarch64.so.1`）を設定し、`libc.so` が自己完結
  していること・`NEEDED` を持たないことを `verify_rootfs` で検証する
- **配布イメージに `/tmp` が無かった**（v0.1.0 以降ずっと）。
  `/run`・`/var/log`・`/var/tmp`・`/var/cache`・`/var/lib`・`/home`・`/opt`・
  `/srv`・`/mnt`・`/media`・`/usr/local/*` も同様で、`/var` には宛先の無い
  `lock -> ../run/lock` と `run -> ../run` だけが残っていた。
  `optimize_rootfs` の `find -type d -empty -delete` が無条件だったため、
  `create_directory_structure` が作り `set_permissions` が 1777 を付けた
  FHS の骨格を、空だからという理由で全部消していた
  （混入は 2025-12-21 の「rootfsサイズ最適化」= v0.1.0 の前日）。
  `/run` が無いと OpenRC が state を書けないため、Init を入れただけでは
  動かない。掃除は残したまま骨格を除外対象にし、`verify_rootfs` に
  必須ディレクトリとスティッキービットの検証を追加した。
  **サイズへの影響はゼロ**（修正前後ともに standard 3.43MB / tarball 1.5MB。
  この数字は 2026-10-09 時点のもので、その後の重複ヘルパの symlink 化で
  2.78MB になった）。
  つまりこの最適化は最初から何も削減していなかった
- **配布イメージに OpenRC のバイナリが1つも入っていなかった**（v0.1.0 以降ずっと）。
  `scripts/build-rootfs.sh` が OpenRC の `usr/sbin` / `usr/lib` を
  コピー対象にしていなかった（OpenRC の prefix は `/usr` なので
  実行ファイル9個と `librc.so.1` / `libeinfo.so.1` はすべてそこに入る）。
  ログは「✓ OpenRC copied」と出ていた。
  加えて `build-rootfs.sh` は musl と BusyBox しかビルド確認していなかったため、
  `make build-rootfs` / `make ci-build-local` の経路では OpenRC が
  そもそもビルドされていなかった
- **musl の `libc.so` が入っておらず、動的リンカがリンク切れだった**
  （v0.1.0 以降ずっと）。`/lib/ld-musl-<arch>.so.1` は
  `/usr/lib/libc.so` を指す絶対シンボリックリンクだが、その実体を
  コピーしていなかった。BusyBox は static-pie なので smoke テストは通り、
  気づけない状態だった。README が案内する「自分のアプリを COPY する」
  使い方はこれで動くようになった
- **OpenRC の `start-stop-daemon` / `supervise-daemon` が
  `libcap.so.2` を解決できず起動しなかった。** OpenRC 0.63.2 は libcap が
  必須で、ランタイムイメージには musl 以外の共有ライブラリを置いていない。
  meson に `--prefer-static` を渡して libcap を静的リンクするようにした
  （Alpine のように `libcap.so.2` を同梱する方針は採らなかった）
- **arm64 の OpenRC 0.63.2 が1度もビルドできていなかった**（CI の arm64
  ジョブ3つが全部これで失敗）。原因が3つ重なっていた。
  (1) Alpine 3.24 の `libcap` は `libcap2` と `libcap-utils` に依存するだけの
  メタパッケージ（`.apk` は 1301 バイトで中身なし）で、`apk fetch` は依存を
  引かないため `libcap.so.2` が sysroot に入っていなかった。`libcap2` を
  取るようにし、コピー失敗を握り潰していた `2>/dev/null || true` も外した。
  (2) `.pc` の `libdir` は `/usr/lib` なので meson は `<sysroot>/usr/lib` を
  見るが、実物は `<sysroot>/lib` にしか無く、`-lcap` がホストの x86_64 の
  `/usr/lib/libcap.so` に流れて `incompatible with aarch64linux` になっていた。
  (3) meson のクロスファイルをビルドディレクトリの中に書いていたため、
  `meson setup` の直前でそのディレクトリを作り直す処理が一緒に消していた
  （`build/openrc-cross-<arch>/` に分離）
- **静的リンクした aarch64 の libcap が outline-atomics を参照していた** —
  `undefined symbol: __aarch64_swp1_acq_rel`。クロスラッパーは `-nostdlib`
  なので compiler-rt の builtins を明示的にリンク末尾へ足すようにした
  （アーカイブをファイルパスで渡すと meson の依存解決が
  `'utf-8' codec can't decode byte` で落ちるため `-l` 形式）
- **カーネル 6.18.55 の x86_64 ビルドが realmode のリンクで落ちていた。**
  `scripts/build-kernel.sh` が `REALMODE_CFLAGS` を丸ごと上書きしており、
  上流の値にある `-D__DISABLE_EXPORTS` が落ちていたため、realmode の
  アセンブリで `RET` が `jmp __x86_return_thunk` に展開され
  `undefined reference to '__x86_return_thunk'` になっていた。
  6.18 では上流の `REALMODE_CFLAGS` が `-std=gnu11` を持つので上書きは不要
- **`make shellcheck-scan` が手元で回らず、警告が出ても成功していた。**
  shellcheck が無い環境では即 exit 1（ビルド環境イメージにも入っていない）、
  かつ `find -exec shellcheck {} \;` で終了コードを捨てていた。
  Docker イメージでの代替と、終了コードの伝播を入れた
- **`scripts/download-busybox.sh` がキャッシュ済み tarball を再利用すると
  必ず落ちていた** — `skip_checksum` と `github_tag_version` が
  ダウンロード分岐の中でしか定義されておらず `set -u` に殺されていた
- **`make version` が `2.0.1` ではなく `list` を返していた** —
  打ち間違いで出来たと思われる `list` タグが `git describe --tags` で
  最新タグとして拾われていた。`--match 'v[0-9]*'` で絞るようにした
- **CI のテストが絶対に落ちなかった** — `|| echo "... not ready yet"` で
  握り潰されていた（522件すべて通るのに意味を失っていた）
- **`dependency-review.yml` のバージョン報告が常に空だった** —
  存在しない `MUSL_VERSION=` を `scripts/build-rootfs.sh` から grep していた。
  ハードコードされた `OpenRC: 0.44+` / `Alpine: edge` も実態とずれていた
- **musl のチェックサム不一致が警告だけで通っていた**のを失敗させるようにした
- `scripts/download-openrc.sh` の第一 URL が全バージョンで 404 だったため
  毎回無駄な取得を試みていたのを修正
- OpenRC 0.63.2 でソース構成が変わった `src/rc/rc.c` → `src/openrc/rc.c` に追従
- `scripts/build-openrc.sh` が渡していた `-Dos=Linux` を除去
  （0.63.2 では上流から削除されており `meson setup` が失敗する）
- `scripts/apply-kernel-patches.sh` が1本も当てていないのに
  「Applied 1 patches successfully」と報告していたのを修正。
  適用／当たらなかった／プレースホルダを分けて数えるようにした
- `build-system/Makefile` の `VERSION := 0.1.0` を git タグ由来に変更
- **`apk fetch --arch aarch64` が署名検証で失敗していた** — Alpine は
  アーキテクチャごとに別の鍵で署名しており、x86_64 のベースイメージには
  x86_64 用の鍵しか入っていない。`--keys-dir /usr/share/apk/keys/aarch64`
  を渡して解決（`--allow-untrusted` は使わず検証を維持）
- **OpenRC 0.63.2 が要求する `libcap` がビルド環境に無かった** —
  0.52.1 では `-Dcapabilities` で無効化できたが、そのオプションごと
  上流から削除され必須になっている。`libcap` / `libcap-dev` を追加し、
  arm64 クロス用には sysroot 側に `libcap.pc` を置いて meson の
  クロスファイルから `pkg_config_libdir` / `sys_root` で指すようにした
- **`pytest.ini` に書いた `[hypothesis]` と `[coverage:*]` が効いていなかった** —
  hypothesis は ini ファイルを読まず、coverage が読むのは
  `.coveragerc` / `setup.cfg` / `tox.ini` / `pyproject.toml` で `pytest.ini` は
  読まない。coverage 設定を `.coveragerc` に移し、hypothesis 設定は
  `tests/conftest.py` のプロファイルに一本化した
- **hypothesis の既定デッドライン 200ms で3件のプロパティテストが
  落ちていた** — `tmp_path` への実ファイル書き込みとサブプロセス起動を
  含むテストが 300-400ms かかるため。ロジックではなく実行速度の問題なので
  プロファイルに `deadline=None` を設定した
- **`datetime.utcnow()` / `utcfromtimestamp()` の非推奨**（Python 3.12 で
  非推奨、将来削除）。`datetime.now(timezone.utc).replace(tzinfo=None)` に
  置き換えた（naive に戻さないと `isoformat()` が `+00:00` を付けて
  末尾 `"Z"` の既存書式が壊れる）
- `tests/conftest.py` の `KIMIGAYO_VERSION = "0.1.0"` を git タグ由来に変更

### Removed

- **カーネルパッチ3本**（`0002-disable-retpoline-realmode`・
  `0003-efi-stub-std-gnu11`・`0004-x86-boot-compressed-std-gnu11`）。
  いずれも GCC 15 で 6.6 系をビルドするための `-std=gnu11` 回避策で、
  6.18 では上流が取り込み済み
- `Dockerfile` から Rust ツールチェイン（rustup）のインストール。
  対象だった `isn` パッケージマネージャ（`src/pkg/`）は v0.1.1 で削除済みで、
  `cargo` を参照するコードもビルド経路も残っていなかった
- `config.mk` の死んでいた `ISN_VERSION`
- Git 管理下にあった `.hypothesis/` のキャッシュ59ファイルと
  `benchmark-optimized.log`（`.gitignore` に追加）
- **CI からカーネルビルドを完全に外した。** 成果物は rootfs だけを詰めた
  Docker イメージで**カーネルはイメージに入らない**（コンテナはホストの
  カーネルで動く）ため、CI が毎回ビルドしてもイメージの中身は1バイトも
  変わらないのに 1 run あたり数十分かかっていた。想定する使い方も
  VPS 上の Docker コンテナなので、組み込み・ベアメタル起動は対象外とした。
  `make kernel` と `manual-build.yml` の `build_kernel=true` は残してある
- **`.kiro/specs/kimigayo-os-core/`**（`requirements.md` / `design.md` /
  `tasks.md`）。18 箇所の参照を `SPECIFICATION.md` と
  `docs/developer/ARCHITECTURE.md` に向け直した
- **`src/kernel/patches/0001-security-hardening.patch`** — 中身がコメント
  だけのプレースホルダで、毎ビルド「適用できないパッチ」として警告を
  出すだけだった。0 件のときに再生成する処理も外した（消しても次の
  ビルドで復活していた）
- **OpenRC の重複ヘルパ 39 ファイル**をシンボリックリンクに置き換えた
  （実測 816KB 削減）。上流の meson が `argv[0]` で分岐する1つの
  プログラムを名前ごとの実コピーで install するため。
  判定は名前のリストではなく**内容（md5）**で行うので、OpenRC を
  上げてヘルパが増えても追従する

---

## [2.0.1] - 2026-01-16

ビルド成果物とリリース経路の安定化。v1.0.0 から 70 コミット。
（`v2.0.0` タグは存在せず 1.0.0 → 2.0.1 となっている）

### Fixed

- BusyBox が動的リンクされ musl ランタイム不在で起動できない問題を解消
  （ARM64 で `-nostdlib` により CRT が落ちていた。
  詳細 → [docs/troubleshooting/busybox-static-linking.md](docs/troubleshooting/busybox-static-linking.md)）
- ARM64 の compiler-rt builtins の解決（`-rtlib=compiler-rt`）
- `release.yml` の rootfs ビルドコマンドとスクリプトパスの修正

### Changed

- ベンチマーク結果と `PERFORMANCE_TUNING.md` を v2.0.1 実測値へ更新
- README に Docker Hub リンクとバッジを追加

詳細は `git log v1.0.0..v2.0.1`。

---

## [1.0.0] - 2026-01-02

初の安定版リリース。v0.1.1 から 175 コミット。

### Added

- リリースノートの自動生成（前回タグからの PR 一覧）
- Discord 通知
- マルチアーキテクチャ対応の整備（x86_64 / arm64）

### Changed

- Docker Hub のタグ命名を `{version}-{variant}-{arch}` 形式に統一
- GitHub Advanced Security 対応として各ワークフローに `permissions` を明示

### Fixed

- `/etc/shadow` のパーミッションエラー
- Release ワークフローの artifact ダウンロード範囲を `kimigayo-*` に限定

詳細は `git log v0.1.1..v1.0.0`。

---

## [0.1.1] - 2025-12-22

**設計思想を Alpine 寄りから distroless 寄りへ移行。** v0.1.0 から 17 コミット。

### Removed

- **`isn` パッケージマネージャーを完全削除。**
  パッケージマネージャーを持たないこと自体を設計の中心に据え直した

### Changed

- ビルドステップ番号の整理（`Makefile` / `build-system/Makefile`）

詳細は `git log v0.1.0..v0.1.1`。


## [0.1.0] - 2025-12-21

### Added
- rootfsサイズ最適化を実装
- 個別コンポーネントのクリーンターゲットを追加
- ビルドマイルストーン表示とOpenRC検証修正
- make cleanに詳細な進捗表示を追加
- カーネルビルドの進捗表示を改善
- Makefileのhelpを視覚的に改善
- make infoコマンドを追加
- プロジェクトrootのMakefileに`make build`を追加
- OpenRCベースのInitシステムを実装 (タスク5.1, 5.2)

### Changed
- 組み込み関連の記述を削除しコンテナ向けOSであることを明記
- Makefileを再構成してDocker管理用の簡易コマンドを追加

### Fixed
- rootfs最適化の算術式エラーを修正
- OpenRCインストール検証でlib/rcディレクトリを追加
- カーネルソース抽出の検証を強化
- カーネルパッチ検証時のパス解決を修正
- make cleanでダウンロードキャッシュを保持するように修正
- ビルドスクリプトのパス解決を修正
- カーネルソースツリーのクリーニングを追加
- カーネルビルドの対話的プロンプトを回避して進捗表示を改善
- Docker Composeにplatform: linux/amd64を追加
- Alpine Linuxのgcc向けに-m64フラグを削除
- OpenRC brandingをスペースなしの単一単語に修正
- OpenRC brandingの文字列エスケープを修正
- BusyBox設定ファイルのパス解決を修正
- Fix SIGPIPE error (141) in musl build verification
- Fix musl-gcc wrapper creation and summary errors
- Fix libc.so verification path detection
- Fix binutils tools detection for musl build
- Fix C compiler detection for x86_64 musl build
- Improve error handling in musl build script
- Fix wget timeout error in ARM64 toolchain download
- PyYAMLをDockerfileに追加してimportエラーを修正
- FilesystemManagerのパス正規化を修正
- 統合テストのAttributeErrorを修正し、Phase 1を完了
- 統合テストのインポートエラーを修正
- モックバイナリのサイズ計算エラーを修正
- test_utility_add_removeのロジックエラーを修正

### Security
- Task 28にセキュリティ監査とペネトレーションテスト項目を統合
- セキュリティドキュメントから報奨金プログラムの記載を削除
- ランタイムセキュリティ強制を実装
- パッケージセキュリティ検証機能を実装 (タスク6.4, 6.5, 6.6)
- サービスセキュリティ機能を実装 (タスク5.3, 5.4)

### Documentation
- Docker Hub README構成を改善
- Phase 8以降をDocker Hub公開向けに修正
- README.mdにトラブルシューティングセクションを追加
- README.mdのビルド手順を新しいMakefileに合わせて更新
- ビルドログ確認手順を追加
- Docker volumeの削除コマンドを修正
- Add OpenRC init scripts and service definitions
- ドキュメントから「実装予定」「計画中」の記載を削除
- README.mdの「作成予定」表記を削除
- README.mdにドキュメントセクションを拡充
- README.mdにユーザー向けドキュメントへのリンクを追加
- Ed25519署名検証機能をドキュメントに追加
- エラーハンドリングとログ機能を実装 (タスク5.5, 5.6)
- タスク2.1と2.2を完了としてマーク
- 包括的なREADME.mdを作成
- spec.mdをSPECIFICATION.mdにリネーム

### Build/CI
- ビルドシステムとプロジェクト構造を追加


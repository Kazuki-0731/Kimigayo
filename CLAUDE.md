# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**このファイルが作業ルールの正本。** 変更したらここを更新し、他のファイルに
重複させない。Claude Code 固有の設定は `.claude/`（`.gitignore` 済み、
機密を含むため共有しない）。

---

## このプロジェクトは何か

**Kimigayo OS** — Google の distroless と Alpine Linux の設計思想を組み合わせた、
**コンテナ向けの軽量 OS**。パッケージマネージャーを意図的に持たない不変インフラ。

- **成果物は Docker イメージ**（`ishinokazuki/kimigayo-os`）。rootfs だけを詰めた
  イメージで、**カーネルはイメージに入らない**（コンテナはホストのカーネルで動く）。
  カーネルをビルドするのはベアメタル／QEMU 検証のため
- **バリアント 3 種**（minimal / standard / extended）× **アーキテクチャ 2 種**（x86_64 / arm64）
- **実績値**（v2.0.1）: Standard 1.17MB / 起動 439ms / メモリ 0.2MB
- 構成要素: **musl libc**（C ライブラリ）/ **Linux カーネル**（強化版）/
  **BusyBox**（コアユーティリティ）/ **OpenRC**（Init）

詳細は [README.md](README.md)・[SPECIFICATION.md](SPECIFICATION.md)・
[docs/developer/ARCHITECTURE.md](docs/developer/ARCHITECTURE.md)。
要求・設計・タスクは [.kiro/specs/kimigayo-os-core/](.kiro/specs/kimigayo-os-core/)。

---

## ミスを繰り返さない（自己成長ルール）

**ユーザーとの会話でミス・不具合が見つかったら、二度と同じ失敗をしないよう
記憶し、仕組み化する。** 手段は**それぞれの特徴を踏まえて適材適所で選ぶ**。
1つの形式に決め打ちしない（何でも Hook 化すると毎回の警告がノイズになるし、
何でも Memory 化しても関連度が低ければ読み込まれず効果が出ない）。

- **Memory** — 会話をまたいで持ち越したい文脈・経緯向き（人物像・プロジェクトの
  背景・検証済みの判断）。関連度で読み込まれるかが決まるので、**毎回必ず守って
  ほしい確定ルール**には向かない
- **この `CLAUDE.md` のルール化** — セッション開始時に必ず読まれる。恒常的な
  方針・行動規範向き。増やしすぎると全体が長くなり「今読むべき所」が埋もれるので、
  頻度・重要度が高いものに絞る
- **手順化**（`docs/` 配下への文書化） — 頻度は低いが型が決まっている作業向き。
  このリポジトリは既に `docs/developer/BUILD_GUIDE.md`・`docs/troubleshooting/`・
  `docs/maintainer/MAINTENANCE_SCHEDULE.md` を持っている。**同じ罠を踏んだら、
  会話で説明せず該当ドキュメントに追記する**
- **Hook 化** — 人間の判断を介さず機械的に検知・強制できるもの向き
  （破壊的 git 操作の遮断、コミット漏れの検知）。判断や例外が多いミスを
  Hook 化すると誤検知や毎回の警告でノイズになる
- **Skills 化** — 判断・解釈を伴う複雑な手順で、必要な場面だけ明示的に
  呼び出したいもの向き
- **Subagent 化** — 繰り返し行う監視・検算など、役割とツールを絞って独立に
  任せたいタスク向き。担当を限定できる分モデルコストも絞れる
- **既存の専門家の定義を更新する** — その作業を担当する Subagent / Skill が既に
  あるなら、**そこに書かないと届かない**。メインが学んだだけでは、次に同じ作業を
  任された専門家が同じ罠を踏む。**「自分は知っているから大丈夫」は、委譲する
  運用では成立しない**
- **回帰テスト化**（テストコードに落とす） — コードのバグ・境界値の誤りは、
  直した箇所を壊すテストケースとして残す。ドキュメントや Memory より機械的な
  強制力がある（次に同じ間違いをすれば `pytest` が落ちて教えてくれる）。
  このリポジトリは `tests/unit/`・`tests/property/` が整っているので、
  **コードレベルのミスは第一候補がこれ**
- **CI に落とす**（`.github/workflows/`） — ローカルでは気づけず、PR の時点で
  止めたいもの向き（シェルスクリプトの構文、脆弱性、バージョンの乖離）

### 手段の選び方 — 判断が絡まないミスは文章にしない

> **人の判断が絡まないミス（突合漏れ・転記ミス・仕様の見落とし）は、文章にしない。
> 構造かチェックにする。文章は「判断・解釈が要ること」だけに使う。**

- **文章のルールは「その瞬間に思い出せたときだけ」発火する。** 30 ターン目に
  報告を書いているとき、セッション冒頭に読んだ文章は背景に沈む
- **構造を変える ＞ 機械チェック ＞ 文章** の順に検討する。上 2 つが取れない
  ときだけ文章にする

> このリポジトリでの実例（2026-10-09）: コンポーネントのバージョンが
> `config.mk`・`scripts/download-*.sh`・`scripts/build-*.sh`・
> `scripts/apply-kernel-patches.sh`・`src/kernel/build.py` の**5 箇所に
> 散っていた**。「更新するときは全部直す」と文章で書いても必ず漏れるので、
> [versions.mk](versions.mk) に**単一の真実の源**を作って各スクリプトが
> 読む構造にした（→「バージョンの単一の真実の源」節）。

---

## 会話の応答は日本語で行う

**ユーザーへの応答は原則日本語で書く。** ユーザーが明示的に英語等を求めない限り、
要約・進捗報告・説明を含めすべて日本語にする。作業内容が英語圏由来
（ビルドログ・コンパイルエラー・コミット差分の引用等）でも、それを説明する
地の文は日本語にする。

**コード・スクリプト内のコメントとログメッセージは既存の流儀に合わせる。**
このリポジトリは `scripts/` が英語ログ（`log_info "Downloading..."`）、
`Makefile` の `help` と `docs/` が日本語という混在状態。**新しく書くときは
そのファイルの周囲に合わせ、勝手に統一しない。**

## ユーザー（石野）も間違えることがある

**ユーザー自身も、指示の内容やこれまでの経緯を勘違いしたり忘れたりする
ことがある。** コード・`git log`・ドキュメント・`.kiro/specs/`・過去のルール
（この `CLAUDE.md`・Memory）と食い違う指示や発言を受けたら、黙って従わず、
根拠となる情報源を示した上で聞き返す・指摘する。ユーザーの発言だからといって
無条件に正しいとは限らない。**この確認作業自体が、ユーザー自身のヒューマン
エラーを防ぐための仕組みである。**

**とくにこのリポジトリで食い違いが起きやすい箇所:**

- **バージョン番号。** README は v2.0.1 の実績を書き、`git tag` も `v2.0.1` まで
  あるのに、`CHANGELOG.md` は 0.1.0 止まり・`Dockerfile` の `LABEL version` は
  `0.1.0` のままだった（2026-10-09 に突合して修正）。**「今のバージョンは？」は
  `git describe --tags` と [versions.mk](versions.mk) を見て答える**
- **ベンチマークの数値。** README・`docs/benchmarks/`・`PERFORMANCE_TUNING.md` に
  それぞれ数値がある。**どの版・どのホストで測ったかを確認せずに引用しない**

---

## 指示の範囲を超えない

**プロンプトで指示された範囲を超えることをする前に、必ず提案して承認を得る。**
勝手にやらない。良かれと思ってでもやらない。

まず依頼を次のどれかに分類し、**「やること」だけを実行する。**
「提案に留めること」に該当したら、実行せずに『〜しましょうか』と聞く。

### 質問

「〜は何ですか」「どうなっていますか」「〜でしたっけ」

| やること | 提案に留めること |
| --- | --- |
| 答える | **ファイルの作成・変更・削除** |
| 事実確認のための読み取り（Read / grep / `git status` / `git log`） | **コミット・push** |
| 必要なら根拠を示す | **見つけた問題の修正・片付け** |

**答えて終わり。** 質問の過程で問題を見つけたら、報告はするが直さない。

### 調査

「調べて」「使えるか確認して」「比較して」

| やること | 提案に留めること |
| --- | --- |
| 調べて報告する | **調査で見つけた問題の修正** |
| 読み取り・Web 取得・計測・実測 | **設定ファイル・バージョンの変更** |
| 判断材料を並べる | **`apk add` などの依存追加** |

**調査のための実行が、動いているビルドと競合しないか先に確認する。**
ビルドコンテナは `kimigayo-build-env` という固定名なので、
`docker ps` で走っているものを確認してから叩く。

### 設計

「設計書を書いて」「仕様に落として」

| やること | 提案に留めること |
| --- | --- |
| `.kiro/specs/`・`docs/` 配下の作成・更新 | **実装（コードを書く）** |
| 設計に必要な調査・実測 | **既存コードの変更** |
| ドキュメントどうしのリンク整合 | **設計方針そのものの変更**（既存の決定を覆す場合） |

### 開発

「実装して」「作って」「直して」

| やること | 提案に留めること |
| --- | --- |
| 実装・テスト・コミット | **構成要素のバージョン変更**（musl / カーネル / BusyBox / OpenRC / Alpine） |
| 実装に必然的に伴うもの（テスト、docstring） | **カーネル config・BusyBox config の項目追加** |
| 実装中に見つけた自分のバグの修正 | **セキュリティ強化フラグの緩和**（`-Werror` を外す等） |
| | **スコープの拡大**（頼まれていない機能） |

**「ついでに直しておきました」をやらない。** 見つけたら報告して指示を待つ。

**とくに `-Wno-error` や `|| true` を足して通すのは「直した」ではない。**
`scripts/build-kernel.sh` には既に `KCFLAGS="-std=gnu11 -Wno-error"` や
`2>&1 || true` が入っている箇所がある。**既にあるからといって増やしてよい
理由にはならない。** エラーを黙らせる変更は必ず提案に留める。

### ビルド・計測

「ビルドして」「測って」「ベンチマーク取って」

| やること | 提案に留めること |
| --- | --- |
| ビルド・計測・報告 | **結果を受けた config 変更・最適化** |
| 数字の解釈を添える | **結果を受けた目標値の書き換え** |
| 測定条件（ホスト・arch・バリアント・版）を明示する | **README・docs の数値の更新**（→「数値を出したら反映まで」節） |

**時間がかかる実行は、所要時間の見込みを先に伝える。**
カーネルのフルビルドは数十分〜数時間かかる（→「ビルドの現実的な制約」節）。

### 実行・運用・リリース

「走らせて」「止めて」「出して」

| やること | 提案に留めること |
| --- | --- |
| 指定されたものを実行・停止 | **パラメータを勝手に変える** |
| 進捗の監視と報告 | **タグを打つ・Docker Hub へ push する** |
| 明らかな異常の検知と報告 | **失敗したときの作戦変更** |

**`git tag v*.*.*` は push した瞬間に `release.yml` が走り、Docker Hub の
`latest` を含む公開イメージを差し替える。** タグ・push・リリースは
**毎回ユーザーの明示的な承認を取る**（→「Git の運用ルール」節）。

### その他 / 判断がつかないとき

**迷ったら実行しない。聞く。**

「これは指示に含まれるか？」と一瞬でも思ったら、それは含まれていない。

### 例外（提案なしでやってよいこと）

- **情報を読むだけ**の操作（ファイル閲覧・検索・`git log` 等）
- **指示された作業を完了させるのに不可避**なもの
  （実装を頼まれたらテストを書く、ドキュメントを書いたらリンクを繋ぐ）
- **自分が今回のセッションで壊したもの**の修復
- **危険を止める**操作（暴走しているビルドの停止など）。ただし事後に必ず報告する

### 提案のしかた

長々と説明しない。**何をしたいか・なぜか・影響**を3行で書き、指示を待つ。

```
〜という問題が見つかりました（事実）
〜すれば直りますが、〜に影響します（対処と影響）
やりますか？
```

---

## 次・残り・追加提案を都度示す

**ユーザーは会話の途中で決めたこと・保留にしたことを忘れやすいと自認している。**
作業の区切り（実装完了・調査完了・ビルド完了）ごとに、聞かれなくても次の3点を
短く示す:

1. **次にやるべきこと** — 今すぐ着手できる直近の一手
2. **残っていること** — 判断待ち・保留中のタスク（[TODO.md](TODO.md)・
   [NEXT.md](NEXT.md) の未消化項目、会話中で「後で」と保留したもの）
3. **追加でやった方がいいこと** — 頼まれていないが気づいた改善点。
   **提案に留め、指示なく実行しない**（→「指示の範囲を超えない」節）

**箇条書き数行に収める。** 経緯の再説明はしない。すでに直前の応答で言った内容を
繰り返さず、まだ言っていない「次」だけを書く。

## 目安の無い指示は、一度の変更で様子見せず先に聞く

**「軽くして」「速くして」「縮めて」「増やして」のように、具体的な目安が無い指示を
受けたら、変更する前に目安を聞く。** 一度変えて様子を見ると、往復が増えて
ユーザーの時間を奪う。

**このリポジトリでは数値で表されるものが多く、全部これに当たる:**
イメージサイズの目標、起動時間の目標、カーネル config の項目、BusyBox の
有効コマンド数、`BUILD_JOBS`、リソース制限（`docker-compose.yml` の memory/cpus）、
ベンチマークの試行回数。

## 削除指示を受けたら

**「消して」「削除して」と明示的に指示されても、即座には消さない。**
先に「本当に削除してよいのか・削除しても復活できるのか・再利用性はないのか」を
考え、疑わしければ実行前にユーザーに再確認する。

判断基準:

- **いつでも即座に再現できる** → 確認不要、指示どおり削除してよい。
  `build/`・`output/`・`build/downloads/`（再ダウンロードで戻る）、
  Docker イメージ、`.pytest_cache/`・`.hypothesis/`
- **復元できない／再現に時間や費用がかかる** → 疑ってかかる。中身を確認し、
  再利用の余地があれば先にユーザーに提示してから判断を仰ぐ。該当するもの:
  - **`src/kernel/patches/`・`src/busybox/patches/`** — 過去のビルド失敗から
    手で作ったパッチ。消すと同じ失敗をゼロから調べ直すことになる
    （→「パッチはなぜ存在するか」節）
  - **`src/kernel/config/`・`src/busybox/config/`** — 項目ごとの取捨選択が
    実測の結果。`defconfig` から作り直せない
  - **`benchmark-results/`・`docs/benchmarks/`** — 過去の版の実測値。
    測り直すには同じホスト・同じ版が必要で、事実上再現できない
  - **`.env`** — Docker Hub のアクセストークンが入っている

**`make clean-all` は `build/downloads/` のキャッシュまで消し、
カーネル・musl・BusyBox・OpenRC の再ダウンロード（約 150MB）とフルビルドを
招く。** 「クリーンして」と言われたら、`clean`（成果物のみ）/ `clean-cache`
（ダウンロードのみ）/ `clean-all`（全部）のどれかを確認する。

## データ取得は自力で行う

**「相手が決める値」は変わる。** 上流のバージョン・チェックサム・EOL 日・
CVE 情報・Alpine のパッケージ版は、コードやドキュメントに書いてある値は
**書いた時点のスナップショット**でしかない。**判断に使う前に、現在の値を確認する。**

**ユーザーに「ページを開いて数値を貼ってください」と手動取得を頼まない。**
自分で取得する。このリポジトリで必要になる取得元は決まっている:

| 欲しいもの | 取得元 |
| --- | --- |
| カーネルの最新版・LTS・EOL | `curl -s https://www.kernel.org/releases.json`／`https://www.kernel.org/category/releases.html` |
| カーネルのチェックサム | `https://cdn.kernel.org/pub/linux/kernel/v6.x/sha256sums.asc` |
| BusyBox の最新版・チェックサム | `https://busybox.net/downloads/`／`busybox-<ver>.tar.bz2.sha256` |
| musl の最新版 | `https://musl.libc.org/releases.html` |
| OpenRC の最新版 | Alpine aports の `main/openrc/APKBUILD` の `pkgver` |
| Alpine の最新版 | `https://alpinelinux.org/releases/` |

- **チェックサムは必ず上流の公開値と突合してから書く。** 自分でダウンロードして
  `shasum` を取っただけでは「ダウンロードしたものと同じ」しか言えない。
  musl と OpenRC は公式の SHA256 一覧を出していないので、
  **Alpine aports の `sha512sums` と突合する**（2026-10-09 の更新ではこの方法で
  musl 1.2.6 と OpenRC 0.63.2 を検証した）
- **OpenRC の tarball は GitHub の自動生成アーカイブ**（`archive/refs/tags/<ver>.tar.gz`）。
  `releases/download/...` は**全バージョンで 404**（実測）。自動生成アーカイブは
  理論上バイト列が変わりうるので、チェックサムが合わなくなったら
  改竄ではなく再生成の可能性も疑い、aports と突合する

---

## バージョンの単一の真実の源

**構成要素のバージョンは [versions.mk](versions.mk) にしかない。**
`Makefile`・`config.mk` は `include` し、`scripts/*.sh` は冒頭で読み込む。

```makefile
KERNEL_VERSION  ?= 6.18.55   # LTS, EOL 2028-12
MUSL_VERSION    ?= 1.2.6
BUSYBOX_VERSION ?= 1.38.0
OPENRC_VERSION  ?= 0.63.2
ALPINE_VERSION  ?= 3.24
```

- **バージョンを上げるときは `versions.mk` だけを変える。**
  他の場所に数字を書かない。書いたら次の更新で必ず漏れる
- **同じターンでチェックサムも更新する**（`scripts/download-*.sh` の
  チェックサム表）。チェックサムが無いバージョンは警告だけ出して通ってしまうので、
  **「警告が出たまま」を放置しない**
- 上げたら `docs/` と `README.md` のバージョン表記も突合する
  （→「数値を出したら反映まで」節）

> 2026-10-09 以前は 5 箇所に散っていた（`config.mk` は `6.6`、
> `scripts/download-kernel.sh` は `6.6.11`、`scripts/build-kernel.sh` は `6.6.11`、
> `scripts/apply-kernel-patches.sh` は `6.6.11`、`src/kernel/build.py` の
> `KernelVersion` enum は `"6.6"`）。`.github/workflows/dependency-review.yml` には
> さらに古い `OpenRC: 0.44` が残っていた。

---

## ビルドの全体像

```
versions.mk ─┬→ download-musl    → build-musl     [1/4]
             ├→ download-kernel  → apply-kernel-patches → build-kernel  [2/4]
             ├→ download-busybox → apply-busybox-patches → build-busybox [3/4]
             └→ download-openrc  → build-openrc   [4/4]
                                        ↓
                              build-rootfs.sh（build/rootfs/）
                                        ↓
                        package-rootfs（output/*.tar.gz）
                                        ↓
                    Dockerfile.runtime → Docker イメージ → smoke test
```

**よく使うコマンド**（全量は `make help`）:

```bash
make docker-build          # ビルド環境イメージを構築（Alpine ベース）
make shell                 # ビルドコンテナに入る（推奨。リアルタイム出力が見える）
make build                 # コンテナ内で OS をビルド [1/4]〜[4/4]
make status                # どこまで完了したか確認
make info                  # ビルド設定を表示

make ci-build-local        # rootfs → 統合テスト → イメージ → smoke（GitHub Actions 相当）
make test                  # pytest
make security-scan         # Trivy + ShellCheck
make benchmark             # 全ベンチマーク
```

- **設定の優先順位は コマンドライン > `.env` > デフォルト。**
  `cp .env.example .env` して使う。`.env` は `.gitignore` 済み
  （`DOCKER_HUB_ACCESS_TOKEN` が入るため**絶対にコミットしない**）
- **`make build` はホストではなくコンテナ内で走る**
  （`docker compose run --rm kimigayo-build make build`）。
  一方 **`make ci-build-local` はホスト側で `scripts/build-rootfs.sh` を直接叩く**。
  rootfs 作成は `build/` に musl・BusyBox・OpenRC のビルド結果が既にあることを
  前提にしているので、**先に `make build` を通しておくこと**
- **長いビルドは `make shell` → `tmux` 内で回す。** `make build` を
  そのまま叩くと出力が溜まってから出るため進捗が見えない

### ビルドの現実的な制約

- **`docker-compose.yml` は `platform: linux/amd64` を固定している。**
  開発機が Apple Silicon（arm64）だと **QEMU エミュレーションになる**。
  musl・BusyBox・OpenRC は許容範囲だが、**カーネルのフルビルドは非現実的**
  （数時間〜、失敗もする）。**カーネルの検証は GitHub Actions
  （`ci.yml` の matrix: variant × arch）に任せる**のが既定
- **Docker イメージにカーネルは入らない。** rootfs だけなので、
  musl / BusyBox / OpenRC の変更は `make ci-build-local` で検証できる。
  **「イメージが動いた」はカーネルを検証したことにならない**
- ダウンロードキャッシュは named volume `kimigayo-downloads` に永続化される。
  バージョンを上げたら新しい tarball を取り直すだけで、古いものは残る

### パッチはなぜ存在するか

**パッチを消す・足す前に、なぜ存在するかを調べる**（→「判断を仰ぐ前に、
その対象がなぜ存在するかを調べる」節）。

| パッチ | 理由 |
| --- | --- |
| `src/busybox/patches/0001-vi-musl-libc-compatibility.patch` | BusyBox の `editors/vi.c` が glibc の GNU 正規表現拡張（`re_syntax_options`・`re_compile_pattern`・`re_search`）を使っており musl ではコンパイルできない。POSIX `regcomp`/`regexec` に書き換えている。**1.38.0 でも上流は GNU 拡張のまま**なので引き続き必要（2026-10-09 に 1.38.0 への適用を dry-run で確認）。詳細 → [docs/development/busybox-vi-patch.md](docs/development/busybox-vi-patch.md) |
| `src/kernel/patches/0001-security-hardening.patch` | **中身はコメントだけのプレースホルダ。** 実パッチではない |

**削除済みのパッチ（2026-10-09、カーネル 6.6 → 6.18 で不要になった）:**
`0002-disable-retpoline-realmode.patch`・`0003-efi-stub-std-gnu11.patch`・
`0004-x86-boot-compressed-std-gnu11.patch` はいずれも **GCC 15 で 6.6 系を
ビルドするための `-std=gnu11` 回避策**だった。6.18 では上流が取り込んでいる
（`arch/x86/Makefile` の `REALMODE_CFLAGS := -std=gnu11 ...`、
`drivers/firmware/efi/libstub/Makefile` の `cflags-$(CONFIG_X86) += ... -std=gnu11`、
`arch/x86/boot/compressed/Makefile` の `KBUILD_CFLAGS += -std=gnu11`）。

> **`scripts/apply-kernel-patches.sh` は `patch -p1 --dry-run` が通らないパッチを
> `log_warn` して `return 0` する。つまり当たらないパッチは黙ってスキップされ、
> ビルドは成功したように見える。** バージョンを上げたら
> **`build/kernel-patches.log` を必ず読み、「not applicable」が出ていないか確認する。**
> 効かなくなったパッチは、不要になったのか・当て直しが必要なのかを判断して
> 消すか作り直す。放置すると「適用されているつもり」のまま進む。
> 同じことが `scripts/apply-busybox-patches.sh`（`build/busybox-patches.log`）にも言える。

### 版上げで実際に壊れた箇所（前例）

**上流のビルドオプションは消える。** 2026-10-09 の OpenRC 0.52.1 → 0.63.2 で、
`scripts/build-openrc.sh` が渡していた **`-Dos=Linux` が上流から削除されており、
`meson setup` が "Unknown options" で失敗する**状態だった（0.52.1 → 0.63.2 で
`os`・`capabilities`・`rootprefix`・`split-usr`・`termcap` が消えている）。

- **meson / Kconfig を使う構成要素を上げるときは、オプションの存在を先に突合する。**
  OpenRC なら `meson_options.txt`、BusyBox なら `make oldconfig` の差分、
  カーネルなら `make olddefconfig` の出力
- **`NEWS.md`・`Changelog` を読む。** OpenRC 0.62 では `ready` → `notify` の
  リネームとキャッシュ位置の変更（`libexec` → `/var/cache/rc`）があった
  （このリポジトリの `src/openrc/init.d/`・`configs/openrc/rc.conf` は
  どちらも使っていないので影響なしと確認済み）

---

## テスト

```bash
make test                      # コンテナ内で pytest
python3 -m pytest tests/unit -q          # 単体（269 件）
python3 -m pytest tests/property -q      # プロパティ（hypothesis、253 件）
python3 -m pytest -m "not slow" -q       # 遅いものを除く
pip install -r requirements-dev.txt      # pytest / hypothesis 等
```

- **マーカーは `pytest.ini` に定義済み**（`unit`・`property`・`integration`・
  `slow`・`security`）。`--strict-markers` なので**未定義のマーカーを使うと落ちる**。
  新しいマーカーを使うなら `pytest.ini` に足す
- **プロパティテストは `hypothesis`。** 反例は `.hypothesis/examples/` に
  キャッシュされるが**これは Git 管理下に置かない**
  （2026-10-09 に 59 ファイルを追跡から外した）
- `tests/integration/` の `.sh` は実際に Docker を叩く。
  `test_docker_startup.sh`・`test_functionality.sh` はイメージが必要
- **CI のテストを `|| echo "... not ready yet"` で握り潰さない。**
  2026-10-09 まで `build-workflow.yml`・`release.yml`・`Makefile` の
  `test-integration` がこの形になっていて、**522 件すべて通るのに CI では
  絶対に落ちない**状態だった。テストが落ちたら CI は落ちるべき

---

## セキュリティ

- **コンパイル時の強化フラグは `config.mk` に集約**（`-fPIE`・
  `-fstack-protector-strong`・`-D_FORTIFY_SOURCE=2`・`-Wl,-z,relro,now,noexecstack`）。
  **緩めるのは提案に留める**（→「指示の範囲を超えない」節）
- `make security-scan` = Trivy（イメージ）+ Trivy（ファイルシステム）+ ShellCheck
- `.github/workflows/security.yml` が毎日 02:00 UTC に走り、
  `base-image-update.yml` が毎週月曜に上流の版を確認する。
  **これらが作る PR / Issue は「上流が動いた」という一次情報**なので、
  バージョン更新の起点として先に見る
- **外部 Action は tag で固定する。** `@master` 参照は供給網のリスクかつ
  再現性がない（2026-10-09 に `trivy-action`・`action-shellcheck` を固定した）
- 脆弱性の報告・運用は [docs/security/](docs/security/) 配下
  （`SECURITY_POLICY.md`・`VULNERABILITY_REPORTING.md`・`HARDENING_GUIDE.md`）

**機密を書かない。** `.env`（Docker Hub トークン）・`.claude/` は `.gitignore` 済み。
`CLAUDE.md`・`docs/`・コミットメッセージに API キー・トークン・個人のパスを書かない。

---

## 数値を出したら反映まで

**ベンチマークを取って報告して終わりにしない。** 計測は、次のどれかに
着地させるまでが1セット。着地先が無い計測は、同じことを半年後にもう一度
測り直すだけで、時間の無駄。

| 着地先 | 何をするか |
| --- | --- |
| **ドキュメントに反映する** | `README.md` のパフォーマンス実績表、`docs/benchmarks/`、`docs/developer/PERFORMANCE_ANALYSIS.md`・`PERFORMANCE_TUNING.md` |
| **config に活かす** | カーネル config・BusyBox config・`configs/sysctl/`・`configs/openrc/` の項目を実際に変える（または**外す**） |
| **CI に落とす** | 退行を検知したいならワークフローか回帰テストにする |
| **仕組みにする** | ルール化・Hook 化・回帰テスト化（→「ミスを繰り返さない」節） |

- **「着地先なし」も結論として明示的に選べる。** ただしその場合は
  **なぜ活かせないのか・何が揃えば活かせるのか**を書き残す
- **測定条件を必ず添える**（ホストの arch・バリアント・バージョン・試行回数）。
  開発機は arm64 で `docker-compose.yml` は amd64 を強制するため、
  **ローカルの計測値は CI と直接比較できない**
- **数値を更新するときは、README とベンチマークドキュメントを同じターンで突合する。**
  片方だけ直すと、次に「どっちが正しいのか」を調べ直すことになる

## 調査・判断を仰ぐ前に、その対象がなぜ存在するかを調べる

**設定・パッチ・config 項目・スクリプトの現状を見て「これはおかしいので
直しますか？」と聞く前に、「なぜ今そうなっているか」を記録で調べる。
理由が分かると、質問そのものが消えることがある。**

- **パッチなら** → `docs/development/`・`docs/troubleshooting/`、
  パッチ冒頭のコメント、`git log --follow <patch>`
- **設定値なら** → `git log -S '<値>'` で入った経緯を辿る
- **ビルドの回避策なら** → `docs/troubleshooting/` に症状と原因が書かれている
  ことが多い（例: ARM64 で `-nostdlib` を使うと CRT が落ちて動的リンクになる、
  という既知の罠は `busybox-static-linking.md` にある）
- **「異常だ」と書く前に、それが仕様でないかを確かめる。**
  パッケージマネージャーが無いのは**意図した設計**であって欠落ではない
- **調べた理由は、判断を仰ぐ文章に出典つきで添える。**
  添えられないなら、まだ調べ足りていない

---

## Git の運用ルール

**修正するたびに commit する。** 作業をまとめて最後に一括で commit しない。
「1 つの修正 = 1 コミット」で切る。

- **コミットの粒度は細かいほどよい。** 大きな変更でも、完成してから1つに
  まとめず、部品ができた時点で順次コミットする。切る単位は
  **コンポーネント単位** / **ファイル単位** / **機能単位**。
  複数ファイルを1コミットにまとめてよいのは、片方だけでは壊れる場合のみ
  （例: `versions.mk` を作って参照側を同時に変える）
- ブランチは基本的に `main`。
- **`git push` とタグ打ちは、毎回ユーザーの承認を取る。**
  このリポジトリは **`v*.*.*` タグの push が `release.yml` を起動し、
  Docker Hub の公開イメージ（`latest` を含む）を差し替える**。
  `main` への push だけでも `ci.yml` が走る。ローカルのコミットは自由に進め、
  **外に出す操作は確認する**
- **コミットメッセージは日本語。先頭に絵文字を1つ置き、`feat:` のような
  テキスト prefix は付けない**（このリポジトリの既存 498 コミットは
  すべてこの形式で、テキスト prefix は 0 件）。
  本文に「なぜそうしたか」を書く（何を変えたかは diff を見ればわかる）。

  | 種類 | 絵文字 | | 種類 | 絵文字 |
  | --- | --- | --- | --- | --- |
  | 機能追加 | ✨ | | リファクタ | ♻️ |
  | バグ修正 | 🐛 | | テスト | ✅ |
  | ドキュメント・記録 | 📝 | | 取り消し | ⏪ |
  | 雑務・設定 | 🔧 | | マージ | 🔀 |
  | 性能改善 | ⚡ | | 統計・計測の保存 | 📊 |
  | 依存・バージョン更新 | ⬆️ | | 片付け・削除 | 🧹 |
  | Docker 関連 | 🐳 | | セキュリティ | 🔒 |

  **どれにも当てはまらないものは 📌。** 絵文字は先頭に1つだけで、
  `✨ feat: ...` のように併記しない。
- **`CLAUDE.md` も Git 管理下に置く。** 編集したら他のファイルと同様にコミットする。
- 破壊的な操作（履歴の書き換え、force push、ブランチ削除）はユーザーに確認してから行う。
- **push が non-fast-forward で弾かれたら `rebase` ではなく `merge` を使う。**
  `git rebase origin/main` は自分のコミットのハッシュを書き換えてしまうため使わない。
  `git pull origin main` または `git merge origin/main` で取り込み、
  マージコミットを作ってから push する。
- **新規ファイルを残したままターンを終えない。** コミットするか
  `.gitignore` に入れるかをその場で決める。「後で」にすると誰も気づかない
  （実際に `.hypothesis/` の 59 ファイルと `benchmark-optimized.log` が
  追跡されたまま 9 か月放置されていた）

---

## 現在地の把握

**[TODO.md](TODO.md) と [NEXT.md](NEXT.md) を最初に読む。** 役割は分かれている:

- **`TODO.md`** — 「いま何が起きていて、なぜそうしたか」という経緯・現在地に
  加え、**判断待ち・今後やることの TODO**（決定が必要、ユーザー操作待ち、
  すぐには終わらない案件）を書く場所
- **`NEXT.md`** — **直近やること**だけを書く場所。判断不要ですぐ着手できる
  実行待ちのアクションに絞り、**1項目は数行に収める**。本筋から発散した話題
  （「ついでに気になった」「後で考えたい」）を書き留める場所でもある。
  終わった項目・判断待ちに変わった項目は都度消す

- **何をやったか**は `git log --oneline` を見る。1修正=1コミットで理由つきに
  残してある。`TODO.md` に作業履歴を書かない（git log と二重管理になる）
- **要求・設計・タスクの正本は [.kiro/specs/kimigayo-os-core/](.kiro/specs/kimigayo-os-core/)。**
  `TODO.md` はそこと二重管理にせず、「いま手を動かしている話」に絞る
- **リリースの記録は [CHANGELOG.md](CHANGELOG.md) と [RELEASE_NOTES.md](RELEASE_NOTES.md)。**
  `make changelog` で生成できる。**タグを打つ前に必ず更新する**
  （2026-10-09 まで 0.1.0 止まりで、v2.0.1 までの 2 回のリリースが抜けていた）
- **作業の区切りごとに `TODO.md`・`NEXT.md` を更新する。** とくに次の場合は必ず:
  - フェーズが進んだ（調査 → 変更 → ビルド検証）
  - 長時間のビルド・ベンチマークの状態が変わった
  - 「やって分かったこと」に足すべき事実を踏んだ
  - 判断待ちの項目が増えた/決着した

### 長時間のビルド・計測は「同じターンで」記録する

**起動コマンドを打ったら、その同じターンで `TODO.md`・`NEXT.md` を更新して
コミットする。** 完了・中断・無効判明のときも同じ。「後でまとめて」にしない。

**会話で報告しても記録にはならない。** 会話はセッションが切れれば消える。
次のセッションが読むのは `TODO.md`・`NEXT.md` だけで、そこが古いと
「実行待ち」と誤読してビルドを重複起動する。

書くのは3つだけ:

1. **何が走っているか**（コマンドをそのまま貼る。再実行できる形で）
2. **なぜ走らせているか**（何を確認するためか）
3. **終わったら何を確認するか**（例: `build/kernel-patches.log` に
   "not applicable" が無いこと、イメージサイズが 5MB 未満であること）

## 指された対象そのものを直す

**ユーザーが特定の対象（ファイル・ドキュメント・スクリプト・画面）を指して
「内容が薄い」「こうしてほしい」と言ったら、その対象そのものを直す。
同じ内容を別の場所に新しく作って並べない。** 新規作成の方が実装としてきれいに
見えても、ユーザーから見れば「言った場所が直っていない」「同じ内容が2か所に
分かれてどちらを見ればよいか分からない」状態になる。

- **技術的制約で対象をそのまま直せないときも、まず対象側で実現する方法を探す。**
  「この形式ではできないから別の場所に作る」と判断する前に、代替手段を探し尽くす
- **既存の体裁に合わせる。その場しのぎの独自スタイルを作らない。**
  このリポジトリは `scripts/` のログ関数（`log_info`/`log_warn`/`log_error`、
  JST タイムスタンプ付き）・`Makefile` の絵文字つき日本語 help・
  `docs/` の見出し構成がそれぞれ揃っている。**新しいスクリプトを書くなら
  既存の `scripts/*.sh` から雛形を取る**
- それでも別の場所に作る必要があると判断したら、**作る前に聞く**
- 直した結果、古い方が不要になったら消す。残すと二重管理になる

**ドキュメントが実態とずれていたら、ずれている方を直す。**
`DEVELOPMENT.md` には存在しない `src/pkg/` や `make all`・`make iso` が
書かれていた（2026-10-09 に実態に合わせた）。**「書いてあるから正しい」と
思わず、`git ls-files` と `make help` で突合する。**

---

## ディレクトリとファイルの地図

| 場所 | 何があるか |
| --- | --- |
| [versions.mk](versions.mk) | **構成要素のバージョンの単一の真実の源** |
| `config.mk` | クロスコンパイル設定・最適化/強化フラグ・再現可能ビルド |
| `Makefile` | 入口。全量は `make help` |
| `scripts/` | `download-*` / `apply-*-patches` / `build-*` / `test-*` / `verify-*` / `benchmark-*` |
| `src/kernel/` | カーネル config（arch × バリアント）・パッチ・`build.py` |
| `src/busybox/` | BusyBox config（minimal/standard/extended）・musl 互換パッチ |
| `src/openrc/`, `configs/openrc/` | init.d / conf.d / runlevels / `rc.conf` / サービス一覧 |
| `src/libc/`, `src/toolchain/`, `src/security/`, `src/system/` | ビルド補助の Python モジュール |
| `src/benchmark/`, `src/integration/` | 計測・環境別の検証 |
| `tests/unit/`, `tests/property/`, `tests/integration/` | pytest / hypothesis / シェルの統合テスト |
| `docs/developer/` | ARCHITECTURE・BUILD_GUIDE・CICD_GUIDE・CUSTOM_BUILD・PERFORMANCE_* |
| `docs/security/` | ポリシー・監査・ハードニング・脆弱性報告 |
| `docs/troubleshooting/`, `docs/development/` | **実際に踏んだ罠の記録。版上げの前に読む** |
| `docs/maintainer/` | ISSUE_TRIAGE・MAINTENANCE_SCHEDULE |
| `.kiro/specs/kimigayo-os-core/` | requirements / design / tasks（仕様の正本） |
| `.github/workflows/` | ci / release / security / base-image-update / dependency-review |

## CI/CD

| ワークフロー | いつ走るか | 何をするか |
| --- | --- | --- |
| `ci.yml` | `main`/`develop` への push、`main` への PR | ShellCheck → variant × arch の matrix でビルドとテスト |
| `release.yml` | `v*.*.*` タグ、手動 | **Docker Hub へ公開**・GitHub Release 作成・SARIF 連携 |
| `security.yml` | 毎日 02:00 UTC、手動 | 構成要素の版確認・脆弱性スキャン・Issue 起票 |
| `base-image-update.yml` | 毎週月曜 03:00 UTC、手動 | 上流の更新を検知して PR を作る |
| `dependency-review.yml` | PR、毎週月曜 04:00 UTC | 依存レビュー（`fail-on-severity: high`） |
| `build-workflow.yml` | 他から `workflow_call` | 再利用可能なビルド本体 |
| `manual-build.yml` | 手動のみ | variant / arch を選んでビルド |

詳細は [docs/developer/CICD_GUIDE.md](docs/developer/CICD_GUIDE.md)、
Docker Hub 側の設定は [docs/deployment/DOCKERHUB_SETUP.md](docs/deployment/DOCKERHUB_SETUP.md)。

---

## 品質チェック（手で回すもの）

**ローカルで変更したら、外に出す前に最低これを通す:**

```bash
python3 -m pytest tests/unit tests/property -q     # 522 件
make shellcheck-scan                               # scripts/ の静的解析
make ci-build-local                                # rootfs → イメージ → smoke
make security-scan                                 # Trivy
```

**バージョンを上げたときは追加で:**

```bash
grep -rn '6\.6\|1\.36\|1\.2\.4\|0\.52\|3\.19\|3\.23' --include='*.mk' --include='Makefile' \
  --include='Dockerfile*' --include='*.sh' --include='*.py' --include='*.yml' .
# → versions.mk 以外に古い数字が残っていないか
grep -i 'not applicable' build/kernel-patches.log build/busybox-patches.log
# → 効かなくなったパッチが黙ってスキップされていないか
```

---

## rtk（bash 出力の圧縮）

グローバル hook（`~/.claude/settings.json` の PreToolUse → `rtk hook claude`）が
Bash コマンドを自動で `rtk` 付きに書き換える（`git status` → `rtk git status` など）。
**明示的に `rtk` を書く必要はない。**

- 対象: git / ls / cat / head / rg / find / pytest / gh / curl など。
  未対応コマンドは素通しなので安全
- 生出力が必要なとき: `rtk proxy <cmd>`。削減量の確認: `rtk gain`
- **ビルドログは大きい。** `build/*.log` を読むときは `grep` で絞るか
  `make log-kernel` / `log-musl` / `log-openrc`（最新100行）を使う

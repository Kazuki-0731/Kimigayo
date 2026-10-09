# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**このファイルが作業ルールの正本。** 変更したらここを更新し、他のファイルに
重複させない。Claude Code 固有の設定は `.claude/` に置き、**リポジトリで
共有する**（→「Claude Code の設定を共有する」節）。

---

## このプロジェクトは何か

**Kimigayo OS** — Google の distroless と Alpine Linux の設計思想を組み合わせた、
**コンテナ向けの軽量 OS**。パッケージマネージャーを意図的に持たない不変インフラ。

- **成果物は Docker イメージ**（`ishinokazuki/kimigayo-os`）。rootfs だけを詰めた
  イメージで、**カーネルはイメージに入らない**（コンテナはホストのカーネルで動く）
- **想定する使い方は VPS 上の Docker コンテナ。** 組み込みやベアメタル起動は
  対象外（2026-10-10 に決定）。カーネルのビルドは `make kernel` で残して
  あるが、**CI では一切ビルドしない**（成果物に含まれないものを毎 run
  数十分かけて作っていたため外した）。ベアメタル／QEMU を試したいときだけ
  手で回す（→「カーネルは CI で作らない」節）
- **バリアント 3 種**（minimal / standard / extended）× **アーキテクチャ 2 種**（x86_64 / arm64）
- **実測値**: Standard（x86_64）**2.78MB**（2026-10-10）。
  起動時間とメモリは**計測方法に問題があり未測定**
  （`scripts/benchmark-startup.sh` は `docker run -d <image> sleep 5` の
  終了までを測るため、正常なイメージでは約 5,600ms になる。
  README が長く載せていた 439ms はこの `sleep` が成立しなかった場合の値）。
  **v2.0.1 の 1.17MB は Init も libc.so も入っていないイメージの値**なので、
  現在の 2.78MB と並べて比較しない
- 構成要素: **musl libc**（C ライブラリ）/ **Linux カーネル**（強化版）/
  **BusyBox**（コアユーティリティ）/ **OpenRC**（Init）

詳細は [README.md](README.md)・[SPECIFICATION.md](SPECIFICATION.md)・
[docs/developer/ARCHITECTURE.md](docs/developer/ARCHITECTURE.md)。
仕様は [SPECIFICATION.md](SPECIFICATION.md)、設計は
[docs/developer/ARCHITECTURE.md](docs/developer/ARCHITECTURE.md)。

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

## 依頼者も間違えることがある

**ユーザー自身も、指示の内容やこれまでの経緯を勘違いしたり忘れたりする
ことがある。** コード・`git log`・ドキュメント・`SPECIFICATION.md`・過去のルール
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
| `SPECIFICATION.md`・`docs/` 配下の作成・更新 | **実装（コードを書く）** |
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

**長い作業では、会話の途中で決めたことや保留にしたことが埋もれる。**
作業の区切り（実装完了・調査完了・ビルド完了）ごとに、聞かれなくても次の3点を
短く示す:

1. **次にやるべきこと** — 今すぐ着手できる直近の一手
2. **残っていること** — 判断待ち・保留中のタスク（`TODO.md`・
   `NEXT.md` の未消化項目、会話中で「後で」と保留したもの）
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

### プロジェクト自身の版とコードネームも直書きしない

**構成要素の版は `versions.mk`、プロジェクトの版は `git describe`。**
どちらもファイルに数字を書かない。

| 欲しいもの | 取り方 |
| --- | --- |
| プロジェクトの版（3.0.0） | `scripts/get-version.sh`（`git describe --tags`）。Makefile が `KIMIGAYO_VERSION` として export し、compose の `environment` でコンテナにも入る |
| コードネーム（Himawari） | `scripts/get-codename.sh`。**メジャー番号から導出する**（表に版を書き足さない） |

> 2026-10-10 まで `/etc/os-release`・`/etc/motd`・`/.kimigayo-build-info` の
> **3 箇所に `0.1.0` が直書き**されており、v1.0.0 と v2.0.1 を公開した
> あとのイメージも **`0.1.0` と名乗っていた**。`Dockerfile.runtime` の
> `ARG VERSION` の既定値も `0.1.0` で、`Makefile` が `--build-arg VERSION`
> を渡していなかったため `LABEL version` も同じ状態だった。
> **タグ名だけ合っていて中身のメタデータがずれる**ので、`docker images` を
> 見ているだけでは気づけない。
>
> いまは `build-rootfs.sh` の `resolve_project_version()` が 1 箇所で決め、
> `verify_rootfs` が `/etc/os-release` の `VERSION_ID` / `VERSION_CODENAME`
> とビルド中の版を突合する。`verify-image.sh` も os-release の自己整合を見る。

命名体系の正本は [SPECIFICATION.md](SPECIFICATION.md) の「10.3 リリース名」。
**v1.0 / v2.0 はコードネームの運用開始前に公開済みなので名前を持たない**
（後付けしない）。

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
- **`make ci-build-local` は macOS ホストでは通らない。**
  ホスト側で `scripts/build-rootfs.sh` を直接叩き、その中で
  `build-musl.sh` 等を**実際に呼んでビルドしに行く**（成果物があることを
  前提にはしていない）。macOS では musl の `configure` が
  `unsupported long double type` で落ちる（実測）。
  さらに `ARCH` を省略すると `uname -m` から自動検出するため、
  Apple Silicon では `arm64` になり、x86_64 のビルド結果があっても使われない。
- **ローカルで CI 相当を通したいなら、2つの環境に分けて回す。**
  コンテナには Docker ソケットが**読み取り専用**でしか入っていないので
  `docker build` ができず、コンテナ内だけでも完結しない:

  ```bash
  # 1) コンポーネント + rootfs はコンテナ内（ARCH は明示する）
  docker compose run --rm kimigayo-build sh -c \
    'cd /build/kimigayo && ARCH=x86_64 IMAGE_TYPE=standard bash scripts/build-rootfs.sh'

  # 2) イメージ化と smoke テストはホスト側（docker が使える）
  #    ただし make package-rootfs / build-image / test-smoke は
  #    build-rootfs に依存しているので macOS では使えない。
  #    Makefile と同じ処理を手で打つ:
  cd build/rootfs && COPYFILE_DISABLE=1 tar czf \
    ../../output/kimigayo-standard-latest-x86_64.tar.gz \
    --exclude='._*' --exclude='.DS_Store' . && cd -
  docker build --platform linux/amd64 -f Dockerfile.runtime \
    --build-arg TARBALL_PATH=output/kimigayo-standard-latest-x86_64.tar.gz \
    -t kimigayo-os:standard-x86_64 .
  docker run --rm --platform linux/amd64 kimigayo-os:standard-x86_64 \
    /bin/sh -c 'ls / && busybox | head -1'
  ```

  **`COPYFILE_DISABLE=1` を外さないこと。** macOS の `bsdtar` は
  AppleDouble メンバー（`._*`）を**除外処理のあとに自分で生成する**ため
  `--exclude='._*'` では止まらない。さらに **bsdtar は自分が作った `._*` を
  一覧表示時に隠す**ので `tar tzf` で確認しても気づけない
  （Linux 側で展開すると出てくる）。
  実測では **458 個の `._*` がイメージに入っていた**（2026-10-09）

  **Linux ホストなら `make ci-build-local` がそのまま通る。**
  GitHub Actions（`ubuntu-latest`）はこの経路
- **長いビルドは `make shell` → `tmux` 内で回す。** `make build` を
  そのまま叩くと出力が溜まってから出るため進捗が見えない

### フルビルドは x86_64 / arm64 とも GitHub Actions で回す（既定）

**これが方針。開発機でフルビルドしない。**

- **`docker-compose.yml` は `platform: linux/amd64` を固定している。**
  開発機が Apple Silicon（arm64）だと **x86_64 が QEMU エミュレーションに
  なり、遅いうえに実機が熱くなる**（過去にこれで GitHub Actions へ移した）。
  musl・BusyBox・OpenRC は許容範囲だが、**カーネルのフルビルドは非現実的**
  （数時間〜、失敗もする）
- **arm64 も Actions に任せる。** `ubuntu-latest`（x86_64）から
  clang/lld でクロスコンパイルするので QEMU を介さない。
  **2026-10-09 に 3 バリアント × 2 アーキテクチャの 6 ジョブすべて成功**
  （run 37880882653、カーネル 6.18.55 込み）。所要時間:

  | | x86_64 | arm64 |
  | --- | --- | --- |
  | minimal | 15:47 | 42:44 |
  | standard | 27:05 | 47:30 |
  | extended | 14:59 | 28:50 |

  **この数字はカーネル込み。** いまは CI でカーネルを作らないので
  これより大幅に短い（→ 下の「カーネルは CI で作らない」節）。
  `build-workflow.yml` の `timeout-minutes` は 120 にしてある。
  **arm64 を開発機のネイティブビルドに移す必要はない**
  （`platform` 固定を外す話も不要）
- **開発機でやるのは「段を絞ったビルド」まで。** 例:
  `make ARCH=x86_64 arch/x86/realmode/` のようにカーネルの一部だけ、
  あるいは `scripts/build-openrc.sh` 単体。
  **arm64 のクロスビルドを手元で回すなら compose を使わない**
  （`memory: 2G` 制限で `meson setup` が OOM kill される。
  `docker run --memory 8g` で直接叩く）
- **Docker イメージにカーネルは入らない。** rootfs だけなので、
  musl / BusyBox / OpenRC の変更は `make ci-build-local` で検証できる。
  **「イメージが動いた」はカーネルを検証したことにならない**
- ダウンロードキャッシュは named volume `kimigayo-downloads` に永続化される。
  バージョンを上げたら新しい tarball を取り直すだけで、古いものは残る

### カーネルは CI で作らない

**`ci.yml` はカーネルをビルドしない。** 2026-10-10 に決めた。

- **理由は、成果物に入らないものを検証していたから。** Kimigayo の成果物は
  rootfs だけを詰めた Docker イメージで、コンテナはホストのカーネルで動く。
  CI がカーネルを作っても、できたイメージの中身は1バイトも変わらない。
  それでいて 1 run あたり数十分増えていた
- **想定する使い方は VPS 上の Docker コンテナ。** 組み込み・ベアメタル起動は
  対象外なので、「カーネルが起動するか」を毎 push で見る必要がない
- **`make kernel` は残してある。** ベアメタルや QEMU を試したくなったときに
  ゼロから作り直さずに済むようにするため。消さない
  （→「削除指示を受けたら」節）

| やりたいこと | どうするか |
| --- | --- |
| 手元でカーネルを作る | `make kernel TARGET_ARCH=x86_64`（数十分〜数時間） |
| CI でカーネルを作る | Actions から `manual-build.yml` を `build_kernel=true` で実行 |
| カーネルの版を上げる | `versions.mk` を更新 → 上の2つで確認する。**`ci.yml` は通っても検証にならない** |

**カーネル関連の変更をしたときは、`ci.yml` が緑でも「カーネルは見ていない」。**
`versions.mk` の `KERNEL_VERSION` や `src/kernel/` を触ったら、
手で `manual-build.yml` を回すか `make kernel` を通す。

### パッチはなぜ存在するか

**パッチを消す・足す前に、なぜ存在するかを調べる**（→「判断を仰ぐ前に、
その対象がなぜ存在するかを調べる」節）。

| パッチ | 理由 |
| --- | --- |
| `src/busybox/patches/0001-vi-musl-libc-compatibility.patch` | BusyBox の `editors/vi.c` が glibc の GNU 正規表現拡張（`re_syntax_options`・`re_compile_pattern`・`re_search`）を使っており musl ではコンパイルできない。POSIX `regcomp`/`regexec` に書き換えている。**1.38.0 でも上流は GNU 拡張のまま**なので引き続き必要（2026-10-09 に 1.38.0 への適用を dry-run で確認）。詳細 → [docs/development/busybox-vi-patch.md](docs/development/busybox-vi-patch.md) |

**カーネルのパッチは現在0件。** `0001-security-hardening.patch` は中身が
コメントだけのプレースホルダで、毎ビルド「適用できないパッチ」として
警告を出すだけだったので削除した（2026-10-09）。
`apply-kernel-patches.sh` が0件のときに再生成する処理も外してある
（消しても次のビルドで復活していた）。

**削除済みのパッチ（2026-10-09、カーネル 6.6 → 6.18 で不要になった）:**
`0002-disable-retpoline-realmode.patch`・`0003-efi-stub-std-gnu11.patch`・
`0004-x86-boot-compressed-std-gnu11.patch` はいずれも **GCC 15 で 6.6 系を
ビルドするための `-std=gnu11` 回避策**だった。6.18 では上流が取り込んでいる
（`arch/x86/Makefile` の `REALMODE_CFLAGS := -std=gnu11 ...`、
`drivers/firmware/efi/libstub/Makefile` の `cflags-$(CONFIG_X86) += ... -std=gnu11`、
`arch/x86/boot/compressed/Makefile` の `KBUILD_CFLAGS += -std=gnu11`）。

> **版を上げたら、本当に新しい版がビルドされたかを確かめる。**
> `scripts/build-{musl,busybox,openrc}.sh` は
> インストール先の `.kimigayo-build-version` と `versions.mk` の版が
> 一致したときだけビルドをスキップする（2026-10-09 にそうした）。
> **それ以前は「バイナリが存在するか」だけを見ていたため、版を上げても
> 古いインストール結果が残っていればビルドを飛ばし、しかも
> 「✅ build completed」と報告していた**（BusyBox 1.36.1 が 1.38.0 の
> つもりで残る事故を実際に踏んだ。パッチも当たらない）。
> 確認するなら（`versions.mk` の値と、実際にビルドされた版を並べる）:
>
> ```bash
> make print-versions
> for c in musl busybox openrc; do
>   printf '%-10s %s\n' "$c" \
>     "$(find build -maxdepth 2 -name '.kimigayo-build-version' \
>         -path "*${c}-install-*" -exec cat {} \; 2>/dev/null)"
> done
> # 空欄 = 未ビルド。versions.mk と食い違っていたらビルドし直す
> # BusyBox は "1.38.0+standard" のようにバリアントも入る（下記）
> # カーネルは build/kernel/output/vmlinuz-<version>-<arch> のファイル名で分かる
> ls build/kernel/output/vmlinuz-* 2>/dev/null
> ```

> **BusyBox のスタンプだけは版 + バリアント。**
> BusyBox は同じ版でも minimal / standard / extended で `.config` が違い、
> できあがるバイナリも違う。版だけを見ていたため、
> **standard をビルドしたあとに `IMAGE_TYPE=minimal` でビルドしても
> 「already built」でスキップされ、standard の BusyBox が入った
> minimal イメージが出来ていた**（2026-10-09 に発覚）。
> いま `.kimigayo-build-version` には `1.38.0+standard` のように入る。
> **バリアントを切り替えて測るときは、スキップされていないことを確認する。**

> **`scripts/apply-kernel-patches.sh` は `patch -p1 --dry-run` が通らないパッチを
> `log_warn` して `return 0` する。つまり当たらないパッチは黙ってスキップされ、
> ビルドは成功したように見える。** バージョンを上げたら
> **`build/kernel-patches.log` を必ず読み、「not applicable」が出ていないか確認する。**
> 効かなくなったパッチは、不要になったのか・当て直しが必要なのかを判断して
> 消すか作り直す。放置すると「適用されているつもり」のまま進む。
> 同じことが `scripts/apply-busybox-patches.sh`（`build/busybox-patches.log`）にも言える。

### 版を上げたら `build/` の残骸を疑う

**`build/` には前の版の成果物が残る。これが2通りの形で事故になる。**
2026-10-09 の更新では**両方を実際に踏んだ**。

1. **黙って古いものが使われる（こちらが危険）** —
   ビルド済み判定が版を見ていないと、ビルドを飛ばして
   「✅ build completed」と報告しながら古いバイナリを残す。
   BusyBox 1.36.1 が 1.38.0 のつもりで残った
2. **後段で意味の分かりにくいエラーになる** —
   古い meson で作った `openrc-build-*/meson-private/build.dat` が
   `references functions or classes that don't exist` で `meson setup` を止めた

**いまは `scripts/build-{musl,busybox,openrc}.sh` が
`.kimigayo-build-version` と `versions.mk` を突合し、違っていれば
インストール先とビルドディレクトリの両方を捨てて作り直す。**
それでも想定外の残骸は出るので、**版上げ直後にビルドが妙な挙動をしたら
まず `make clean-<component>` を試す**（`clean-musl` / `clean-kernel` /
`clean-busybox` / `clean-openrc`）。`make clean-all` は
`build/downloads/` まで消して約150MBの再取得を招くので最後の手段。

### musl を作り直したら、それにリンクしているものも作り直す

**`.kimigayo-build-version` はコンポーネント間の依存を見ていない。**
版が同じなら「ビルド済み」と判定するので、**musl を作り直しても
BusyBox と OpenRC は古いバイナリのまま残る。**

2026-10-09 に arm64 の musl のリンク方法を直したあと、これで実際に
詰まった。rootfs の検査（`verify_rootfs`）は全項目通るのに、
イメージで OpenRC を実行すると **Segmentation fault（終了コード 139）**
になった。原因は OpenRC のバイナリが古い musl に対してリンクされた
ままだったこと（`ls -l` の日時で分かる）。

**musl を作り直したときは、BusyBox と OpenRC の成果物も捨てる:**

```bash
# arm64 の例。musl は aarch64、BusyBox と OpenRC は arm64 という
# ディレクトリ名の違いに注意（MUSL_ARCH のマッピング）
rm -rf build/musl-install-aarch64 build/musl-build-aarch64 \
       build/busybox-install-arm64 build/busybox-build-arm64 \
       build/openrc-install-arm64 build/openrc-build-arm64 build/openrc-cross-arm64
```

`make clean-musl` だけでは足りない。
**「ビルドは通ったのに実行すると落ちる」ときは、まず成果物の日時を見る。**

```bash
ls -l build/rootfs/sbin/openrc build/rootfs/usr/lib/libc.so
# libc.so より古い実行ファイルがあれば、それは別の musl 向け
```

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
- **オプションが消えると、任意だった依存が必須になることがある。**
  OpenRC 0.52.1 の libcap は
  `dependency('libcap', required: get_option('capabilities'))` で任意だったが、
  0.63.2 では `dependency('libcap', version: '>=2.33')` になり**必須**。
  `capabilities` オプション自体が消えているので無効化できない。
  ビルド環境に `libcap-dev` を入れ、arm64 クロス用には sysroot 側に
  `libcap.pc` を置いて meson のクロスファイルから `pkg_config_libdir` で
  指すようにした（ホストの `.pc` を拾わせない）
- **`apk` でクロスアーキテクチャのパッケージを取るときは鍵を指定する。**
  Alpine はアーキテクチャごとに別の鍵で署名しており、x86_64 のイメージには
  `/etc/apk/keys` に x86_64 用の鍵しか入っていない。
  `apk fetch --arch aarch64` だけでは APKINDEX が `UNTRUSTED signature` に
  なり `unable to select package` で失敗する。
  `--keys-dir /usr/share/apk/keys/aarch64` を渡す
  （`--allow-untrusted` で黙らせない。署名検証は維持する）

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
- **設定の置き場所を間違えると「書いてあるのに効いていない」状態になる。**
  2026-10-09 まで `pytest.ini` に `[hypothesis]` と `[coverage:run]` /
  `[coverage:report]` が書かれていたが、**どちらも効いていなかった**
  （hypothesis は ini を読まない。coverage が読むのは `.coveragerc` /
  `setup.cfg` / `tox.ini` / `pyproject.toml` で `pytest.ini` は読まない）。
  正しい置き場所:

  | 何の設定 | どこに書くか |
  | --- | --- |
  | pytest 本体（testpaths・addopts・markers） | `pytest.ini` の `[pytest]` |
  | hypothesis（max_examples・verbosity・deadline） | `tests/conftest.py` の `settings.register_profile` |
  | coverage（source・omit・report） | `.coveragerc` |

- **hypothesis の `deadline` は無効にしてある**（`tests/conftest.py`）。
  このリポジトリのプロパティテストは `tmp_path` への実ファイル書き込みや
  サブプロセス起動を含み、1例あたり 300-400ms かかることがある。
  既定の 200ms は純粋な関数の性能劣化を拾うための値で、ここには合わない。
  **arm64 ホストでの linux/amd64 エミュレーションでは実際に 3 件が
  `DeadlineExceeded` で落ちた**（ロジックの失敗ではなく実行速度の問題）
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
- **`make trivy-scan`（イメージスキャン）は何も検査していない。**
  Kimigayo は `scratch` 上の手組み rootfs でパッケージデータベースを
  持たないため、Trivy は対象を1つも識別できない（実測で
  `Target: -` / `Not scanned` / `Metadata.OS: null` / `Results: 0`）。
  **「脆弱性 0 件」ではなく「スキャンしていない」。**
  それでも `security-scan` は「✅ 完了」と出すので、沈黙を安全と
  読まないこと。脆弱性の追跡は構成要素の版を手で突合する
  （→ `security-review` skill）。`trivy-fs-scan` はリポジトリ側の
  依存を見るので有効
- `.github/workflows/security.yml` が毎日 02:00 UTC に走り、
  `base-image-update.yml` が毎週月曜に上流の版を確認する。
  **これらが作る PR / Issue は「上流が動いた」という一次情報**なので、
  バージョン更新の起点として先に見る
- **外部 Action は tag で固定する。** `@master` 参照は供給網のリスクかつ
  再現性がない（2026-10-09 に `trivy-action`・`action-shellcheck` を固定した）
- 脆弱性の報告・運用は [docs/security/](docs/security/) 配下
  （`SECURITY_POLICY.md`・`VULNERABILITY_REPORTING.md`・`HARDENING_GUIDE.md`）

**機密を書かない。** `.env`（Docker Hub トークン）は `.gitignore` 済み。
`CLAUDE.md`・`docs/`・コミットメッセージに API キー・トークン・個人のパスを書かない。
**`.claude/` は共有する**ので、ここにも機密を置かない
（→「Claude Code の設定を共有する」節）。

---

## メモは機密扱いにする

**メモ・下書きのファイルはリポジトリに入れない。**
判断基準は**「いま何が書かれているか」ではなく「次に何が書かれるか
分からないこと」**。メモの置き場にはあとで資格情報・第三者の情報・
社外に出せない情報が書き込まれ得る。**このリポジトリは公開されている**ので、
入ってから気づくのでは遅い。

対象（名前に関わらず、性格がメモなら対象）:

| 置き場 | 例 |
| --- | --- |
| `TODO.md` / `NEXT.md` | 経緯・現在地・判断待ち |
| `.claude/` 直下の `*.md` | `question.md`・`error.md` など会話の下書き |
| `MEMO*` / `NOTES*` / `SCRATCH*` / `WIP*` / `DRAFT*` / `IDEA*` | 名前で分かるもの |
| `*.local.json` など | 個人の環境設定（→「Claude Code の設定を共有する」節） |

**強制は機械チェックで行う**（文章のルールは守れない。
→「判断が絡まないミスは文章にしない」節）:

- **`.claude/hooks/guard-memo-files.sh`** が `git add` の名指しと
  `git commit` 時のステージを検査して止める。**`git add -f` も
  `git add .` 経由も捕まる**
- 判定は **`.claude/hooks/memo-paths.py`**。
  **部分一致は使えない**（このリポジトリには `memory.py`・
  `memory_benchmark.py`・`benchmark-memory.sh` があり `memo` を含む。
  `RELEASE_NOTES.md` も `NOTES` を含むが実ドキュメント）。
  basename に対する厳密な規則だけを使い、
  **追跡中の全ファイルに誤爆しないことを実測で確認してから変える**:

  ```bash
  git ls-files | python3 .claude/hooks/memo-paths.py   # 何も出なければ OK
  ```

- `.gitignore` にも同じパターンを書いてあるが、そちらは補助。
  **パターンを増やすときは両方を更新する**

### 公開ドキュメントからメモへリンクしない

**追跡されないファイルへのリンクは、手元では壊れていることに気づけない。**
`.gitignore` されていてもファイルは手元にあるので、ローカルで
リンクを辿れてしまう。**clone した人にだけ壊れている。**

実例（2026-10-09）: `README.md`・`CHANGELOG.md`・`docs/developer/
PERFORMANCE_TUNING.md` が、追跡していない `TODO.md` を指していた。

**判定は追跡ファイル基準で機械的に行う:**

```bash
make check-links        # scripts/check-links.py
```

`ci.yml` でも走る。ファイルシステムの存在で判定するスクリプトを
書かないこと（それでは今回の件を検知できない）。

経緯をドキュメントに残したいときは、メモにリンクするのではなく
**内容を置き場に移す**（→ 下記の対応表）。

### メモに書くべきでないもの

**他の人に残す必要がある内容をメモに書かない。** そこは追跡されないので
消えるし、公開もされない。置き場はこう分ける:

| 内容 | 置き場 |
| --- | --- |
| 踏んだ罠・症状と原因 | `docs/troubleshooting/` |
| 手順 | `docs/developer/` |
| 変更の経緯・理由 | コミットメッセージ |
| リリースの記録 | `CHANGELOG.md` / `RELEASE_NOTES.md` |
| 仕様・設計 | `SPECIFICATION.md` / `docs/developer/ARCHITECTURE.md` |
| 作業ルール | この `CLAUDE.md` |

---

## Claude Code の設定を共有する

**`.claude/` 配下の設定はリポジトリに入れる。** Skills・Subagent・
カスタムコマンド・Hook は**このプロジェクトの作業ルールそのもの**であり、
技術的な内容しか含まないので共有して困らない。個人の環境に置くと、
次に同じ作業をする人（や次のセッション）に届かない。

**ここに機密を置かない。** Docker Hub トークンは `.env`（`.gitignore` 済み）。
個人のパスも書かない。

> **`settings.local.json` は共有しない。** 判断基準は「秘密が入っているか」
> ではなく**「他人の環境に何を事前承認させるか」**。実際に
> `Read(///**)`（全ファイルシステムの読み取り）と `Bash(bash:*)`（任意の
> コマンド）が入っていた。**このリポジトリは公開されているので、置けば
> clone した全員の Claude Code にその承認が効く。**
> 共有するのは `settings.json`（Hook の登録だけ）。

| 場所 | 中身 | Git |
| --- | --- | --- |
| `.claude/settings.json` | Hook の登録、`env` | 追跡 |
| `.claude/settings.local.json` | 権限の allow リスト | **無視**（下記） |
| `.claude/hooks/*.sh` | 機械的に止めるもの | 追跡。`make shellcheck-scan` の対象 |
| `.claude/agents/*.md` | Subagent の定義 | 追跡 |
| `.claude/skills/*/SKILL.md` | 手順（判断を伴うもの） | 追跡 |
| `.claude/commands/*.md` | スラッシュコマンド | 追跡 |
| `.claude/*.md`（直下） | 個人のメモ | **無視** |

### Hook — 機械的に止めるもの

**人の判断が絡まないミスだけを止める**（→「判断が絡まないミスは文章に
しない」節）。判断や例外が多いものを Hook にすると、毎回の警告がノイズに
なり、ノイズになった警告は読まれなくなる。

| Hook | いつ | 何をするか |
| --- | --- | --- |
| `guard-bash.sh` | PreToolUse(Bash) | リリースタグ・Docker Hub push・force push・rebase・`clean-all`・ダウンロードキャッシュ削除・`COPYFILE_DISABLE` なしの `tar`（macOS）・`.env` の add をブロック |
| `after-edit.sh` | PostToolUse(Edit\|Write) | `.sh` の構文エラーをブロック。`versions.mk` を触ったら連動先を出す。`-Wno-error` や `\|\| true` を**新しく足したら**指摘する |
| `check-untracked.sh` | Stop | 未追跡の新規ファイルが残っていたら1度だけ止める |

**通常の `git push origin main` は止めていない。** 会話での承認ルール
（→「Git の運用ルール」節）に任せる。ここで止めると承認後も進めなくなる。
止めているのは**外に出て取り消せないもの**（タグ・Docker Hub）だけ。

> 権限の allow リストで `git push` を事前承認している環境でも、
> `guard-bash.sh` が整合を取る（Hook は権限の allow より先に走り、
> 危険な部分集合だけを止める）。

### Subagent — 役割とツールを絞って任せる

| Subagent | 使いどき |
| --- | --- |
| `rootfs-verifier` | rootfs / イメージを作った直後、リリース前。**「起動した」は検証ではない** |
| `version-auditor` | 版上げの前後、リリース前。`versions.mk` の突合・チェックサム・上流の新版・パッチのスキップ |
| `docs-reconciler` | 計測のあと、版上げのあと。数値とバージョンの文書間の食い違い |

いずれも**調査専門で変更しない。** 直すかどうかはこちらが判断する。

### Skills — 判断を伴う手順

| Skill | 使いどき |
| --- | --- |
| `version-bump` | 構成要素のバージョンを上げる（上流調査 → チェックサム → パッチ → 検証 → 反映） |
| `measure-and-land` | 計測して数値を着地させる |
| `release` | リリースの準備と承認の取り方 |
| `security-review` | セキュリティ点検（CVE 追跡・強化フラグの検証・攻撃面・供給網・脆弱性報告への対応） |

### カスタムコマンド

| コマンド | 何をするか |
| --- | --- |
| `/status` | 現在地（宣言版 / 実ビルド版 / イメージ / 未 push / 未追跡 / パッチのスキップ） |
| `/gate` | 外に出す前の品質ゲート（pytest / shellcheck / YAML・JSON / 作業ツリー） |
| `/verify-image` | 成果物の検査（`rootfs-verifier` に投げる） |

### Agent Teams

**プロジェクト単位の設定ファイルは存在しない。** `.claude/teams/teams.json`
のようなファイルは設定として認識されず、ただのファイルとして扱われる。
再利用する役割は**Subagent の定義で表現する**（上記 3 つはそのまま
teammate として使える）。

`.claude/settings.json` の `env` で有効化してある:

```json
{ "env": { "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1" } }
```

**実験的機能で、トークン消費が大きい。** teammate は1人ずつ独立した
セッションなので、消費は人数に比例する。**有効なあいだは、名前を付けた
Subagent が teammate として起動する**ため、頼んでいなくてもチームが
できることがある。止めるなら同じ場所を `"0"` にする。

向いているのは**並列に探索して突き合わせる仕事**。このリポジトリなら:

- 版上げの影響調査（カーネル / musl / BusyBox / OpenRC を別々に）
- 成果物の検査を arch × バリアントで分担
- 原因の競合仮説を並べて互いに反証させる（arm64 の OpenRC が
  ビルドできなかったときは原因が4つ重なっていた）

**逐次の作業・同じファイルを触る作業には使わない。** 単一セッションか
Subagent の方が速くて安い。3〜5人から始める。

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

**`TODO.md` と `NEXT.md` を最初に読む。** 役割は分かれている:

- **`TODO.md`** — 「いま何が起きていて、なぜそうしたか」という経緯・現在地に
  加え、**判断待ち・今後やることの TODO**（決定が必要、ユーザー操作待ち、
  すぐには終わらない案件）を書く場所
- **`NEXT.md`** — **直近やること**だけを書く場所。判断不要ですぐ着手できる
  実行待ちのアクションに絞り、**1項目は数行に収める**。本筋から発散した話題
  （「ついでに気になった」「後で考えたい」）を書き留める場所でもある。
  終わった項目・判断待ちに変わった項目は都度消す

- **何をやったか**は `git log --oneline` を見る。1修正=1コミットで理由つきに
  残してある。`TODO.md` に作業履歴を書かない（git log と二重管理になる）
- **仕様の正本は [SPECIFICATION.md](SPECIFICATION.md)、設計は
  [docs/developer/ARCHITECTURE.md](docs/developer/ARCHITECTURE.md)。**
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
| `SPECIFICATION.md` | 仕様の正本 |
| `.github/workflows/` | ci / release / security / base-image-update / dependency-review |

## CI/CD

| ワークフロー | いつ走るか | 何をするか |
| --- | --- | --- |
| `ci.yml` | `main`/`develop` への push、`main` への PR | ShellCheck → リンク検査 → pytest → variant × arch の matrix でビルドとイメージ検証（**カーネルは作らない**） |
| `release.yml` | `v*.*.*` タグ、手動 | **Docker Hub へ公開**・GitHub Release 作成・SARIF 連携 |
| `security.yml` | 毎日 02:00 UTC、手動 | 構成要素の版確認・脆弱性スキャン・Issue 起票 |
| `base-image-update.yml` | 毎週月曜 03:00 UTC、手動 | 上流の更新を検知して PR を作る |
| `dependency-review.yml` | PR、毎週月曜 04:00 UTC | 依存レビュー（`fail-on-severity: high`） |
| `build-workflow.yml` | 他から `workflow_call` | 再利用可能なビルド本体 |
| `manual-build.yml` | 手動のみ | variant / arch を選んでビルド。**カーネルを CI で作る唯一の経路**（`build_kernel=true`） |

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
# 1) 今どの版を使うことになっているか
make print-versions

# 2) versions.mk で捨てた「古い値」が他のファイルに残っていないか
#    （ここに番号を直書きすると次の更新で腐るので、git diff から拾う）
git diff versions.mk | grep '^-[A-Z]' | grep -oE '[0-9]+\.[0-9.]+' | sort -u |
while read -r v; do
  hits=$(grep -rn --fixed-strings "$v" \
    --include='*.mk' --include='Makefile' --include='Dockerfile*' \
    --include='*.sh' --include='*.py' --include='*.yml' . \
    | grep -v '^\./versions.mk' || true)
  [ -n "$hits" ] && { echo "--- 旧値 $v がまだ残っている:"; echo "$hits"; }
done
# チェックサム表とコメント内の経緯は残っていて正しい。
# それ以外に出たら直す。

# 3) 効かなくなったパッチが黙ってスキップされていないか
grep -iE 'skipped: [1-9]|not applicable' \
  build/kernel-patches.log build/busybox-patches.log
# → 出たら「上流が取り込んだので不要」か「当て直しが必要」かを判断する
#    （src/kernel/patches/README.md 参照）

# 4) 上流のビルドオプションが消えていないか
#    OpenRC なら meson_options.txt、BusyBox なら make oldconfig の差分、
#    カーネルなら make olddefconfig の出力を見る
grep -oE "^option\('[a-z_-]+'" build/openrc-*/meson_options.txt
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

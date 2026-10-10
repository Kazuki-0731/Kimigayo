---
name: measure-and-land
description: イメージサイズ・起動時間・メモリなどを計測し、測定条件つきでドキュメントに反映する。ベンチマークを取る、サイズを測る、性能を比較する、README の数値を更新するときに使う。測るだけで終わらせず着地先まで持っていく手順。
---

# 計測して、数値を着地させる

**計測は「測って報告」で終わりにしません。** 着地先が無い計測は、同じことを
半年後にもう一度測り直すだけです（CLAUDE.md「数値を出したら反映まで」節）。

着地先は4つ。**どれにするかを測る前に決めます。**

| 着地先 | 何をするか |
| --- | --- |
| ドキュメント | `README.md` のパフォーマンス表、`docs/benchmarks/`、`docs/developer/PERFORMANCE_*` |
| config | カーネル / BusyBox config、`configs/sysctl/`、`configs/openrc/` の項目を実際に変える（または**外す**） |
| CI | 退行を検知したいならワークフローか回帰テストにする |
| 仕組み | ルール化・Hook 化・回帰テスト化 |

**「着地先なし」も結論として選べます。** ただし**なぜ活かせないのか・
何が揃えば活かせるのか**を書き残します。

---

## 測る前に

**目標値が曖昧な指示は、測る前に目安を聞きます**（CLAUDE.md
「目安の無い指示は、一度の変更で様子見せず先に聞く」節）。
「軽くして」「速くして」は目安を確認してから着手します。

**走っているビルドと競合しないか確認します。**

```bash
docker ps   # ビルドコンテナは kimigayo-build-env という固定名
```

**時間がかかるものは見込みを先に伝えます。** カーネルのフルビルドは数十分〜数時間。

---

## どのスクリプトが何を測るか（8本あります）

**先にここを見てください。** 測りたいものに対応するスクリプトが既にあります。
新しく書く前に、既にあるものが壊れていないかを疑ってください
（2026-10-10 に 2 本が別物を測っていたのが見つかりました）。

| スクリプト | 何を測るか | 主な入力 | 出力 |
| --- | --- | --- | --- |
| `benchmark-size.sh` | イメージサイズ（Kimigayo と比較対象をまとめて） | `IMAGES` 配列（スクリプト内） | `benchmark-size.json` |
| `benchmark-startup.sh` | 起動時間。`MODE=exec` は `/bin/true`、`MODE=init` は `openrc default` の完走まで | `IMAGE` `ITERATIONS` `MODE` `PLATFORM` | `benchmark-startup.json` |
| `benchmark-memory.sh` | 常駐メモリ（**KB**） | `IMAGE` `DURATION` `PLATFORM` | `benchmark-memory.json` |
| `benchmark-busybox.sh` | 8 コマンド（`ls` `grep` `find` `awk` `sort` `cat` `wc` `head`）を Alpine と比較 | `IMAGE_NAME` `ALPINE_IMAGE` `BENCHMARK_ITERATIONS` | `benchmark-results/busybox.json` |
| `benchmark-lifecycle.sh` | コンテナの作成・起動・停止・削除 | `IMAGE_NAME` `BENCHMARK_ITERATIONS` | `benchmark-results/lifecycle.json` |
| `benchmark-comparison.sh` | Kimigayo vs Alpine / distroless / Ubuntu | `ITERATIONS` | `benchmark-results/comparison_<時刻>.{txt,json,md}` |
| `benchmark-report.sh` | **測らない。** 上の JSON を読んで Markdown にまとめる | `$1`（既定 `benchmark-results`） | `benchmark-results/BENCHMARK_REPORT.md` |
| `benchmark-all.sh` | 上をまとめて回す | `OUTPUT_DIR` | `benchmark-results/` 一式 |

**`benchmark-report.sh` は JSON のキー名を直接読んでいます。**
計測スクリプトの出力キーを変えるときは、必ずここも直してください
（2026-10-10 に `average_mb` → `average_kb` で実際に壊しました）。

**`benchmark-all.sh` は各ステップに `|| true` を付けています。**
1本失敗しても最後まで走るので、**「全部成功した」とは読めません**。
使うときは個別の JSON が生成されたかを確認してください。

### 実行環境の制約（macOS の開発機）

- **`mapfile` を使うスクリプトは macOS の bash 3.2 では落ちます。**
  `/opt/homebrew/bin/bash` で実行してください
  （`Makefile` の `benchmark-comparison` ターゲットは既にそうしています）
- **x86_64 を QEMU で測った時間を数値として載せないこと。**
  開発機は Apple Silicon で、`--platform linux/amd64` は
  エミュレーションです。**サイズは比較できますが、時間は比較になりません。**
  時間とメモリは arm64 ネイティブで測り、その旨を明記します
- 比較対象（Alpine / Ubuntu / distroless）も**同じアーキテクチャで引き直して**
  から測ります。`docker pull --platform linux/arm64 ...`

---

## イメージサイズ

これは信頼できる計測です。

```bash
docker images kimigayo-os --format '{{.Tag}}\t{{.Size}}'
```

**比較対象は同じホスト・同じ platform で測り直します。** 他所の公表値を
引用しないこと。

```bash
for i in gcr.io/distroless/static-debian12 alpine:latest ubuntu:24.04; do
  docker pull -q --platform linux/amd64 "$i" >/dev/null
  printf '%-45s %s\n' "$i" "$(docker images "$i" --format '{{.Size}}')"
done
```

**過去の版の値と並べるときは中身が同じか確認します。**
**v2.0.1 の 1.17MB は OpenRC も musl の `libc.so` も `/tmp` も入って
いないイメージの値**で、現在の値と同じものを測った数字ではありません。
並べるなら必ずその旨を書きます。

バリアント間の差はアプレット数だけです（minimal 370 / standard 403 /
extended 413）。差が出ないときは BusyBox のビルドがスキップされた疑いを持ちます
（スタンプは `1.38.0+standard` の形式）。

---

## 起動時間とメモリ（2026-10-10 に直しました）

**両スクリプトは 2026-10-10 まで測るものを間違えていました。** いまは直って
います。壊れ方を知らずに触ると戻してしまうので、何を測るかを変えるときは
ここを読んでください。

| | 壊れていた測り方 | いまの測り方 |
| --- | --- | --- |
| `benchmark-startup.sh` | `docker run -d <image> sleep 5` の**終了まで**。正常なイメージほど必ず約 5,600ms（439ms はこの `sleep` が成立しなかった＝**イメージが壊れているほど速く見える**値）| `docker run --rm <image> /bin/true` の実時間。`MODE=init` なら `/sbin/openrc default` の完走まで |
| `benchmark-memory.sh` | `KiB` を `0.001` に置換したうえ整数 MB に丸め、**1MB 未満を 0 としか表せなかった**（旧 0.2MB）| 単位を見て KB に正規化。KB で保持する |

**起動時間でイメージの優劣を主張しないこと。** 2026-10-10 の実測では
Kimigayo 0.62 秒・Alpine 0.61 秒・Ubuntu 0.61 秒で、**差は出ません**。
測っている時間のほとんどが Docker のコンテナ生成です。
差が出るのは常駐メモリ（232 / 280 / 316KB）の方です。

- **x86_64 を QEMU で測った時間を載せないこと。** 時間の比較になりません。
  開発機（Apple Silicon）では arm64 ネイティブで測ります
- macOS の bash 3.2 では `mapfile: command not found` で落ちます。
  `/opt/homebrew/bin/bash` で実行してください
- 「起動時間」の定義（プロセス起動のオーバーヘッドか、OpenRC の
  `default` ランレベル完了までか）を**決めるのは人の判断**です

---

## 測定条件を必ず添える

条件の無い数値は、次に見た人が再現できず、結局測り直しになります。

```
計測: イメージサイズ
日付: 2026-10-09
ホスト: macOS (Apple Silicon / arm64)
platform: linux/amd64（docker-compose.yml が amd64 を強制）
対象: kimigayo-os:standard-x86_64
方法: docker images --format '{{.Size}}'
試行: 1（サイズは決定的なので1回で足りる）
```

**開発機は arm64 で compose は amd64 を強制するため、ローカルの計測値は
CI と直接比較できません。** 時間を含む指標では必ず明示します。

---

## ドキュメントに反映する

**README とベンチマークドキュメントを同じターンで突合します。**
片方だけ直すと、次に「どっちが正しいのか」を調べ直すことになります。

反映先:

- `README.md` の 主な特徴 と パフォーマンス実績表（**英語セクションも同時に**）
- `docs/benchmarks/`
- `docs/developer/PERFORMANCE_ANALYSIS.md`・`PERFORMANCE_TUNING.md`
- `SPECIFICATION.md`

突合に `docs-reconciler` subagent を使えます。

**取り消す数値も記録します。** 誤りだった数値は黙って消さず、
`CHANGELOG.md` に「取り消した」と書きます（439ms と 0.2MB はそうしました）。
**取り消したあと測り直せたら、取り消した事実の方は消さないこと。**
「なぜ前の数字と違うのか」を読む人が辿れなくなります。

---

## 同じターンで TODO.md / NEXT.md を更新する

長時間の計測は、**起動コマンドを打ったその同じターンで**記録します。
完了・中断・無効判明のときも同じ。

**会話で報告しても記録になりません。** 次のセッションが読むのは
`TODO.md`・`NEXT.md` だけで、そこが古いと「実行待ち」と誤読して
ビルドを重複起動します。

書くのは3つ:

1. **何が走っているか**（コマンドをそのまま。再実行できる形で）
2. **なぜ走らせているか**
3. **終わったら何を確認するか**

---

## コミット

計測結果の保存は 📊、ドキュメント反映は 📝、性能改善そのものは ⚡。

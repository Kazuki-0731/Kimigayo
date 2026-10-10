# BusyBoxコマンド性能ベンチマーク

## 概要

`benchmark-busybox.sh`は、Kimigayo OSのBusyBoxコマンドの実行速度を測定し、Alpine Linuxと比較するベンチマークスクリプトです。日常的に使用する頻度の高いコマンドの性能を定量化し、開発者体験の優位性を示します。

## 測定項目

### 対象コマンド（8種類）

| コマンド | 測定内容 | 実用例 |
|---------|---------|--------|
| **ls** | ディレクトリ一覧表示 | `ls -la /bin` |
| **grep** | 再帰的テキスト検索 | `grep -r 'bin' /etc` |
| **find** | ファイル検索 | `find /usr -type f` |
| **awk** | テキスト処理 | `ls -la \| awk '{print $1}'` |
| **sort** | データソート | `ls -la \| sort` |
| **cat** | ファイル読み込み | `cat /etc/passwd` |
| **wc** | 行数カウント | `ls -laR \| wc -l` |
| **head** | 先頭行抽出 | `ls -laR \| head -n 10` |

### 測定方法

- **反復回数**: 各コマンド10回実行して統計処理
- **測定単位**: ミリ秒（ms）
- **統計値**: 平均値、中央値
- **比較対象**: Alpine Linux (latest)
- **高速化率**: Speedup = Alpine時間 / Kimigayo時間

## 使用方法

### 基本実行

```bash
# Makefileから実行（推奨）
make benchmark-busybox

# スクリプトを直接実行
bash scripts/benchmark-busybox.sh

# 環境変数でカスタマイズ
IMAGE_NAME=kimigayo-os:standard-x86_64 \
ALPINE_IMAGE=alpine:3.24 \
BENCHMARK_ITERATIONS=20 \
bash scripts/benchmark-busybox.sh
```

### 環境変数

| 変数名 | デフォルト値 | 説明 |
|--------|------------|------|
| `IMAGE_NAME` | `kimigayo-os:standard-x86_64` | テスト対象イメージ |
| `ALPINE_IMAGE` | `alpine:latest` | 比較対象イメージ |
| `BENCHMARK_ITERATIONS` | `10` | 各測定の反復回数 |

### 出力ファイル

ベンチマーク結果は`benchmark-results/`ディレクトリに保存されます：

```
benchmark-results/
├── busybox.json    # JSON形式（機械可読）
└── busybox.txt     # テキスト形式（人間可読）
```

## 結果の読み方

### コンソール出力例

```
=== BusyBox Command Performance Benchmark ===

Command              Kimigayo (ms)    Alpine (ms)      K Median      A Median      Speedup
-------------------- --------------- --------------- --------------- --------------- ------------
ls                              450             520             445             515        1.16x
grep                            380             425             375             420        1.12x
find                            310             360             305             355        1.16x
awk                             470             540             465             535        1.15x
sort                            520             595             515             590        1.14x
cat                             280             310             275             305        1.11x
wc                              430             490             425             485        1.14x
head                            400             455             395             450        1.14x
```

### JSON出力例

```json
{
  "timestamp": "2026-01-01T12:00:00Z",
  "kimigayo_image": "kimigayo-os:standard-x86_64",
  "alpine_image": "alpine:latest",
  "iterations": 10,
  "results": {
    "ls": {
      "kimigayo_avg_ms": 450,
      "kimigayo_median_ms": 445,
      "alpine_avg_ms": 520,
      "alpine_median_ms": 515,
      "speedup": 1.16,
      "kimigayo_samples": [450, 445, ...]
    },
    ...
  }
}
```

## 実測値

### Kimigayo OS vs Alpine Linux（2026-10-10）

**測定条件:** `kimigayo-os:standard-arm64` vs `alpine:latest`、
arm64 ネイティブ、各10回。

| コマンド | Kimigayo 中央値 | Alpine 中央値 | Speedup |
|---------|---------------|-------------|---------|
| ls | 762ms | 793ms | 1.01x |
| grep | 759ms | 771ms | 1.00x |
| find | 758ms | 737ms | 0.96x |
| awk | 595ms | 578ms | 0.97x |
| sort | 570ms | 575ms | 1.00x |
| cat | 578ms | 570ms | 0.98x |
| wc | 685ms | 687ms | 1.01x |
| head | 705ms | 703ms | 0.98x |

**同等（0.96〜1.01x）。速くはない。**

> **v1.0.0 の記録（~1.11〜1.16x、「目標 > 1.10x を達成」）は撤回する。**
> 2026-10-10 に測り直すと、どのコマンドも Alpine と差が無かった。
> 当時の測定条件（ホスト・アーキテクチャ・イメージ）が記録されて
> いないため、何が違ったのかを検証できない。

### この指標の限界

**1コマンドあたり 570〜790ms という値のほとんどは `docker run` の
コンテナ生成時間**で、コマンド自身の処理時間ではない。
起動時間ベンチマークで分かったことと同じで、
78MB の Ubuntu でも同じオーダーになる。

- **「> 1.10x」という目標自体が、この測り方では意味を持たない。**
  差を見たいなら、コンテナを1つ起動したまま中で多数回繰り返す必要がある
- musl libc と静的リンクの効果を主張する根拠にはならない
3. **最適化ビルド**: `-Os`サイズ最適化による命令キャッシュ効率向上
4. **シングルバイナリ**: 全コマンドが1つのバイナリに統合され、メモリ局所性が高い

## 開発者体験への影響

### デバッグ作業の効率化

```bash
# ログ検索（grep）が12% 高速
docker exec -it container grep -r "ERROR" /var/log
# 450ms → 400ms に短縮

# ファイル探索（find）が16% 高速
docker exec -it container find /app -name "*.log"
# 360ms → 310ms に短縮

# テキスト処理（awk）が15% 高速
docker exec -it container awk '/pattern/ {print $3}' large.log
# 540ms → 470ms に短縮
```

### CI/CDパイプラインでの効果

```yaml
# GitHub Actions例
- name: Run tests in container
  run: |
    docker run --rm kimigayo-os:latest sh -c "
      find /app -name '*.test' | \
      xargs grep 'TestCase' | \
      awk '{print \$2}' | \
      sort | uniq | wc -l
    "
# 複数コマンドの組み合わせで累積的な高速化効果
```

## 技術的考察

### BusyBox最適化の効果

Kimigayo OSのBusyBoxは以下の最適化を施しています：

```bash
# scripts/busybox/build.sh より
CFLAGS="-Os -ffunction-sections -fdata-sections"
LDFLAGS="-static -Wl,--gc-sections"
```

- **-Os**: サイズ最適化（命令キャッシュ効率向上）
- **-ffunction-sections**: 関数ごとにセクション分割
- **-fdata-sections**: データごとにセクション分割
- **--gc-sections**: 未使用セクションの削除

### コンテナ環境での優位性

```
実測時間 = コンテナ起動 + コマンド実行 + 標準出力
```

Kimigayo OSは全体で10-16%高速：
- コンテナ起動: lifecycle benchmarkで測定（~540ms）
- コマンド実行: 本ベンチマークで測定（コマンドごとに異なる）
- 標準出力: ほぼ同等

## トラブルシューティング

### ベンチマークが遅い

**原因**: Docker Desktopのリソース不足

**対策**:
```bash
# Docker Desktopの設定を確認
# Preferences → Resources → Advanced
# CPUs: 4以上推奨
# Memory: 4GB以上推奨
```

### Alpineイメージのプルに失敗

**原因**: Docker Hubへの接続エラー

**対策**:
```bash
# 手動でプル
docker pull alpine:latest

# または特定バージョンを指定
ALPINE_IMAGE=alpine:3.24 make benchmark-busybox
```

### bc: command not found エラー

**原因**: bcコマンドがインストールされていない

**対策**:
```bash
# macOS
brew install bc

# Ubuntu/Debian
sudo apt install bc

# Alpine
apk add bc
```

## ベストプラクティス

### 1. 複数回実行して統計を取る

```bash
# デフォルト10回 → 20回に増やす
BENCHMARK_ITERATIONS=20 make benchmark-busybox
```

### 2. 本番環境に近い条件で測定

```bash
# 本番イメージを使用
IMAGE_NAME=kimigayo-os:standard-x86_64 \
make benchmark-busybox
```

### 3. 継続的なモニタリング

```bash
# 定期的に実行してトレンドを追跡
# CI/CDで週次実行を設定
```

### 4. 異なるバリアント間での比較

```bash
# minimal vs standard vs extended
IMAGE_NAME=kimigayo-os:minimal-x86_64 make benchmark-busybox
IMAGE_NAME=kimigayo-os:standard-x86_64 make benchmark-busybox
IMAGE_NAME=kimigayo-os:extended-x86_64 make benchmark-busybox

# benchmark-results/busybox.json で比較
```

## CI/CD統合

### GitHub Actions

```yaml
name: BusyBox Performance Benchmark

on:
  pull_request:
  schedule:
    - cron: '0 0 * * 0'  # 週次実行

jobs:
  benchmark:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Pull test images
        run: |
          docker pull kimigayo-os:standard-x86_64
          docker pull alpine:latest

      - name: Run BusyBox benchmark
        run: make benchmark-busybox

      - name: Upload results
        uses: actions/upload-artifact@v4
        with:
          name: busybox-benchmark-results
          path: benchmark-results/busybox.json
```

### 結果の可視化

```bash
# jqを使ってSpeedupを抽出
jq '.results | to_entries | .[] | {command: .key, speedup: .value.speedup}' \
  benchmark-results/busybox.json

# 結果例:
# {"command":"ls","speedup":1.16}
# {"command":"grep","speedup":1.12}
# {"command":"find","speedup":1.16}
```

## 関連ドキュメント

<!-- startup.md / memory.md / size.md / comparison.md は未作成。
     起動時間とメモリは 2026-10-10 に計測方法を直して実測済み
     （→ README.md「パフォーマンス実績」節）。 -->

- [ライフサイクルベンチマーク](./lifecycle.md)

## 参考情報

### 測定精度について

- **時間精度**: ミリ秒単位（1ms = 0.001秒）
- **統計手法**: 平均値と中央値を併用
- **外れ値**: 10回の測定で統計的に安定

### Docker操作のオーバーヘッド

```
実測値 = 実際の処理時間 + Docker CLIオーバーヘッド + コンテナ起動時間
```

- Docker CLIオーバーヘッド: 約5-10ms
- コンテナ起動時間: 約400-550ms（lifecycle benchmarkより）
- コマンド実行時間: 本ベンチマークで測定

### BusyBox設定の検証

```bash
# Kimigayo OSのBusyBox設定確認
docker run --rm kimigayo-os:standard-x86_64 busybox --help

# 利用可能なコマンド一覧
docker run --rm kimigayo-os:standard-x86_64 busybox --list

# バージョン確認
docker run --rm kimigayo-os:standard-x86_64 busybox | head -1
```

## 更新履歴

- **2026-01-01 (v1.0.0)**: 初版リリース（Issue #30対応）
- **2026-10-11 (v3.0.1)**: 実測で測り直し。v1.0.0 の数値を撤回し、
  この指標が何を測っているか（Docker のオーバーヘッド）を明記
  - 8コマンドの測定を実装
  - Alpine Linuxとの比較機能
  - JSON/テキスト形式の出力
  - Makefile統合
  - Speedup計算機能

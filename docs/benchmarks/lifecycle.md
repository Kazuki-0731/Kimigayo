# コンテナライフサイクルベンチマーク

## 概要

`benchmark-lifecycle.sh`は、Kimigayo OSのコンテナライフサイクル全体の性能を測定するベンチマークスクリプトです。CI/CD、Kubernetes、本番環境での実用的な性能指標を提供します。

## 測定項目

### 1. Run-to-completion時間
**概要**: コンテナの起動から終了までの完全なサイクル時間

**測定内容**:
```bash
docker run --rm kimigayo-os:latest /bin/sh -c "echo 'test' && sleep 0.1"
```

**重要性**:
- CI/CDパイプラインでの各ステップ実行時間
- 短時間タスクのオーバーヘッド測定
- テスト実行環境の性能評価

### 2. コンテナ起動時間
**概要**: コンテナ作成からプロセス起動までの時間

**測定内容**:
```bash
docker create + docker start
```

**重要性**:
- Kubernetesでのpod起動速度
- オートスケーリング応答時間
- 障害復旧時間

### 3. コンテナ停止時間
**概要**: 実行中コンテナを安全に停止するまでの時間

**測定内容**:
```bash
docker stop (SIGTERM処理時間)
```

**重要性**:
- グレースフルシャットダウン性能
- ローリングアップデート時のダウンタイム
- リソース解放速度

### 4. コンテナ再起動時間
**概要**: 既存コンテナを再起動する時間

**測定内容**:
```bash
docker restart (stop + start)
```

**重要性**:
- 設定変更後の再起動時間
- ヘルスチェック失敗時の自動復旧
- メンテナンス作業の所要時間

### 5. コンテナクリーンアップ時間
**概要**: コンテナを強制削除する時間

**測定内容**:
```bash
docker rm -f
```

**重要性**:
- CI/CD後のクリーンアップ速度
- リソース回収効率
- ビルドパイプライン全体の時間

### 6. イメージ情報
**概要**: イメージサイズ、レイヤー数

**測定内容**:
- イメージサイズ（MB）
- レイヤー数

**重要性**:
- ディスク使用量
- プル時間への影響
- キャッシュ効率

### 7. イメージプル時間（ウォームキャッシュ）
**概要**: キャッシュ済みイメージの再プル時間

**測定内容**:
```bash
docker pull (already up to date)
```

**重要性**:
- CI/CDでのキャッシュ活用
- デプロイ時間の予測
- ネットワーク負荷

## 使用方法

### 基本実行

```bash
# Makefileから実行（推奨）
make benchmark-lifecycle

# スクリプトを直接実行
bash scripts/benchmark-lifecycle.sh

# 環境変数でカスタマイズ
IMAGE_NAME=ishinokazuki/kimigayo-os:3.0.1 \
BENCHMARK_ITERATIONS=20 \
bash scripts/benchmark-lifecycle.sh
```

### 環境変数

| 変数名 | デフォルト値 | 説明 |
|--------|------------|------|
| `IMAGE_NAME` | `ishinokazuki/kimigayo-os:latest` | テスト対象イメージ |
| `BENCHMARK_ITERATIONS` | `10` | 各測定の反復回数 |

### 出力ファイル

ベンチマーク結果は`benchmark-results/`ディレクトリに保存されます：

```
benchmark-results/
├── lifecycle_20260101_120000.json    # JSON形式（機械可読）
└── lifecycle_20260101_120000.txt     # テキスト形式（人間可読）
```

## 結果の読み方

### コンソール出力例

```
=== Container Lifecycle Benchmark ===
Image: kimigayo-os:standard-arm64
Iterations: 10

Metric                                 Average (ms)     Median (ms)
----------------------------------- --------------- ---------------
Run-to-completion                               699             696
Container start                                 561             556
Container stop                                10368           10365
Container restart                             10643           10645
Container cleanup                               299             298
Image pull (warm cache)                        2258            2282

Image size (MB)                                3.13
Layer count                                       2
```

（2026-10-11 実測。stop / restart の 10 秒は Docker の猶予時間 →
上の「stop と restart の 10 秒は Kimigayo のせいではない」節）

### JSON出力例

```json
{
  "timestamp": "2026-10-11T00:52:00Z",
  "image": "kimigayo-os:standard-arm64",
  "iterations": 10,
  "results": {
    "run_to_completion": {
      "average_ms": 699,
      "median_ms": 696,
      "samples": [696, 701, 712, ...]
    },
    ...
  }
}
```

## パフォーマンス目標

### Kimigayo OS目標値

### 実測値（2026-10-11、v3.0.1）

**測定条件:** `kimigayo-os:standard-arm64`、macOS / Apple Silicon、
arm64 ネイティブ、10回（warm pull のみ3回）の中央値。

| 項目 | 中央値 | 何を測っているか |
|------|--------|----------------|
| Run-to-completion | 696ms | `docker run --rm` が返るまで |
| Container start | 556ms | `docker run -d` が返るまで |
| Container stop | **10,365ms** | **Docker の猶予時間**（下記）|
| Container restart | **10,645ms** | 同上（stop を含む）|
| Container cleanup | 298ms | `docker rm` |
| Image pull (warm) | 2,282ms | キャッシュ済みの `docker pull` |

### stop と restart の 10 秒は Kimigayo のせいではない

**`docker stop` は PID 1 に SIGTERM を送り、10 秒待ってから SIGKILL します。**
カーネルは **PID 1 についてはハンドラの無いシグナルを無視する**ので、
`sleep 60` を PID 1 で動かしているこのベンチマークでは必ず猶予時間を
使い切ります。

同じ条件で測った比較（2026-10-11）:

| | `sleep 60` を PID 1 | SIGTERM を `trap` する `sh` |
|---|---|---|
| Kimigayo Standard | 10,388ms | **665ms** |
| `alpine:latest` | 10,379ms | **667ms** |

**Alpine と 9ms しか違いません。** この数値はイメージの性質ではなく、
PID 1 のシグナル処理の性質です。

> **v1.0.0 の記録「Container stop < 150ms（~125ms）✅ 達成」は撤回します。**
> この測り方では出ない値です。同じ記録にあった
> run-to-completion ~234ms・start ~89ms も、現在の実測
> （696ms / 556ms）と桁が合いません。測定条件が残っていないため
> 何が違ったのか検証できません。

### 利用者向けの実用上の注意

**アプリケーションが SIGTERM を処理しないと、`docker stop` と
Kubernetes の Pod 終了に毎回 10 秒かかります。**
これは Kimigayo に限らずどのイメージでも同じですが、
Kimigayo は Init（OpenRC）を持つので選択肢があります。

```dockerfile
# アプリを PID 1 にするなら、SIGTERM を処理する
CMD ["/app/server"]        # server 側で SIGTERM を受けて終了する

# シェル経由にするなら exec を使う（sh が PID 1 に残らないようにする）
CMD ["/bin/sh", "-c", "exec /app/server"]
```

猶予時間を縮めるならホスト側で指定します。

```bash
docker stop --timeout 2 <container>
docker run --stop-timeout 2 ...
```

### 他OSとの比較

**ライフサイクルの時間はイメージでは変わりません。**
2026-10-11 に arm64 ネイティブで測った比較（10回の中央値）:

| OS | 起動（`docker run`）| 常駐メモリ | イメージサイズ |
|----|------------------|-----------|---------------|
| **Kimigayo Standard** | 613ms | **232KB** | 3.13MB |
| `alpine:latest` | 616ms | 276KB | 8.66MB |
| `ubuntu:24.04` | 589ms | 312KB | 100.81MB |
| `gcr.io/distroless/static-debian12` | 測定不可（実行ファイル無し）| — | 2.11MB |

**100MB の Ubuntu が最速に出ています。** 測っている時間のほとんどが
Docker 自身のコンテナ生成なので、イメージサイズは効きません。
差が出るのは常駐メモリとサイズの方です。

> **旧表（Kimigayo 234ms / Alpine 245ms / Ubuntu 890ms）は撤回します。**
> Ubuntu が 890ms という値は再現しません（実測 589ms）。
> 測定条件が記録されておらず、検証できません。

## CI/CD統合

### GitHub Actions

```yaml
name: Lifecycle Benchmark

on:
  pull_request:
  schedule:
    - cron: '0 0 * * 0'  # 週次実行

jobs:
  benchmark:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Pull test image
        run: docker pull ishinokazuki/kimigayo-os:latest

      - name: Run lifecycle benchmark
        run: make benchmark-lifecycle

      - name: Upload results
        uses: actions/upload-artifact@v4
        with:
          name: lifecycle-benchmark-results
          path: benchmark-results/lifecycle_*.json
```

### Kubernetes環境での活用

```yaml
# Deployment起動時間の予測
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: app
        image: ishinokazuki/kimigayo-os:3.0.1
        livenessProbe:
          initialDelaySeconds: 1
          periodSeconds: 5
        # **SIGTERM を処理しないと Pod の終了に 30 秒かかります**
        # （Kubernetes の既定の terminationGracePeriodSeconds）。
        # アプリ側で SIGTERM を受けて終了するのが本筋です。
      terminationGracePeriodSeconds: 5
```

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

### イメージプルに失敗

**原因**: Docker Hubへの接続エラー

**対策**:
```bash
# ローカルイメージを使用
IMAGE_NAME=kimigayo-os:local bash scripts/benchmark-lifecycle.sh

# または手動でプル
docker pull ishinokazuki/kimigayo-os:3.0.1
```

### 権限エラー

**原因**: Dockerデーモンへのアクセス権限不足

**対策**:
```bash
# ユーザーをdockerグループに追加
sudo usermod -aG docker $USER

# ログアウト→ログインして反映
```

## ベストプラクティス

### 1. 複数回実行して統計を取る

```bash
# デフォルト10回 → 20回に増やす
BENCHMARK_ITERATIONS=20 make benchmark-lifecycle
```

### 2. 本番環境に近い条件で測定

```bash
# 本番イメージを使用
IMAGE_NAME=ishinokazuki/kimigayo-os:3.0.1-minimal \
make benchmark-lifecycle
```

### 3. 継続的なモニタリング

```bash
# 定期的に実行してトレンドを追跡
# CI/CDで週次実行を設定
```

### 4. 結果の比較

```bash
# 異なるバージョン間での比較
IMAGE_NAME=ishinokazuki/kimigayo-os:0.9.0 make benchmark-lifecycle
IMAGE_NAME=ishinokazuki/kimigayo-os:3.0.1 make benchmark-lifecycle

# benchmark-results/ディレクトリで比較
diff benchmark-results/lifecycle_*.txt
```

## 関連ドキュメント

<!-- startup.md / memory.md / size.md / comparison.md は未作成。
     起動時間とメモリは 2026-10-10 に計測方法を直して実測済み
     （→ README.md「パフォーマンス実績」節）。 -->


## 参考情報

### 測定精度について

- **時間精度**: ミリ秒単位（1ms = 0.001秒）
- **統計手法**: 平均値と中央値を併用
- **外れ値**: 10回の測定で統計的に安定

### Docker操作のオーバーヘッド

```
実測値 = 実際の処理時間 + Docker CLIオーバーヘッド
```

Docker CLIのオーバーヘッドは約5-10ms程度です。

### Kubernetes環境での補正

Kubernetesでは追加のオーバーヘッドがあります：

- kubelet処理: ~50ms
- CNIネットワーク設定: ~30ms
- ストレージマウント: ~20ms

**合計**: ベンチマーク値 + 約100ms

## 更新履歴

- **2026-01-01 (v1.0.0)**: 初版リリース（Issue #29対応）
- **2026-10-11 (v3.0.1)**: 実測で測り直し。v1.0.0 の数値を撤回し、
  この指標が何を測っているか（Docker のオーバーヘッド）を明記
  - 7項目の測定を実装
  - JSON/テキスト形式の出力
  - Makefile統合
  - 統計計算（平均、中央値）

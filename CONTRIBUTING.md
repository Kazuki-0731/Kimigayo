# Contributing to Kimigayo OS

Kimigayo OSへの貢献に興味を持っていただきありがとうございます！このドキュメントでは、プロジェクトへの貢献方法について説明します。

## 開発環境のセットアップ

### 必要な環境

- Docker（`docker compose` が使えること）
- Git
- Docker に割り当てるメモリ: arm64 のクロスビルドまで回すなら 8GB
  （`docker-compose.yml` の上限。2GB では OpenRC の `meson setup` が OOM で落ちたことがある）

### セットアップ手順

1. リポジトリをクローン:
```bash
git clone https://github.com/Kazuki-0731/Kimigayo.git
cd Kimigayo
```

2. Docker環境を構築:
```bash
make docker-build
```

3. コンテナに入る:
```bash
make shell
```

4. ビルドシステムをテスト（コンテナ内で）:
```bash
make test
```

## 開発ワークフロー

### ブランチ戦略

現在はメンテナー 1 人で、ブランチは `main` だけです（`develop` はありません）。
外部からの貢献は、fork した上で任意の名前のブランチを切り、`main` に向けて
Pull Request を出してください。

### コミットメッセージ

**日本語で書き、先頭に絵文字を1つ置く。`feat:` のようなテキスト
プレフィックスは付けない。**

#### フォーマット

```
<絵文字> <何をしたか>

<なぜそうしたか。何を変えたかは diff を見れば分かる>
```

絵文字は先頭に1つだけで、`✨ feat: ...` のように併記しない。
テキストプレフィックスが付いているコミットは 1 件だけです
（2026-10-12 時点、723 コミット中。それが例外）。

#### 絵文字の一覧

| 種類 | 絵文字 | | 種類 | 絵文字 |
| --- | --- | --- | --- | --- |
| 機能追加 | ✨ | | リファクタ | ♻️ |
| バグ修正 | 🐛 | | テスト | ✅ |
| ドキュメント・記録 | 📝 | | 取り消し | ⏪ |
| 雑務・設定 | 🔧 | | マージ | 🔀 |
| 性能改善 | ⚡ | | 統計・計測の保存 | 📊 |
| 依存・バージョン更新 | ⬆️ | | 片付け・削除 | 🧹 |
| Docker 関連 | 🐳 | | セキュリティ | 🔒 |

**どれにも当てはまらないものは 📌。**

#### コミット例

**新機能追加:**
```
✨ パッケージマネージャーが入っていないことを検査する

- verify-image.sh にアプレット一覧とパスの両方を見る検査を追加
- apk / apt / opkg / yum / dnf / pacman も同じ検査に載せる
- 検査項目は 28 → 29 になる
```

**バグ修正:**
```
🐛 rootfs 最適化の算術式エラーを修正

scripts/build-rootfs.sh:234でゼロ除算が発生していた問題を修正
```

**セキュリティ修正:**
```
🔒 dpkg / rpm がイメージに入っていた

BusyBox の既定が有効なため、config に書かなければ入ってしまう
```

**ドキュメント:**
```
📝 CONTRIBUTING.md のコミット規約を実態に合わせる

テキストプレフィックスは 1 件しか使われていなかった
```

#### CHANGELOG

**`CHANGELOG.md` は手で書きます。** コミットの件名は「何を変えたか」しか
持っていませんが、`CHANGELOG.md` には「なぜ」が必要です。

```bash
make changelog     # build/CHANGELOG.generated.md に下書きを出す
```

このコマンドは**下書きを `build/` に出すだけ**で、`CHANGELOG.md` は
書き換えません（2026-10-11 までは `CHANGELOG.md` を丸ごと上書きする
作りで、手で書いた内容が消える状態でした）。使える行をコピーして、
理由を足してください。

表に無い絵文字のコミットは `Uncategorized` に入ります（黙って
落とさないため）。

## コーディング規約

このリポジトリに C のソースはありません（構成要素は上流の tarball に
パッチを当ててビルドします）。書くのは主にシェルスクリプトと Python です。

### シェルスクリプト（`scripts/`）

- `#!/bin/bash` と `set -e` / `set -o pipefail` で始める
- ログは既存のスクリプトと同じ `log_info` / `log_warn` / `log_error`（JST タイムスタンプ付き）を使う。
  新しいスクリプトは既存の `scripts/*.sh` から雛形を取る
- `make shellcheck-scan` を通す（CI でも走る）
- 構成要素のバージョンを直書きしない（`scripts/lib/versions.sh` 経由で `versions.mk` を読む）
- 失敗を `|| true` や `-Wno-error` で黙らせない

### Python（`src/`・`tests/`）

- PEP 8 に準拠（インデント 4 スペース、関数名 `snake_case`、クラス名 `PascalCase`）
- テストは pytest。プロパティテストは hypothesis（設定は `tests/conftest.py` のプロファイル）
- マーカーは `pytest.ini` に定義済みのもの（`unit`・`property`・`integration`・`slow`・`security`）
  だけを使う（`--strict-markers`）

### セキュリティ

- コンパイル時の強化フラグ（`scripts/build-{musl,busybox,openrc}.sh`）を緩めない
- 成果物の強化は `scripts/verify-image.sh` が全 ELF で検査する（PIE・RELRO・BIND_NOW・非実行スタック）

## テスト

### プロパティベーステスト

新しい機能にはプロパティテストを足してください。実物の例
（`tests/property/test_build_constraints.py` の抜粋）:

```python
# **Feature: kimigayo-os-core, Property 1: ビルドサイズ制約**
@pytest.mark.property
@given(build_config=build_configurations())  # 同じファイルで定義した strategy
def test_build_size_constraint(build_config, tmp_path):
    """任意のビルド設定に対して、イメージはバリアントの上限未満
    （MINIMAL 5MB / STANDARD 15MB / EXTENDED 50MB。SPECIFICATION.md §8.3）"""
    image = build_base_image(build_config, output_dir=tmp_path)
    assert image.size_bytes < build_config.max_image_size
```

### テスト実行

```bash
# 全テスト実行
make test

# プロパティテストのみ
pytest tests/property/

# 単体テストのみ
pytest tests/unit/

# 統合テスト（Docker が必要）
make test-integration
```

## プルリクエスト

### プルリクエストの作成

1. fork した上で `main` から新しいブランチを作成
2. 変更を実装
3. テストを追加・更新
4. すべてのテストが通ることを確認
5. プルリクエストを作成

### プルリクエストのチェックリスト

- [ ] すべてのテストが通る
- [ ] 新機能にはプロパティテストを追加
- [ ] ドキュメントを更新
- [ ] コミットメッセージが規約に準拠
- [ ] セキュリティ要件を満たす
- [ ] ビルドサイズへの影響を確認

## ライセンス

ビルドシステム・ドキュメント・テストへの貢献は MIT ライセンスに従います（→ [LICENSE](LICENSE)）。
上流の構成要素（BusyBox・musl・OpenRC・カーネル）に当てるパッチは、その構成要素のライセンスに従います。

## サポート

質問や提案がある場合は、以下の方法でお問い合わせください:

- GitHub Issues: バグレポート、機能リクエスト
- GitHub Discussions: 一般的な質問、アイデア

---

貢献に感謝します！🙏

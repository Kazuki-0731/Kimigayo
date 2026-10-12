# Kimigayo OS Tests

## 構造

```
tests/
├── conftest.py         # Pytest設定とフィクスチャ（hypothesis のプロファイルもここ）
├── fixtures/           # テスト用のデータ
├── unit/               # 単体テスト（344 件、2026-10-13 時点）
├── property/           # プロパティベーステスト（255 件、同）
└── integration/        # 統合テスト
```

## テスト実行

### すべてのテスト

```bash
make test        # ビルドコンテナ内で pytest tests/ -v
# または（ホストで、pip install -r requirements-dev.txt のあと）
pytest
```

`make test-unit` / `make test-property` はビルドコンテナ側（`build-system/Makefile`）の
ターゲットです。ホストで叩くと `No rule to make target` になるので、
`make shell` で入ってから叩くか、ホストでは `pytest` を直接使います。

### 単体テストのみ

```bash
make test-unit           # ビルドコンテナ内
# または
pytest tests/unit/
```

### プロパティテストのみ

```bash
make test-property       # ビルドコンテナ内
# または
pytest tests/property/ -v --hypothesis-show-statistics
```

### 統合テストのみ

```bash
pytest tests/integration/
```

**ホストの `make test-integration` はこれと同じではありません。**
`tests/integration/test_phase1_integration.py` だけを回し、
`output/` に rootfs の tarball があるかを確かめます（`make ci-build-local` の一段）。
シェルの統合テストは `make test-docker`（`test_docker_startup.sh`）と
`make test-func`（`test_functionality.sh`）で、どちらもイメージが要ります。
検査するイメージは `kimigayo-os:<variant>-<arch>`（`make ci-build-local` が作る名前）で、
Makefile が `VARIANT` / `ARCH` / `VERSION` を渡します
（`make test-docker VARIANT=minimal ARCH=arm64`）。スクリプトを直接叩くときも
`IMAGE_NAME` を省けば同じ名前が既定になります。

ビルドコンテナ側の `make test-musl` / `test-busybox` / `test-openrc`
（`scripts/test-*-integration.sh`）は、ビルド済みの構成要素
（`build/*-install-*`）を検査します。

### 特定のマーカー

```bash
# セキュリティテストのみ
pytest -m security

# スローテストを除外
pytest -m "not slow"
```

## プロパティベーステスト

プロパティテストは次の形式で書きます（既存のファイルには、見出しコメントが
この形式に揃っていないものもあります。「要件 1.1」などの番号が指す要件定義の
文書はリポジトリにありません）:

```python
# tests/property/test_build_constraints.py（抜粋）
# **Feature: kimigayo-os-core, Property 1: ビルドサイズ制約**
# **検証対象: 要件 1.1**
@pytest.mark.property
@given(build_config=build_configurations())  # 同じファイルで定義した strategy
def test_build_size_constraint(build_config, tmp_path):
    """任意のビルド設定に対して、イメージはバリアントの上限未満
    （MINIMAL 5MB / STANDARD 15MB / EXTENDED 50MB。SPECIFICATION.md §8.3）"""
    image = build_base_image(build_config, output_dir=tmp_path)
    assert image.size_bytes < build_config.max_image_size
```

### Hypothesis設定

`tests/conftest.py` にプロファイルがあります（`deadline` はすべて無効）。

- `kimigayo`（デフォルト）: 100回の反復
- `ci`: 200回の反復
- `dev`: 50回の反復

環境変数で切り替えます:
```bash
HYPOTHESIS_PROFILE=ci pytest
```

**CI（`ci.yml`）は `HYPOTHESIS_PROFILE` を設定していない**ので、CI でも 100 回です。

## カバレッジ

```bash
pytest --cov=src --cov-report=html
```

レポートは `htmlcov/index.html` に生成されます。

## 継続的インテグレーション

GitHub Actions（`ci.yml` の Tests ジョブ）が、`main` への push と PR で
`pytest tests/unit tests/property -q` を回します。

- `tests/integration/` の pytest とカバレッジ測定は CI では回していません
- イメージの検証は pytest ではなく `scripts/verify-image.sh` が、variant × arch の
  ビルドごとに行います
- スケジュール実行はセキュリティスキャン（`security.yml`・`dependency-review.yml`）です

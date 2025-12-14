# Kimigayo OS Tests

## 構造

```
tests/
├── conftest.py         # Pytest設定とフィクスチャ
├── unit/               # 単体テスト
├── property/           # プロパティベーステスト
└── integration/        # 統合テスト
```

## テスト実行

### すべてのテスト

```bash
make test
# または
pytest
```

### 単体テストのみ

```bash
make test-unit
# または
pytest tests/unit/
```

### プロパティテストのみ

```bash
make test-property
# または
pytest tests/property/ -v --hypothesis-show-statistics
```

### 統合テストのみ

```bash
make test-integration
# または
pytest tests/integration/
```

### 特定のマーカー

```bash
# セキュリティテストのみ
pytest -m security

# スローテストを除外
pytest -m "not slow"
```

## プロパティベーステスト

すべてのプロパティテストは以下の形式に従います:

```python
# **Feature: kimigayo-os-core, Property 1: ビルドサイズ制約**
# **検証対象: 要件 1.1**

from hypothesis import given
import hypothesis.strategies as st

@given(build_config=st.builds(BuildConfig))
def test_build_size_constraint(build_config):
    """任意のビルド設定に対して、Base_Imageは5MB未満"""
    image = build_base_image(build_config)
    assert image.size_bytes < 5 * 1024 * 1024
```

### Hypothesis設定

- デフォルト: 100回の反復
- CI環境: 200回の反復
- 開発環境: 50回の反復

環境変数で設定:
```bash
HYPOTHESIS_PROFILE=ci pytest
```

## カバレッジ

```bash
pytest --cov=src --cov-report=html
```

レポートは `htmlcov/index.html` に生成されます。

## 継続的インテグレーション

GitHub Actionsで自動的に実行されます:

- プッシュ時: すべてのテスト
- プルリクエスト時: すべてのテスト + カバレッジ
- スケジュール: セキュリティスキャン

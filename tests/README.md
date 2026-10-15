# Kimigayo OS Tests

## 構造

```
tests/
├── unit/               # 単体テスト（pytest。3 ファイル 65 件、2026-10-14 時点）
└── integration/        # 統合テスト（シェル。Docker のイメージが要る）
```

| ファイル | 何を見るか |
| --- | --- |
| `unit/test_busybox_config_explicit.py` | BusyBox の config で「既定値に任せると危ない項目」（`DPKG`・`RPM`・`FEATURE_PATH_TRAVERSAL_PROTECTION` など）が明示されているか |
| `unit/test_check_links.py` | `scripts/check-links.py`（リンク切れ検査）の判定 |
| `unit/test_memo_paths.py` | `.claude/hooks/memo-paths.py`（メモ・下書きファイルの判定）の規則 |
| `integration/test_docker_startup.sh` | イメージの起動 |
| `integration/test_functionality.sh` | BusyBox・ネットワークなどの機能 |

以前あったプロパティテスト（hypothesis）と、`src/` の Python モジュールを
検証していたテストは 2026-10-14 に削除しました（どのスクリプト・Makefile・
ワークフローからも使われていないモックだったため）。カバレッジ測定も
していません。

## テスト実行

### 単体テスト

```bash
make test                # ビルドコンテナ内で pytest tests/ -v
make test-unit           # ビルドコンテナ内で pytest tests/unit/ -v
# または（ホストで、pip install -r requirements-dev.txt のあと）
python3 -m pytest tests -q
```

`make test-unit` はビルドコンテナ側（`build-system/Makefile`）のターゲットです。
ホストで叩くと `No rule to make target` になるので、`make shell` で入ってから叩くか、
ホストでは `pytest` を直接使います。

### 特定のマーカー

マーカーは `pytest.ini` に定義した `unit`・`integration`・`slow`・`security`
だけです（`--strict-markers`）。

```bash
pytest -m security
pytest -m "not slow"
```

### 統合テスト（シェル）

`make test-docker`（`test_docker_startup.sh`）と
`make test-func`（`test_functionality.sh`）で、どちらもイメージが要ります。
検査するイメージは `kimigayo-os:<variant>-<arch>`（`make ci-build-local` が作る名前）で、
Makefile が `VARIANT` / `ARCH` / `VERSION` を渡します
（`make test-docker VARIANT=minimal ARCH=arm64`）。スクリプトを直接叩くときも
`IMAGE_NAME` を省けば同じ名前が既定になります。

**ホストの `make test-integration` はこれらとは別物です。**
`output/` に rootfs の tarball があるかを確かめるだけです
（`make ci-build-local` の一段）。

ビルドコンテナ側の `make test-musl` / `test-busybox` / `test-openrc`
（`scripts/test-*-integration.sh`）は、ビルド済みの構成要素
（`build/*-install-*`）を検査します。

## 継続的インテグレーション

GitHub Actions（`build-and-verify.yml` の Tests ジョブ）が、`main` への push と PR で
`pytest tests/unit -q` を回します。

- `tests/integration/` のシェルは CI では回していません
- イメージの検証は pytest ではなく `scripts/verify-image.sh` が、variant × arch の
  ビルドごとに行います
- スケジュール実行はセキュリティスキャン（`security.yml`・`dependency-review.yml`）です

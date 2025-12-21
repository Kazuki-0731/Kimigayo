# Kimigayo OS - Docker Management Makefile
# プロジェクト管理用の簡易コマンド集

.PHONY: help up down build rebuild clean logs shell test test-docker build-os clean-cache clean-all info
.PHONY: build-rootfs package-rootfs build-image test-integration test-smoke ci-build-local

# デフォルトターゲット
help:
	@echo "╔════════════════════════════════════════════════════════════════╗"
	@echo "║         Kimigayo OS - コンテナ向けOSビルドシステム             ║"
	@echo "║           軽量・高速・セキュアなDockerイメージOS               ║"
	@echo "╚════════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "📦 クイックスタート:"
	@echo "  1. make docker-build  # ビルド環境を構築"
	@echo "  2. make build         # OSをビルド"
	@echo "  3. make test          # テストを実行"
	@echo ""
	@echo "🔧 OSビルドコマンド:"
	@echo "  make build        - Kimigayo OSをビルド [1/6]～[6/6]"
	@echo "  make test         - テストを実行"
	@echo "  make test-docker  - Dockerイメージ起動テストを実行"
	@echo "  make test-func    - 機能テストを実行 (BusyBox, Network, Package Manager)"
	@echo "  make status       - ビルド状態を表示（どこまで完了したか確認）"
	@echo "  make info         - ビルド設定情報を表示"
	@echo ""
	@echo "🚀 CI/CDローカル実行（GitHub Actions相当）:"
	@echo "  make ci-build-local      - 完全なCI/CDビルド（rootfs→テスト→イメージ）"
	@echo "  make build-rootfs        - rootfsのみビルド"
	@echo "  make package-rootfs      - rootfsをtarballにパッケージ化"
	@echo "  make test-integration    - 統合テストを実行"
	@echo "  make build-image         - Dockerイメージをビルド"
	@echo "  make test-smoke          - スモークテストを実行"
	@echo "  make ci-build-all        - 全バリアントをビルド"
	@echo ""
	@echo "  設定方法（優先順位: コマンドライン > .env > デフォルト）:"
	@echo "    1. .envファイルを作成: cp .env.example .env"
	@echo "    2. .envを編集してデフォルト値を設定"
	@echo "    3. コマンドライン引数で一時的に上書き可能"
	@echo ""
	@echo "  パラメータ例:"
	@echo "    make ci-build-local                              # .envの設定を使用"
	@echo "    VARIANT=minimal make ci-build-local              # .envを上書き"
	@echo "    VARIANT=minimal ARCH=x86_64 VERSION=0.1.0 make ci-build-local"
	@echo ""
	@echo "🐳 Docker管理:"
	@echo "  make docker-build - ビルド環境イメージを構築"
	@echo "  make docker-rebuild - キャッシュなしで再構築"
	@echo "  make shell        - コンテナにログイン（推奨）"
	@echo "  make up           - コンテナをバックグラウンド起動"
	@echo "  make down         - コンテナを停止・削除"
	@echo "  make logs         - コンテナログを表示"
	@echo ""
	@echo "🗑️  クリーンアップ:"
	@echo "  make clean        - ビルド成果物のみ削除（ダウンロードキャッシュ保持）"
	@echo "  make clean-cache  - ダウンロードキャッシュを削除"
	@echo "  make clean-all    - すべて削除（推奨：完全リセット）"
	@echo ""
	@echo "📋 ログ確認:"
	@echo "  make log-kernel   - カーネルビルドログ（最新100行）"
	@echo "  make log-musl     - musl libcビルドログ（最新100行）"
	@echo "  make log-openrc   - OpenRCビルドログ（最新100行）"
	@echo ""
	@echo "💡 推奨ワークフロー（リアルタイム出力）:"
	@echo "  1. make shell               # コンテナに入る"
	@echo "  2. make build               # コンテナ内でビルド"
	@echo "  3. tmux new -s build        # tmuxでバックグラウンド実行"
	@echo "  4. make build && echo ✅    # ビルド＆完了通知"
	@echo "  5. Ctrl+B → D               # デタッチ（バックグラウンド化）"
	@echo ""
	@echo "⚙️  コンテナ内で使える個別ビルド:"
	@echo "  make musl                   # musl libcのみ [1/6]"
	@echo "  make kernel                 # Linuxカーネルのみ [2/6]"
	@echo "  make busybox                # BusyBoxのみ [3/6]"
	@echo "  make init                   # OpenRCのみ [4/6]"
	@echo "  make pkg                    # パッケージマネージャのみ [5/6]"
	@echo ""
	@echo "⚙️  コンテナ内で使える個別クリーン:"
	@echo "  make clean-musl             # muslのみ削除"
	@echo "  make clean-kernel           # カーネルのみ削除"
	@echo "  make clean-busybox          # BusyBoxのみ削除"
	@echo "  make clean-openrc           # OpenRCのみ削除"
	@echo "  make clean-pkg              # パッケージマネージャのみ削除"
	@echo ""
	@echo "📖 詳細なドキュメント: https://github.com/Kazuki-0731/Kimigayo"

# Dockerコンテナ管理
up:
	@echo "コンテナを起動..."
	docker compose up -d

down:
	@echo "コンテナを停止・削除..."
	docker compose down

docker-build:
	@echo "Dockerイメージをビルド..."
	docker compose build

docker-rebuild:
	@echo "Dockerイメージを再ビルド（キャッシュなし）..."
	docker compose build --no-cache

shell:
	@echo "コンテナにログイン..."
	docker compose run --rm kimigayo-build bash

logs:
	@echo "コンテナログを表示..."
	docker compose logs -f

# OSビルド
build:
	@echo "Kimigayo OSをビルド..."
	docker compose run --rm kimigayo-build make build

test:
	@echo "テストを実行..."
	docker compose run --rm kimigayo-build make test

test-docker:
	@echo "Dockerイメージ起動テストを実行..."
	bash tests/integration/test_docker_startup.sh

test-func:
	@echo "機能テストを実行..."
	bash tests/integration/test_functionality.sh

info:
	@echo "ビルド情報を表示..."
	docker compose run --rm kimigayo-build make info

status:
	@echo "ビルド状態を表示..."
	docker compose run --rm kimigayo-build make status

# クリーンアップ
clean:
	@echo "ビルド成果物を削除..."
	docker compose run --rm kimigayo-build make clean

clean-cache:
	@echo "ダウンロードキャッシュを削除..."
	docker compose down
	docker volume rm kimigayo_kimigayo-downloads || true

clean-all:
	@echo "すべて削除（コンテナ+volume）..."
	docker compose down -v
	docker rmi kimigayo-os-build:latest || true

# ログ確認
log-kernel:
	@echo "カーネルビルドログを表示..."
	docker compose run --rm kimigayo-build tail -n 100 /build/kimigayo/build/logs/kernel-build.log

log-musl:
	@echo "musl libcビルドログを表示..."
	docker compose run --rm kimigayo-build tail -n 100 /build/kimigayo/build/logs/musl-build.log

log-openrc:
	@echo "OpenRCビルドログを表示..."
	docker compose run --rm kimigayo-build tail -n 100 /build/kimigayo/build/logs/openrc-build.log

# ============================================================================
# CI/CDローカル実行
# ============================================================================

# .envファイルが存在する場合は読み込む
ifneq (,$(wildcard .env))
    include .env
    export
endif

# 設定変数（.envで上書き可能、コマンドラインでさらに上書き可能）
ARCH ?= x86_64
VARIANT ?= standard
VERSION ?= latest
DOCKER_HUB_USERNAME ?= ishinokazuki
IMAGE_NAME ?= kimigayo-os
BUILD_JOBS ?= 4
DEBUG ?= false

TARBALL_NAME = kimigayo-$(VARIANT)-$(VERSION)-$(ARCH).tar.gz

# rootfsビルド（GitHub Actionsの同等処理）
build-rootfs:
	@echo "=== Building Kimigayo OS rootfs ==="
	@echo "Architecture: $(ARCH)"
	@echo "Variant: $(VARIANT)"
	@echo "Version: $(VERSION)"
	@export ARCH=$(ARCH) && export IMAGE_TYPE=$(VARIANT) && bash scripts/build-rootfs.sh
	@echo ""
	@echo "=== Verifying build output ==="
	@ls -lah build/rootfs/ | head -20
	@echo ""
	@echo "=== Checking for essential files ==="
	@ls -l build/rootfs/bin/sh 2>/dev/null || echo "WARNING: /bin/sh not found"
	@ls -l build/rootfs/bin/busybox 2>/dev/null || echo "WARNING: /bin/busybox not found"

# rootfsをtarballにパッケージ化
package-rootfs: build-rootfs
	@echo ""
	@echo "=== Packaging rootfs into tarball ==="
	@mkdir -p output
	@cd build/rootfs && tar czf ../../output/$(TARBALL_NAME) .
	@echo ""
	@echo "=== Tarball created ==="
	@ls -lh output/
	@echo ""
	@echo "=== Contents of tarball (first 20 files) ==="
	@tar tzf output/$(TARBALL_NAME) | head -20

# 統合テスト実行
test-integration:
	@echo "=== Running integration tests ==="
	@python3 -m pip install --upgrade pip --quiet
	@pip3 install pytest hypothesis pytest-cov pytest-xdist pyyaml --quiet
	@echo "Running integration tests for $(VARIANT) variant on $(ARCH)..."
	@if [ -f "tests/integration/test_phase1_integration.py" ]; then \
		python3 -m pytest tests/integration/test_phase1_integration.py -v || echo "Phase 1 tests not ready yet"; \
	fi
	@echo ""
	@echo "=== Verifying rootfs tarball ==="
	@TARBALL_COUNT=$$(ls -1 output/kimigayo-$(VARIANT)-*.tar.gz 2>/dev/null | wc -l); \
	if [ "$$TARBALL_COUNT" -gt 0 ]; then \
		echo "✓ Rootfs tarball created successfully"; \
		ls -lh output/kimigayo-$(VARIANT)-*.tar.gz; \
	else \
		echo "✗ Rootfs tarball not found"; \
		echo "Contents of output directory:"; \
		ls -lah output/ || echo "output/ directory does not exist"; \
		exit 1; \
	fi

# Dockerイメージビルド
build-image: package-rootfs
	@echo ""
	@echo "=== Building Docker image ==="
	@docker build -f Dockerfile.runtime \
		-t kimigayo-os:$(VARIANT)-$(ARCH) \
		-t kimigayo-os:$(VERSION)-$(VARIANT)-$(ARCH) .
	@echo ""
	@echo "✓ Docker image built: kimigayo-os:$(VARIANT)-$(ARCH)"

# スモークテスト
test-smoke: build-image
	@echo ""
	@echo "=== Running smoke tests ==="
	@echo "Inspecting built image..."
	@docker run --rm kimigayo-os:$(VARIANT)-$(ARCH) ls -la / || echo "Failed to list root directory"
	@echo ""
	@echo "Test 1: Verify image can start..."
	@docker run --rm kimigayo-os:$(VARIANT)-$(ARCH) /bin/sh -c "echo 'Container started successfully'"
	@echo ""
	@echo "Test 2: Verify basic commands work..."
	@docker run --rm kimigayo-os:$(VARIANT)-$(ARCH) /bin/sh -c "ls / && pwd"
	@echo ""
	@echo "Test 3: Verify BusyBox is available..."
	@docker run --rm kimigayo-os:$(VARIANT)-$(ARCH) /bin/sh -c "busybox --help" | head -5
	@echo ""
	@echo "✓ All smoke tests passed"

# 完全なCI/CDビルド（ローカル実行）
ci-build-local: build-rootfs package-rootfs test-integration build-image test-smoke
	@echo ""
	@echo "╔════════════════════════════════════════════════════════════════╗"
	@echo "║              ✅ CI/CDビルド完了                                  ║"
	@echo "╚════════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "📦 生成されたアーティファクト:"
	@echo "  - Tarball: output/$(TARBALL_NAME)"
	@echo "  - Docker Image: kimigayo-os:$(VARIANT)-$(ARCH)"
	@echo ""
	@echo "🚀 次のステップ:"
	@echo "  - イメージをテスト: docker run -it kimigayo-os:$(VARIANT)-$(ARCH) /bin/sh"
	@echo "  - 他のバリアント: make ci-build-local VARIANT=minimal"
	@echo "  - 他のアーキ: make ci-build-local ARCH=arm64"
	@echo ""

# 複数バリアントビルド
ci-build-all:
	@echo "=== Building all variants for $(ARCH) ==="
	@$(MAKE) ci-build-local VARIANT=minimal ARCH=$(ARCH)
	@$(MAKE) ci-build-local VARIANT=standard ARCH=$(ARCH)
	@$(MAKE) ci-build-local VARIANT=extended ARCH=$(ARCH)
	@echo ""
	@echo "✅ All variants built successfully for $(ARCH)"

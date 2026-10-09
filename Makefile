# Kimigayo OS - Docker Management Makefile
# プロジェクト管理用の簡易コマンド集

# 構成要素のバージョンの単一の真実の源（CLAUDE.md 参照）
include versions.mk

# include より後に最初のターゲットが来るので明示しておく。
# 省略すると、include したファイルがターゲットを持った瞬間に既定ゴールを奪われる。
.DEFAULT_GOAL := help

# docker compose / Dockerfile に build arg として渡すため export する
KIMIGAYO_VERSION ?= $(shell bash scripts/get-version.sh 2>/dev/null || echo dev)
export ALPINE_VERSION KIMIGAYO_VERSION

.PHONY: help up down build rebuild clean logs shell test test-docker build-os clean-cache clean-all info
.PHONY: build-rootfs package-rootfs build-image verify-image check-links test-integration test-smoke ci-build-local ci-build-all
.PHONY: docker-hub-login push-image ci-build-push security-scan trivy-scan version show-version changelog
.PHONY: benchmark benchmark-startup benchmark-memory benchmark-size benchmark-comparison benchmark-lifecycle benchmark-all
.PHONY: print-kernel print-musl print-busybox print-openrc print-alpine print-versions

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
	@echo "  make build        - Kimigayo OSをビルド [1/4]～[4/4]"
	@echo "  make test         - テストを実行"
	@echo "  make test-docker  - Dockerイメージ起動テストを実行"
	@echo "  make test-func    - 機能テストを実行 (BusyBox, Network)"
	@echo "  make status       - ビルド状態を表示（どこまで完了したか確認）"
	@echo "  make info         - ビルド設定情報を表示"
	@echo ""
	@echo "🚀 CI/CDローカル実行（GitHub Actions相当）:"
	@echo "  make ci-build-local      - 完全なCI/CDビルド（rootfs→テスト→イメージ）"
	@echo "  make ci-build-push       - ビルド＋Docker Hubへプッシュ"
	@echo "  make build-rootfs        - rootfsのみビルド"
	@echo "  make package-rootfs      - rootfsをtarballにパッケージ化"
	@echo "  make test-integration    - 統合テストを実行"
	@echo "  make build-image         - Dockerイメージをビルド"
	@echo "  make test-smoke          - スモークテストを実行"
	@echo "  make ci-build-all        - 全バリアントをビルド"
	@echo ""
	@echo "🐳 Docker Hub連携:"
	@echo "  make docker-hub-login    - Docker Hubにログイン"
	@echo "  make push-image          - イメージをDocker Hubにプッシュ"
	@echo ""
	@echo "🔒 セキュリティスキャン:"
	@echo "  make trivy-scan          - Trivyで脆弱性スキャン"
	@echo "  make security-scan       - 総合セキュリティスキャン（Trivy）"
	@echo ""
	@echo "  設定方法（優先順位: コマンドライン > .env > デフォルト）:"
	@echo "    1. .envファイルを作成: cp .env.example .env"
	@echo "    2. .envを編集してデフォルト値を設定（DOCKER_HUB_ACCESS_TOKEN含む）"
	@echo "    3. コマンドライン引数で一時的に上書き可能"
	@echo ""
	@echo "  パラメータ例:"
	@echo "    make ci-build-local                              # .envの設定を使用"
	@echo "    VARIANT=minimal make ci-build-local              # .envを上書き"
	@echo "    make ci-build-push                               # ビルド＆プッシュ"
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
	@echo "📌 バージョン管理:"
	@echo "  make version      - バージョン番号を取得"
	@echo "  make show-version - バージョン情報を表示"
	@echo "  make changelog    - CHANGELOG.mdを生成"
	@echo ""
	@echo "⚡ ベンチマーク:"
	@echo "  make benchmark            - 全ベンチマーク実行"
	@echo "  make benchmark-startup    - 起動時間測定"
	@echo "  make benchmark-memory     - メモリ使用量測定"
	@echo "  make benchmark-size       - ディスクサイズ比較"
	@echo "  make benchmark-lifecycle  - コンテナライフサイクル測定"
	@echo "  make benchmark-busybox    - BusyBoxコマンド性能測定"
	@echo "  make benchmark-comparison - Alpine/Distroless/Ubuntuとの比較"
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
	@echo "  make musl                   # musl libcのみ [1/4]"
	@echo "  make kernel                 # Linuxカーネルのみ [2/4]"
	@echo "  make busybox                # BusyBoxのみ [3/4]"
	@echo "  make init                   # OpenRCのみ [4/4]"
	@echo ""
	@echo "⚙️  コンテナ内で使える個別クリーン:"
	@echo "  make clean-musl             # muslのみ削除"
	@echo "  make clean-kernel           # カーネルのみ削除"
	@echo "  make clean-busybox          # BusyBoxのみ削除"
	@echo "  make clean-openrc           # OpenRCのみ削除"
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
DOCKER_HUB_ACCESS_TOKEN ?=

TARBALL_NAME = kimigayo-$(VARIANT)-$(VERSION)-$(ARCH).tar.gz
DOCKER_IMAGE_TAG = $(DOCKER_HUB_USERNAME)/$(IMAGE_NAME):$(VARIANT)-$(ARCH)

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
	@# macOSのリソースフォーク（._*）とその他の不要ファイルを除外
	@#
	@# COPYFILE_DISABLE=1 が必須。macOS の bsdtar は AppleDouble メンバー
	@# （._*）を「除外処理のあとに」自分で生成するため、--exclude='._*' では
	@# 止まらない。さらに bsdtar は自分が作った ._* を一覧表示時に隠すので、
	@# tar tzf で確認しても気づけない（Linux 側で展開すると出てくる）。
	@# 実測: COPYFILE_DISABLE なしで 458 個の ._* がイメージに入っていた。
	@cd build/rootfs && COPYFILE_DISABLE=1 tar czf ../../output/$(TARBALL_NAME) \
		--exclude='._*' \
		--exclude='.DS_Store' \
		--exclude='.AppleDouble' \
		--exclude='.LSOverride' \
		.
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
	@python3 -m pip install -r requirements-dev.txt --quiet
	@echo "Running integration tests for $(VARIANT) variant on $(ARCH)..."
	@if [ -f "tests/integration/test_phase1_integration.py" ]; then \
		python3 -m pytest tests/integration/test_phase1_integration.py -v; \
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
# ARCH -> Docker の platform 表記
DOCKER_PLATFORM = $(if $(filter arm64,$(ARCH)),linux/arm64,linux/amd64)

build-image: package-rootfs
	@echo ""
	@echo "=== Building Docker image ==="
	@# --platform と TARBALL_PATH は必須。
	@# 省略すると (1) arm64 の rootfs を amd64 のイメージとして包んでしまい、
	@# (2) Dockerfile.runtime の既定 TARBALL_PATH=output/*.tar.gz が
	@# 別のバリアント／アーキの tarball を拾う。
	@docker build -f Dockerfile.runtime \
		--platform $(DOCKER_PLATFORM) \
		--build-arg TARBALL_PATH=output/$(TARBALL_NAME) \
		-t kimigayo-os:$(VARIANT)-$(ARCH) \
		-t kimigayo-os:$(VERSION)-$(VARIANT)-$(ARCH) \
		-t $(DOCKER_IMAGE_TAG) \
		-t $(DOCKER_HUB_USERNAME)/$(IMAGE_NAME):$(VERSION)-$(VARIANT)-$(ARCH) .
	@echo ""
	@echo "✓ Docker image built: kimigayo-os:$(VARIANT)-$(ARCH)"
	@echo "✓ Tagged for Docker Hub: $(DOCKER_IMAGE_TAG)"

# 既にあるイメージを検証する（ビルドしない）
verify-image:
	@bash scripts/verify-image.sh kimigayo-os:$(VARIANT)-$(ARCH) $(VARIANT) $(ARCH)

# スモークテスト = イメージを作って検証する
#
# 以前はここに「/bin/sh が動く」「ls が動く」「busybox --help が動く」の
# 3つだけを並べていた。BusyBox は static-pie なのでこの3つは
# OpenRC・libc.so・/tmp が1つも入っていなくても通る。実際に
# v0.1.0〜v2.0.1 の公開済み4タグすべてがその状態で通過していた。
# 検証の実体は scripts/verify-image.sh に移し、CI・release・ローカルの
# 3経路から同じものを呼ぶ（YAML に埋めると経路ごとにずれる）。
test-smoke: build-image verify-image

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

# Docker Hubログイン
docker-hub-login:
	@echo "=== Logging in to Docker Hub ==="
	@if [ -z "$(DOCKER_HUB_ACCESS_TOKEN)" ]; then \
		echo "❌ Error: DOCKER_HUB_ACCESS_TOKEN is not set"; \
		echo ""; \
		echo "Please set it in one of the following ways:"; \
		echo "  1. Add to .env file: DOCKER_HUB_ACCESS_TOKEN=dckr_pat_xxxxx"; \
		echo "  2. Set environment variable: export DOCKER_HUB_ACCESS_TOKEN=dckr_pat_xxxxx"; \
		echo "  3. Pass as argument: DOCKER_HUB_ACCESS_TOKEN=dckr_pat_xxxxx make docker-hub-login"; \
		echo ""; \
		echo "Get your token from: https://hub.docker.com/settings/security"; \
		exit 1; \
	fi
	@echo "$(DOCKER_HUB_ACCESS_TOKEN)" | docker login -u $(DOCKER_HUB_USERNAME) --password-stdin
	@echo "✓ Successfully logged in to Docker Hub as $(DOCKER_HUB_USERNAME)"

# Docker Hubへプッシュ
push-image: docker-hub-login
	@echo ""
	@echo "=== Pushing image to Docker Hub ==="
	@docker push $(DOCKER_IMAGE_TAG)
	@docker push $(DOCKER_HUB_USERNAME)/$(IMAGE_NAME):$(VERSION)-$(VARIANT)-$(ARCH)
	@echo ""
	@echo "✓ Successfully pushed to Docker Hub"
	@echo "  - $(DOCKER_IMAGE_TAG)"
	@echo "  - $(DOCKER_HUB_USERNAME)/$(IMAGE_NAME):$(VERSION)-$(VARIANT)-$(ARCH)"

# 完全なCI/CDビルド（プッシュ含む）
ci-build-push: ci-build-local push-image
	@echo ""
	@echo "╔════════════════════════════════════════════════════════════════╗"
	@echo "║         ✅ CI/CDビルド＆プッシュ完了                            ║"
	@echo "╚════════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "🚀 イメージがDocker Hubにプッシュされました:"
	@echo "   docker pull $(DOCKER_IMAGE_TAG)"
	@echo ""

# ============================================================================
# セキュリティスキャン
# ============================================================================

# Trivyで脆弱性スキャン（イメージ）
trivy-scan:
	@echo "=== Running Trivy vulnerability scan ==="
	@echo "Image: kimigayo-os:$(VARIANT)-$(ARCH)"
	@echo ""
	@if ! command -v trivy &> /dev/null; then \
		echo "❌ Error: Trivy is not installed"; \
		echo ""; \
		echo "Install Trivy:"; \
		echo "  macOS: brew install trivy"; \
		echo "  Linux: https://aquasecurity.github.io/trivy/latest/getting-started/installation/"; \
		exit 1; \
	fi
	@echo "Scanning for CRITICAL and HIGH vulnerabilities..."
	@trivy image --severity CRITICAL,HIGH --scanners vuln,config,secret kimigayo-os:$(VARIANT)-$(ARCH) || true
	@echo ""
	@echo "Full vulnerability report:"
	@trivy image --scanners vuln,config,secret kimigayo-os:$(VARIANT)-$(ARCH)

# Trivyでファイルシステムスキャン
trivy-fs-scan:
	@echo "=== Running Trivy filesystem scan ==="
	@echo "Scanning project directory..."
	@echo ""
	@if ! command -v trivy &> /dev/null; then \
		echo "❌ Error: Trivy is not installed"; \
		echo ""; \
		echo "Install Trivy:"; \
		echo "  macOS: brew install trivy"; \
		echo "  Linux: https://aquasecurity.github.io/trivy/latest/getting-started/installation/"; \
		exit 1; \
	fi
	@trivy fs --severity CRITICAL,HIGH,MEDIUM --scanners vuln,config,secret,license .

# ShellCheckで静的解析
# CI の shellcheck ジョブ（ludeeus/action-shellcheck, severity: warning）と
# 同じ条件でローカルに回す。
# shellcheck が入っていなければ Docker イメージで代替する
# （ビルド環境イメージにも Alpine の shellcheck は入っていない）。
# 以前は -exec shellcheck {} \; だったため、警告が出ても make が成功していた。
# 検査対象。.claude/hooks/ も含める（Claude Code のフックは
# このリポジトリの作業ルールの一部であり、壊れると静かに効かなくなる）。
SHELLCHECK_TARGETS := scripts/*.sh scripts/lib/*.sh .claude/hooks/*.sh

# ドキュメントのリンク切れ検査
#
# **追跡ファイル基準で判定する。** ローカルのファイルシステムで見ると、
# .gitignore されているファイル（TODO.md など）が手元にあるせいで
# 「リンクは生きている」と誤判定し、clone した人だけ壊れている状態を
# 見逃す。実際に README が追跡されていない TODO.md を指していた。
check-links:
	@echo "=== Checking markdown links (tracked files only) ==="
	@python3 scripts/check-links.py

shellcheck-scan:
	@echo "=== Running ShellCheck on scripts (severity: warning) ==="
	@echo ""
	@if command -v shellcheck > /dev/null 2>&1; then \
		shellcheck --severity=warning $(SHELLCHECK_TARGETS); \
	elif command -v docker > /dev/null 2>&1; then \
		echo "shellcheck が無いので Docker イメージで実行します"; \
		docker run --rm -v "$(CURDIR):/mnt" -w /mnt koalaman/shellcheck:stable \
			--severity=warning $(SHELLCHECK_TARGETS); \
	else \
		echo "❌ Error: ShellCheck も Docker も見つかりません"; \
		echo ""; \
		echo "Install ShellCheck:"; \
		echo "  macOS: brew install shellcheck"; \
		echo "  Linux: apt install shellcheck"; \
		exit 1; \
	fi
	@echo "✅ ShellCheck: 警告なし"

# 総合セキュリティスキャン
security-scan: trivy-scan trivy-fs-scan shellcheck-scan
	@echo ""
	@echo "╔════════════════════════════════════════════════════════════════╗"
	@echo "║              ✅ セキュリティスキャン完了                         ║"
	@echo "╚════════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "📊 スキャン結果は上記を確認してください"
	@echo ""

# ════════════════════════════════════════════════════════════════════════
# バージョン管理
# ════════════════════════════════════════════════════════════════════════

# バージョン番号を取得
version:
	@bash scripts/get-version.sh

# バージョン情報を表示
show-version:
	@bash scripts/show-version.sh

# CHANGELOG.mdを生成
# versions.mk の値を単発で取り出す（スクリプト・ドキュメントから使う）
print-kernel:
	@echo $(KERNEL_VERSION)
print-musl:
	@echo $(MUSL_VERSION)
print-busybox:
	@echo $(BUSYBOX_VERSION)
print-openrc:
	@echo $(OPENRC_VERSION)
print-alpine:
	@echo $(ALPINE_VERSION)
print-versions:
	@echo "kernel=$(KERNEL_VERSION) musl=$(MUSL_VERSION) busybox=$(BUSYBOX_VERSION) openrc=$(OPENRC_VERSION) alpine=$(ALPINE_VERSION)"

changelog:
	@bash scripts/generate-changelog.sh

# ════════════════════════════════════════════════════════════════════════
# ベンチマーク
# ════════════════════════════════════════════════════════════════════════

# 起動時間ベンチマーク
benchmark-startup:
	@bash scripts/benchmark-startup.sh

# メモリ使用量ベンチマーク
benchmark-memory:
	@bash scripts/benchmark-memory.sh

# ディスクサイズベンチマーク
benchmark-size:
	@bash scripts/benchmark-size.sh

# 比較ベンチマーク（Alpine, Distroless, Ubuntuとの比較）
# Note: Requires bash 4.0+ (macOS: brew install bash)
benchmark-comparison:
	@if command -v /opt/homebrew/bin/bash >/dev/null 2>&1; then \
		/opt/homebrew/bin/bash scripts/benchmark-comparison.sh; \
	elif command -v /usr/local/bin/bash >/dev/null 2>&1; then \
		/usr/local/bin/bash scripts/benchmark-comparison.sh; \
	else \
		bash scripts/benchmark-comparison.sh; \
	fi

# コンテナライフサイクルベンチマーク（Phase 2 - Issue #29）
# コンテナ起動、停止、再起動のライフサイクル全体の性能を測定
benchmark-lifecycle:
	@IMAGE_NAME=$(IMAGE_NAME):$(VARIANT)-$(ARCH) bash scripts/benchmark-lifecycle.sh

# BusyBoxコマンド性能ベンチマーク（Phase 3 - Issue #30）
# ls, grep, find, awk, sort, cat, wc, headの実行速度測定
benchmark-busybox:
	@IMAGE_NAME=$(IMAGE_NAME):$(VARIANT)-$(ARCH) bash scripts/benchmark-busybox.sh

# 全ベンチマーク実行
benchmark-all:
	@bash scripts/benchmark-all.sh

# デフォルトベンチマーク（全て実行）
benchmark: benchmark-all

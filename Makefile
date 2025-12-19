# Kimigayo OS - Docker Management Makefile
# プロジェクト管理用の簡易コマンド集

.PHONY: help up down build rebuild clean logs shell test build-os clean-cache clean-all info

# デフォルトターゲット
help:
	@echo "╔════════════════════════════════════════════════════════════════╗"
	@echo "║         Kimigayo OS - コンテナ向けOSビルドシステム             ║"
	@echo "║    軽量・高速・セキュアなDockerイメージOS                       ║"
	@echo "╚════════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "📦 クイックスタート:"
	@echo "  1. make docker-build  # ビルド環境を構築"
	@echo "  2. make build         # OSをビルド"
	@echo "  3. make test          # テストを実行"
	@echo ""
	@echo "🔧 OSビルドコマンド:"
	@echo "  make build        - Kimigayo OSをビルド"
	@echo "  make test         - テストを実行"
	@echo "  make info         - ビルド設定情報を表示"
	@echo "  make clean        - ビルド成果物を削除"
	@echo ""
	@echo "🐳 Docker管理:"
	@echo "  make docker-build - ビルド環境イメージを構築"
	@echo "  make docker-rebuild - キャッシュなしで再構築"
	@echo "  make shell        - コンテナにログイン"
	@echo "  make up           - コンテナをバックグラウンド起動"
	@echo "  make down         - コンテナを停止・削除"
	@echo "  make logs         - コンテナログを表示"
	@echo ""
	@echo "🗑️  クリーンアップ:"
	@echo "  make clean        - ビルド成果物のみ削除"
	@echo "  make clean-cache  - ダウンロードキャッシュを削除"
	@echo "  make clean-all    - すべて削除（推奨：完全リセット）"
	@echo ""
	@echo "📋 ログ確認:"
	@echo "  make log-kernel   - カーネルビルドログ（最新100行）"
	@echo "  make log-musl     - musl libcビルドログ（最新100行）"
	@echo "  make log-openrc   - OpenRCビルドログ（最新100行）"
	@echo ""
	@echo "⚙️  詳細オプション:"
	@echo "  docker compose run --rm kimigayo-build make build ARCH=x86_64"
	@echo "  docker compose run --rm kimigayo-build make build V=1"
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

info:
	@echo "ビルド情報を表示..."
	docker compose run --rm kimigayo-build make info

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

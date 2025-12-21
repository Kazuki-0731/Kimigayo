# Kimigayo OS - Docker Management Makefile
# プロジェクト管理用の簡易コマンド集

.PHONY: help up down build rebuild clean logs shell test test-docker build-os clean-cache clean-all info

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

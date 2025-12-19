# Kimigayo OS - Docker Management Makefile
# プロジェクト管理用の簡易コマンド集

.PHONY: help up down build clean logs shell test build-os clean-cache clean-all

# デフォルトターゲット
help:
	@echo "Kimigayo OS - Docker Management Commands"
	@echo ""
	@echo "Docker管理コマンド:"
	@echo "  make up           - コンテナを起動"
	@echo "  make down         - コンテナを停止・削除"
	@echo "  make build        - Dockerイメージをビルド"
	@echo "  make rebuild      - Dockerイメージを再ビルド（キャッシュなし）"
	@echo "  make shell        - コンテナにログイン（bash）"
	@echo "  make logs         - コンテナのログを表示"
	@echo ""
	@echo "OSビルドコマンド:"
	@echo "  make build-os     - Kimigayo OSをビルド"
	@echo "  make test         - テストを実行"
	@echo ""
	@echo "クリーンアップコマンド:"
	@echo "  make clean        - ビルド成果物を削除"
	@echo "  make clean-cache  - ダウンロードキャッシュを削除"
	@echo "  make clean-all    - すべて削除（コンテナ+volume）"
	@echo ""
	@echo "ログ確認コマンド:"
	@echo "  make log-kernel   - カーネルビルドログを表示"
	@echo "  make log-musl     - musl libcビルドログを表示"
	@echo "  make log-openrc   - OpenRCビルドログを表示"

# Dockerコンテナ管理
up:
	@echo "コンテナを起動..."
	docker compose up -d

down:
	@echo "コンテナを停止・削除..."
	docker compose down

build:
	@echo "Dockerイメージをビルド..."
	docker compose build

rebuild:
	@echo "Dockerイメージを再ビルド（キャッシュなし）..."
	docker compose build --no-cache

shell:
	@echo "コンテナにログイン..."
	docker compose run --rm kimigayo-build bash

logs:
	@echo "コンテナログを表示..."
	docker compose logs -f

# OSビルド
build-os:
	@echo "Kimigayo OSをビルド..."
	docker compose run --rm kimigayo-build make build

test:
	@echo "テストを実行..."
	docker compose run --rm kimigayo-build make test

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

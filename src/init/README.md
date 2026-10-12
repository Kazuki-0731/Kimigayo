# Init System

Kimigayo OSのInitシステム (OpenRCベース) まわりの Python モジュール

**このディレクトリはイメージに入りません。** イメージの Init は上流の
OpenRC で、`scripts/build-openrc.sh` がビルドし `scripts/build-rootfs.sh`
が rootfs に入れます。ここにあるのはテスト（`tests/unit/`・`tests/property/`）
から使う Python のモデルです。

## 構造

- `openrc.py` - OpenRC の設定・ランレベルのモデル
- `service.py` - サービス管理
- `security.py` - サービスのセキュリティ設定
- `logging.py` - ログ管理
- `shutdown.py` - シャットダウン処理

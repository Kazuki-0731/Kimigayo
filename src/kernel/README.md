# Kernel Configuration

このディレクトリには、Kimigayo OSのLinuxカーネルのビルド補助が含まれます。

**カーネルは Docker イメージに入りません**（コンテナはホストのカーネルで動く）。
カーネルを作るのはベアメタル／QEMU で試すときだけで、CI では作りません。

## 構造

- `config/` - カーネル設定の置き場。**追跡中の config は無く**（README だけ）、
  `<arch>.config` を置けばビルドで使われる（→ [config/README.md](config/README.md)）
- `patches/` - カーネルパッチ（現在0件）

実際のビルドは `scripts/build-kernel.sh`（ビルドコンテナ内の `make kernel`）です。

## セキュリティ強化設定

`scripts/build-kernel.sh` の `apply_security_hardening()` が、defconfig に
次を上書きします（詳細は [config/README.md](config/README.md)）。

- KASLR（`RANDOMIZE_BASE`・`RANDOMIZE_MEMORY`）
- Stack protector（`STACKPROTECTOR_STRONG`）
- `HARDENED_USERCOPY`・`FORTIFY_SOURCE`・`SECURITY_DMESG_RESTRICT`

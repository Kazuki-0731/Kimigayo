# Kernel Configuration

このディレクトリには、Kimigayo OSのLinuxカーネルのビルド補助が含まれます。

**カーネルは Docker イメージに入りません**（コンテナはホストのカーネルで動く）。
カーネルを作るのはベアメタル／QEMU で試すときだけで、CI では作りません。

## 構造

- `config/` - カーネル設定ファイル。**ビルドで実際に読まれるのは
  `<arch>.config` だけで、追跡中の `x86_64.config` はプレースホルダ**
  （→ [config/README.md](config/README.md)）
- `patches/` - カーネルパッチ（現在0件）
- `build.py` - Python のビルド補助（`tests/unit/test_kernel_build.py` から使われる。
  実際のビルドは `scripts/build-kernel.sh`）

## セキュリティ強化設定

`scripts/build-kernel.sh` の `apply_security_hardening()` が、defconfig に
次を上書きします（詳細は [config/README.md](config/README.md)）。

- KASLR（`RANDOMIZE_BASE`・`RANDOMIZE_MEMORY`）
- Stack protector（`STACKPROTECTOR_STRONG`）
- `HARDENED_USERCOPY`・`FORTIFY_SOURCE`・`SECURITY_DMESG_RESTRICT`

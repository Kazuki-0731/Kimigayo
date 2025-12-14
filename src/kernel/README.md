# Kernel Configuration

このディレクトリには、Kimigayo OSのLinuxカーネル設定が含まれます。

## 構造

- `config/` - カーネル設定ファイル (.config)
- `patches/` - カーネルパッチ

## セキュリティ強化設定

すべてのカーネルビルドには以下が適用されます:

- ASLR (Address Space Layout Randomization)
- DEP (Data Execution Prevention)
- Stack protection
- Kernel hardening options

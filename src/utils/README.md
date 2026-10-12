# Core Utilities

Kimigayo OSのコアユーティリティ

**このディレクトリには README しかありません。** コアユーティリティは
BusyBox で、設定は `src/busybox/config/`（minimal / standard / extended）、
パッチは `src/busybox/patches/` にあります。

## BusyBoxコンポーネント（バリアントにより異なる）

- シェル (ash)
- ファイル操作 (cp, mv, rm, tar, gzip, etc.)
- ネットワーク (nc など。wget は standard / extended のみ)
- システム (ps, top, kill, etc.)

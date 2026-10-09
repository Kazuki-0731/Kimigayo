---
description: ビルドしたイメージ／rootfs を過去に壊れた形で壊れていないか検査する（引数: イメージタグ、省略時は手元の kimigayo-os 全部）
argument-hint: "[image-tag]  例: kimigayo-os:standard-arm64"
---

成果物を検査する。対象: $1

引数が無ければ `docker images kimigayo-os` にあるもの**全部**と
`build/rootfs` を対象にする。

**`rootfs-verifier` subagent に投げてください。** 検査項目はその定義に
入っています。渡すときは次を明示すること:

- 対象のイメージタグ（または rootfs ディレクトリ）
- 期待するアーキテクチャとバリアント
- すでに分かっている問題（二度調べさせない）

## この検査で「合格」にしてはいけないもの

**「イメージが起動した」は検証ではありません。** v0.1.0〜v2.0.1 の
公開済み4タグはすべて smoke テストに通りながら、OpenRC・`libc.so`・
`/tmp` が入っていませんでした。

とくに次は**実際に実行しないと分かりません**。ファイルの存在では駄目です。

```
docker run --rm --platform linux/<arch> <image> /bin/sh -c \
  'for b in openrc openrc-run rc-update start-stop-daemon; do
     printf "%-20s %s\n" "$b" "$(/sbin/$b --version 2>&1 | head -1)"
   done'
```

`Error relocating ...: <symbol>: symbol not found` は**不合格**。
arm64 で `__letf2` が未解決になり動的リンクのバイナリが全滅していた
前例があります。x86_64 は long double が 80-bit でハードウェア命令を
使うため同じ問題が出ません。**必ず両アーキテクチャを見ること。**

## 報告

subagent の結果を受けて、**不合格があれば冒頭に「不合格」と書く**。
直し方は聞かれるまで実行しないこと（CLAUDE.md「指示の範囲を超えない」節）。

不合格だった場合は、それが**既にリリースされている版にも存在するか**を
`git log` と `git show <tag>:<file>` で確認して添えてください。
影響範囲が「今の作業ツリーだけ」か「公開済み全部」かで対応が変わります。

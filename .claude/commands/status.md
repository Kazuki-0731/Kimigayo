---
description: 現在地を一覧する（宣言バージョン / 実ビルド版 / イメージ / 直近コミット / 未追跡ファイル / 判断待ち）
allowed-tools: Bash(make print-versions), Bash(git:*), Bash(find:*), Bash(ls:*), Bash(docker images:*), Bash(grep:*), Bash(printf:*), Bash(for:*), Bash(do:*), Bash(done)
---

セッションの現在地を把握する。

## 宣言されているバージョン

!`make print-versions 2>/dev/null || grep -E '^[A-Z_]+_VERSION' versions.mk`

## 実際にビルドされている版

!`for c in musl busybox openrc; do printf '%-10s %s\n' "$c" "$(find build -maxdepth 2 -name '.kimigayo-build-version' -path "*${c}-install-*" -exec cat {} \; 2>/dev/null | tr '\n' ' ')"; done; ls build/kernel/output/vmlinuz-* 2>/dev/null || echo 'kernel     未ビルド'`

## 手元の Docker イメージ

!`docker images kimigayo-os --format '{{.Tag}}\t{{.Size}}\t{{.CreatedSince}}' 2>/dev/null || echo '(docker なし)'`

## 直近のコミットと未 push

!`git log --oneline -8; echo '--- 未 push ---'; git log --oneline @{u}..HEAD 2>/dev/null || echo '(upstream 未設定)'`

## 作業ツリー

!`git status --short; echo '--- 未追跡 ---'; git ls-files --others --exclude-standard | head -20`

## パッチが黙ってスキップされていないか

!`grep -iE 'skipped: [1-9]|not applicable' build/kernel-patches.log build/busybox-patches.log 2>/dev/null || echo '問題なし（またはログ未生成）'`

---

上の出力をもとに、次の3点を**箇条書き数行で**報告してください。
経緯の再説明はしないこと。

1. **次にやるべきこと** — 今すぐ着手できる直近の一手
2. **残っていること** — `TODO.md` の【要判断】【判断待ち】と
   `NEXT.md` の未消化項目（この2ファイルを読んで拾う）
3. **気づいた問題** — 上の出力に食い違いがあれば指摘する。
   **直さないこと**（報告のみ）

とくに次の食い違いは見逃さないこと:

- 宣言バージョンと実ビルド版の不一致（古いバイナリが使われる事故）
- BusyBox のスタンプにバリアントが入っていない、または測りたい
  バリアントと違う（`1.38.0+standard` の形式）
- 未追跡ファイルの放置（`.hypothesis/` の59ファイルが9か月放置された前例）
- `not applicable` なパッチ

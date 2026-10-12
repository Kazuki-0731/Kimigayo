# BusyBox VI エディタ musl libc 互換性パッチ

## 概要

BusyBoxのviエディタ（1.36.1 で発覚。1.38.0 でも上流は GNU 拡張のまま）は、GNU正規表現拡張機能を使用しているため、musl libcでコンパイルエラーが発生します。このドキュメントでは、musl libc対応パッチの詳細と適用方法を説明します。

## 問題の詳細

### エラー内容

```
editors/vi.c:2394:9: error: 're_syntax_options' undeclared (first use in this function)
 2394 |         re_syntax_options = RE_SYNTAX_POSIX_BASIC & (~RE_DOT_NEWLINE);
      |         ^~~~~~~~~~~~~~~~~
editors/vi.c:2394:29: error: 'RE_SYNTAX_POSIX_BASIC' undeclared (first use in this function)
 2394 |         re_syntax_options = RE_SYNTAX_POSIX_BASIC & (~RE_DOT_NEWLINE);
      |                             ^~~~~~~~~~~~~~~~~~~~~
editors/vi.c:2394:55: error: 'RE_DOT_NEWLINE' undeclared (first use in this function)
 2394 |         re_syntax_options = RE_SYNTAX_POSIX_BASIC & (~RE_DOT_NEWLINE);
      |                                                       ^~~~~~~~~~~~~~
```

### 原因

BusyBox viエディタ（`editors/vi.c`）が使用するGNU正規表現拡張：

| GNU拡張 | 説明 | musl libcでの状態 |
|---------|------|------------------|
| `re_syntax_options` | 正規表現構文オプション | ❌ 存在しない |
| `RE_SYNTAX_POSIX_BASIC` | POSIX基本正規表現モード | ❌ 存在しない |
| `RE_DOT_NEWLINE` | ドットが改行にマッチ | ❌ 存在しない |
| `RE_ICASE` | 大文字小文字を無視 | ❌ 存在しない |
| `re_compile_pattern()` | パターンコンパイル | ❌ 存在しない |
| `re_search()` | 正規表現検索 | ❌ 存在しない |
| `struct re_pattern_buffer` | パターンバッファ構造体 | ❌ 存在しない |

これらはglibcの`<regex.h>`に含まれるGNU拡張で、POSIX標準ではありません。

## パッチの内容

### ファイル構成

```
Kimigayo/
├── src/busybox/patches/
│   └── 0001-vi-musl-libc-compatibility.patch  # musl libc対応パッチ
└── scripts/
    └── apply-busybox-patches.sh               # パッチ適用スクリプト
```

### 変更内容

パッチは以下の変更を行います：

#### 1. GNU正規表現 → POSIX正規表現への置き換え

| GNU API | POSIX API | 説明 |
|---------|-----------|------|
| `re_compile_pattern()` | `regcomp()` | パターンコンパイル |
| `re_search()` | `regexec()` | パターン検索 |
| `struct re_pattern_buffer` | `regex_t` | 正規表現構造体 |
| `regfree()` | `regfree()` | メモリ解放（共通） |

#### 2. オプションフラグの変換

```c
// GNU正規表現
re_syntax_options = RE_SYNTAX_POSIX_BASIC & (~RE_DOT_NEWLINE);
if (ignorecase)
    re_syntax_options |= RE_ICASE;

// POSIX正規表現
int cflags = REG_NOSUB;  // マッチ位置不要
if (ignorecase)
    cflags |= REG_ICASE;  // 大文字小文字無視
```

#### 3. 後方検索の実装

GNU `re_search()` は方向指定が可能ですが、POSIX `regexec()` は前方検索のみです。
パッチでは、後方検索を「前方検索を繰り返して最後のマッチを見つける」方法で実装しています。

```c
// 後方検索の実装（擬似コード）
char *last_match = NULL;
char *search_pos = start;
while (search_pos < end && regexec(&preg, search_pos, 1, match, 0) == 0) {
    last_match = search_pos + match[0].rm_so;
    search_pos = search_pos + match[0].rm_so + 1;
}
```

#### 4. エラーハンドリング

```c
// GNU正規表現
const char *err = re_compile_pattern(pat, strlen(pat), &preg);
if (err != NULL) {
    status_line_bold("bad search pattern '%s': %s", pat, err);
    return p;
}

// POSIX正規表現
int rc = regcomp(&preg, pat, cflags);
if (rc != 0) {
    char errbuf[256];
    regerror(rc, &preg, errbuf, sizeof(errbuf));
    status_line_bold("bad search pattern '%s': %s", pat, errbuf);
    regfree(&preg);
    return p;
}
```

## パッチの適用方法

### 自動適用（推奨）

ビルドプロセスで自動的に適用されます：

```bash
# ビルド時に自動適用（ビルドコンテナ内の build-system/Makefile）
docker compose run --rm -T kimigayo-build make busybox TARGET_ARCH=x86_64 IMAGE_TYPE=standard
```

`scripts/build-busybox.sh` が `scripts/apply-busybox-patches.sh` を呼び、
コンパイル前に `src/busybox/patches/` のパッチを適用します
（当たらなければビルドが失敗します）。

### 手動適用

```bash
# BusyBoxソースディレクトリに移動（<version> は versions.mk の BUSYBOX_VERSION）
cd build/busybox-<version>

# 当たるかを先に確認してから適用
patch -p1 --dry-run < ../../src/busybox/patches/0001-vi-musl-libc-compatibility.patch
patch -p1 < ../../src/busybox/patches/0001-vi-musl-libc-compatibility.patch
```

### パッチの取り消し

```bash
cd build/busybox-<version>
patch -p1 -R < ../../src/busybox/patches/0001-vi-musl-libc-compatibility.patch
```

## テスト方法

### 1. ビルドテスト

```bash
# scripts/build-busybox.sh は直接叩かない（Makefile が渡す変数が要る）
docker compose run --rm -T kimigayo-build make busybox TARGET_ARCH=x86_64 IMAGE_TYPE=standard
docker compose run --rm -T kimigayo-build make busybox TARGET_ARCH=x86_64 IMAGE_TYPE=extended
```

### 2. 機能テスト

```bash
# コンテナ起動
docker run -it kimigayo-os:standard-x86_64 /bin/sh

# viエディタ起動
vi test.txt

# 検索機能テスト
# vi内で:
# /pattern  - 前方検索
# ?pattern  - 後方検索
# n         - 次を検索
# N         - 前を検索

# 大文字小文字無視検索
# :set ignorecase
# /Pattern  - PATTERNもpatternもマッチ
```

### 3. 正規表現テスト

正規表現検索（`CONFIG_FEATURE_VI_REGEX_SEARCH`）が有効なのは extended だけです
（standard の config には書かれておらず、minimal は vi 自体が無効）。

```bash
# vi内で正規表現検索
/^start.*end$
/[0-9]+
/test\|example
```

## パフォーマンス比較

### GNU vs POSIX正規表現

| 操作 | GNU `re_search` | POSIX `regexec` | 備考 |
|------|-----------------|-----------------|------|
| 前方検索 | O(n) | O(n) | 同等 |
| 後方検索 | O(n) | O(n²) | POSIXは繰り返し検索が必要 |
| メモリ使用量 | 小 | 小 | ほぼ同等 |

**注**: 後方検索は理論上O(n²)ですが、実際のファイル編集では検索範囲が限定的なため、体感速度への影響は軽微です。

## トラブルシューティング

### パッチ適用失敗

```bash
# エラー例
patching file editors/vi.c
Hunk #1 FAILED at 2390.
1 out of 1 hunk FAILED -- saving rejects to file editors/vi.c.rej
```

**原因**: BusyBoxのバージョンが異なる、または既にvi.cが変更されている

**対処法**:
```bash
# 1. BusyBoxバージョン確認
ls build/busybox-*

# 2. パッチを手動で作り直す（展開した tarball は git 管理ではないので diff を使う）
cd build
cp -a busybox-<version> busybox-orig   # 編集前の状態を残しておく
vi busybox-<version>/editors/vi.c
# 手動でGNU正規表現をPOSIX正規表現に置き換え

# 3. 新しいパッチファイル生成（patch -p1 で当たる形）
diff -u busybox-orig/editors/vi.c busybox-<version>/editors/vi.c \
  > ../src/busybox/patches/0001-vi-musl-libc-compatibility-new.patch
```

### viの検索が動作しない

```bash
# 検索に使う機能が config で有効か確かめる
grep -n 'CONFIG_FEATURE_VI_SEARCH\|CONFIG_FEATURE_VI_REGEX_SEARCH' src/busybox/config/*.config
```

### パフォーマンス低下

後方検索(`?pattern`)が遅い場合：

```bash
# 代替手段1: 前方検索を使用
# viで末尾に移動してから前方検索
G       # ファイル末尾へ
/pattern

# 代替手段2: sedを使用
sed -n '/pattern/p' file
```

## 既知の制限事項

### 1. REG_STARTEND非対応

```c
// BSD拡張（一部のmusl環境で未対応）
regexec(&preg, q, MAX_SUBPATTERN, regmatch, REG_STARTEND)
```

**対処**: オフセットで代替

### 2. 後方検索のパフォーマンス

大きなファイル（数MB以上）での後方検索は遅くなる可能性があります。

**対処**: 前方検索を推奨、またはsed/awkを使用

### 3. 一部の正規表現機能

GNU拡張の一部機能（例: `\w`, `\s`）はPOSIX BREでは使用不可。

**対処**: POSIX準拠の正規表現を使用
- `\w` → `[a-zA-Z0-9_]`
- `\s` → `[ \t\n]`

## 参考資料

### POSIX正規表現

- [POSIX.1-2017 regex.h](https://pubs.opengroup.org/onlinepubs/9699919799/basedefs/regex.h.html)
- [regcomp() specification](https://pubs.opengroup.org/onlinepubs/9699919799/functions/regcomp.html)

### musl libc

- [musl libc regex implementation](https://git.musl-libc.org/cgit/musl/tree/src/regex)
- [musl vs glibc compatibility](https://wiki.musl-libc.org/functional-differences-from-glibc.html)

### BusyBox

- [BusyBox vi.c source](https://git.busybox.net/busybox/tree/editors/vi.c)
- [BusyBox configuration options](https://git.busybox.net/busybox/tree/editors/Config.in)

## 更新履歴

- **2026-01-01**: 初版作成（Phase 3完了後対応）
  - musl libc対応パッチ作成
  - 自動適用スクリプト実装
  - ドキュメント整備

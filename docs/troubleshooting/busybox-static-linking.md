# BusyBox静的リンク問題のトラブルシューティング

## 問題の概要

BusyBoxが動的リンクでビルドされ、muslランタイムライブラリがイメージに含まれていないため、実行時にエラーが発生する問題。

## エラーの症状

```bash
$ docker run --rm ishinokazuki/kimigayo-os:latest-standard /bin/sh -c "echo test"
standard_init_linux.go:228: exec user process caused: no such file or directory
```

## 原因

1. **ARM64ビルドでの`-nostdlib`フラグ使用**
   - CRT（C Runtime）ファイル（crt0.o, crti.o, crtn.o）が除外される
   - 結果として動的リンクされたバイナリが生成される

2. **muslランタイムライブラリの不在**
   - 動的リンクされたバイナリは`/lib/ld-musl-aarch64.so.1`を必要とする
   - イメージにmuslライブラリが含まれていない

## 診断方法

### 1. バイナリのリンク状態を確認

```bash
# ローカルビルドの場合
file build/busybox-build-arm64/busybox

# イメージ内のバイナリを確認
docker create --name temp ishinokazuki/kimigayo-os:latest-standard
docker cp temp:/bin/busybox /tmp/busybox-check
file /tmp/busybox-check
docker rm temp
rm /tmp/busybox-check
```

**期待される出力:**
```
statically linked
```
または
```
static-pie linked
```

**問題のある出力:**
```
dynamically linked, interpreter /lib/ld-musl-aarch64.so.1
```

### 2. lddコマンドで依存関係を確認

```bash
ldd /tmp/busybox-check
```

**期待される出力:**
```
not a dynamic executable
```

**問題のある出力:**
```
/lib/ld-musl-aarch64.so.1 (0x...)
libc.so => /lib/ld-musl-aarch64.so.1 (0x...)
```

### 3. BusyBox .configを確認

```bash
grep "^CONFIG_STATIC" build/busybox-build-arm64/.config
```

**期待される出力:**
```
CONFIG_STATIC=y
CONFIG_STATIC_LIBGCC=y  # ARM64の場合はnでも可
```

## 解決方法

### Option 1: BusyBoxを完全静的リンクでビルド（推奨）

`scripts/build-busybox.sh`で以下の設定を使用:

```bash
# ARM64の場合
export CFLAGS="-Os -fstack-protector-strong -D_FORTIFY_SOURCE=2"
export LDFLAGS="-static -Wl,-z,relro -Wl,-z,now"
```

重要なポイント:
- ❌ `-nostdlib`を使用しない
- ✅ `-static`フラグのみを使用
- ✅ `CONFIG_STATIC=y`を設定
- ✅ muslツールチェーンに標準的なリンクを任せる

### Option 2: muslライブラリをイメージに含める（非推奨）

`scripts/build-rootfs.sh`の`copy_components()`関数で:

```bash
# Copy musl dynamic linker and libc
if [ -d "$MUSL_INSTALL_DIR" ]; then
    mkdir -p "$ROOTFS_DIR/lib"

    # Copy dynamic linker
    if [ "$ARCH" = "arm64" ]; then
        cp "$MUSL_INSTALL_DIR/lib/ld-musl-aarch64.so.1" "$ROOTFS_DIR/lib/"
    else
        cp "$MUSL_INSTALL_DIR/lib/ld-musl-x86_64.so.1" "$ROOTFS_DIR/lib/"
    fi

    # Copy libc
    cp "$MUSL_INSTALL_DIR/lib/libc.so" "$ROOTFS_DIR/lib/"
fi
```

デメリット:
- イメージサイズが増加（+500KB〜1MB）
- 静的リンクの利点（ポータビリティ、セキュリティ）を失う

## 検証手順

1. **クリーンビルド**
   ```bash
   rm -rf build/busybox-build-arm64
   bash scripts/build-busybox.sh
   ```

2. **バイナリ検証**
   ```bash
   file build/busybox-build-arm64/busybox | grep "statically linked"
   ```

3. **イメージビルドとテスト**
   ```bash
   ARCH=arm64 IMAGE_TYPE=standard bash scripts/build-rootfs.sh
   docker build -t test-kimigayo:arm64 -f Dockerfile .
   docker run --rm test-kimigayo:arm64 /bin/sh -c "echo 'Success!'"
   ```

## 関連Issue

- [#53 BusyBoxが動的リンクでビルドされmuslランタイムが不足](https://github.com/Kazuki-0731/Kimigayo/issues/53)

## 参考資料

- [BusyBox Configuration](https://busybox.net/FAQ.html#build_system)
- [musl libc - Functional differences from glibc](https://wiki.musl-libc.org/functional-differences-from-glibc.html)
- [Static linking with musl](https://wiki.alpinelinux.org/wiki/Creating_an_Alpine_package#Static_linking)

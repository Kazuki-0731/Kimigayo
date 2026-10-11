# `wget` の HTTPS が Segmentation fault で落ちる（v3.0.1）

**症状**: `wget https://...` が**本文のダウンロードには成功したあと**、
Segmentation fault（終了コード 139）で落ちる。HTTP は正常。

```console
/ # wget -O/dev/null https://example.com
Connecting to example.com (172.66.147.243:443)
wget: note: TLS certificate validation not implemented
saving to '/dev/null'
null                 100% |********************************|   577  0:00:00 ETA
'/dev/null' saved
Segmentation fault
/ # echo $?
139
```

**発見**: 2026-10-11（v3.0.1 公開後のドキュメント監査中）。
**状態**: **未修正・原因調査中。** クラッシュは Kimigayo の BusyBox バイナリに
ついてくる（musl でもリンク方法でもない）。容疑は config か clang。

---

## 分かっていること（すべて実測）

| 条件 | 結果 |
| --- | --- |
| `wget https://example.com`（arm64 ネイティブ）| **rc=139（SIGSEGV）** |
| `wget https://cloudflare.com` | rc=139（ホストに依らない）|
| `wget http://example.com` | **rc=0（HTTP は正常）** |
| `wget -O/tmp/out https://example.com` | rc=139 だが **577 バイトが正しく保存されている** |
| Standard / Extended | **両方で再現** |
| x86_64（Apple Silicon 上の QEMU）| `error getting response: Connection reset by peer`（rc=1）|
| `ssl_client` を単体でパイプして使う | **rc=0（落ちない）** |
| Alpine 3.24 の BusyBox で同じ取得 | **rc=0（落ちない）** |

**データは壊れていない。** 本文は正しく取得・保存されており、
落ちるのは取得後の後片付け。**可用性の問題であって、取得内容の
完全性や機密性の問題ではない。** ただし終了コードが 139 になるので、
**シェルスクリプトで `wget` の成功判定に使えない。**

**落ちるのは親プロセス。** バックグラウンドで走らせて `wait` すると
139 が返り、ジョブ制御の通知も同じジョブに対して出る。

## BusyBox の HTTPS の仕組み（1.38.0）

`networking/wget.c` の `spawn_ssl_client()`（L769）は、
**`BB_MMU` が有効な環境では `ssl_client` を exec しない。**
`fork` した子プロセスが**プロセス内で** TLS を処理する。

```c
pid = BB_MMU ? xfork() : xvfork();
if (pid == 0) {
    /* Child */
    ...
    if (BB_MMU) {
        tls_state_t *tls = new_tls_state();
        tls->ifd = tls->ofd = network_fd;
        tls_handshake(tls, servername);
        tls_run_copy_loop(tls, flags);
        exit(0);
    } else {
        /* ここは no-MMU 環境だけ。ssl_client を exec する */
    }
}
/* Parent */
```

**だから `ssl_client` 単体が動くことは、`wget` の HTTPS が動く根拠に
ならない。** 通る経路が違う。

## 原因の切り分け（途中。静的リンクではなかった）

> **2026-10-11 の初版で「原因は静的リンク」と書いたが、誤りだった。**
> BusyBox を動的リンクにしてビルドし直しても同じように落ちた。
> 以下は訂正後の切り分け結果。

### 1. 版とリンク方法を Alpine と比べた

すべて arm64 ネイティブ、`wget -O/dev/null https://example.com`:

| ビルド | ELF | 結果 |
| --- | --- | --- |
| Alpine edge の動的リンク 1.38.0 | 動的 | **rc=0（正常）** |
| Alpine edge の `busybox-static` 1.38.0 | static-pie | rc=1（TLS の note 直後に失敗）|
| Kimigayo v3.0.1 | static-pie | **rc=139（SIGSEGV）** |
| **Kimigayo を動的リンクにしたもの**（実験ブランチ）| **動的** | **rc=139（SIGSEGV）** |

**動的にしても落ちる。** 当初は上 3 行だけを見て「動的なら通る＝
静的リンクが原因」と結論したが、Kimigayo 側の動的版を作って
確かめていなかった。Alpine の `busybox-static` が rc=1 で失敗するのは
別の問題（静的リンクで何かが壊れる）で、**Kimigayo の SIGSEGV とは
症状も原因も違う。**

### 2. BusyBox と musl を Alpine と入れ替えた

| 組み合わせ | 結果 |
| --- | --- |
| **Kimigayo の BusyBox** × Alpine の musl | **rc=139（落ちる）** |
| Alpine の BusyBox × **Kimigayo の musl** | rc=1（`Address not available`。落ちない）|

**SIGSEGV は Kimigayo の BusyBox バイナリについてくる。musl ではない。**
（2 行目の `Address not available` は別件。名前解決で得た IPv6 アドレスに
つなぎに行っている疑い。Kimigayo の BusyBox ではこのエラーは出ない）

### 3. 残っている容疑

Alpine の BusyBox と Kimigayo の BusyBox の違い:

| 違い | Alpine | Kimigayo |
| --- | --- | --- |
| コンパイラ（arm64）| gcc | **clang（LLVM でクロスビルド）** |
| config | Alpine のもの | `src/busybox/config/*.config` |
| パッチ | Alpine のもの | `0001-vi-musl-libc-compatibility.patch`（vi のみ）|
| フラグ | Alpine の既定 | `-Os -fstack-protector-strong -D_FORTIFY_SOURCE=2 -fPIE` |

**gdb の下では落ちずに止まった**（ptrace で挙動が変わる）。
タイミング依存の可能性がある。

**次にやる実験**（1 つずつ潰す）:

1. **x86_64 をネイティブで試す。** x86_64 は gcc でビルドしている。
   手元（Apple Silicon）では QEMU なので `Connection reset by peer`
   （rc=1）になり判断できない。GitHub Actions の `ubuntu-latest` で
   `docker run` すればネイティブで確かめられる。
   **x86_64 で通れば clang が容疑者、落ちれば config が容疑者。**
2. **Alpine の config で Kimigayo の BusyBox をビルドする。**
   config とコンパイラを分離できる。
3. ストリップ前のバイナリ（`busybox_unstripped`）で gdb を使い、
   落ちる関数を特定する。

### どう扱うか（現時点）

**原因が分かるまで、利用者には「`wget` の HTTPS は使えない、
`curl` を持ち込む」と案内する。** 動的リンク化は原因ではなかったので、
これを理由に BusyBox のリンク方法を変える根拠にはならない。

## 回避策（利用者向け）

- **HTTP で済むなら HTTP を使う**（rc=0 で正常）
- **HTTPS が必要なら `curl` をビルド時に持ち込む。**
  `curl` はどのバリアントにも入っていない。
  手順は [examples/](../../examples/) と
  [インストールガイド](../user/INSTALLATION.md#追加ソフトウェアのインストール)

```dockerfile
FROM alpine:3.24 AS builder
RUN apk add --no-cache curl
RUN mkdir -p /stage/usr/bin /stage/usr/lib \
    && cp /usr/bin/curl /stage/usr/bin/ \
    && ldd /usr/bin/curl \
       | awk '/=>/ { print $3 } /^\/lib|^\/usr\/lib/ { print $1 }' \
       | grep -v 'ld-musl' | sort -u \
       | xargs -I{} cp -L {} /stage/usr/lib/

FROM ishinokazuki/kimigayo-os:3.0.1
COPY --from=builder /stage/ /
```

## 関連

- 公開文書への記載: [docs/user/QUICKSTART.md](../user/QUICKSTART.md) の
  「基本コマンド > ネットワーク」に既知の問題として書いてある
- `ssl_client` は `CONFIG_SSL_CLIENT`（既定 `y`、`select TLS`）で入る。
  `src/busybox/config/*.config` に明示していないので**既定で入っている**
  （BusyBox の config は「書かないと既定値が入る」。
  → [CLAUDE.md](../../CLAUDE.md)）

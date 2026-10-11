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
**状態**: 未修正。原因の切り分けは下記まで進んでいる。

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

## 切り分けが必要な点

Alpine と Kimigayo の差は**2つある。どちらが原因か未確定。**

| | Alpine 3.24 | Kimigayo v3.0.1 |
| --- | --- | --- |
| BusyBox の版 | **1.37.0** | **1.38.0** |
| リンク方法 | **動的**（`libc.musl-aarch64.so.1`）| **static-pie** |

**次にやるべき実験**（どちらの差が効いているかを1つずつ潰す）:

1. **1.38.0 を動的リンクでビルドして同じ取得をする。**
   落ちなければ static-pie 側の問題。落ちれば 1.38.0 の回帰。
2. **1.37.0 を static-pie でビルドして同じ取得をする。**
   落ちれば static-pie 側の問題。落ちなければ 1.38.0 の回帰。

```bash
# 版を変える場合は versions.mk を書き換える（直書きしない）
# config を変えただけではビルドがスキップされるので成果物を消す
rm -rf build/busybox-build-x86_64 build/busybox-install-x86_64
docker compose run --rm -T kimigayo-build make busybox \
  TARGET_ARCH=x86_64 IMAGE_TYPE=standard
```

**`-T` を忘れないこと**（`docker-compose.yml` が `tty: true` なので、
パイプに繋ぐと出力が消える）。

3. 上流に同じ報告があるかを確認する（`busybox.net` の bug tracker、
   `busybox` メーリングリスト）。1.38.0 は比較的新しいので、
   既知の回帰である可能性がある。

**デバッガはイメージに入っていない。** `gdb` を使うなら
マルチステージで持ち込むか、ビルド環境側で再現させる。

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

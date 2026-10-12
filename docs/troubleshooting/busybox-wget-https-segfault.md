# `wget` の HTTPS が Segmentation fault で落ちる（v3.0.1、解決済み）

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
**状態**: **v3.0.2（2026-10-12 公開）で修正済み。**
v3.0.1 以前の公開イメージでは再現する。

---

## 原因

**BusyBox の `CONFIG_FEATURE_WGET_OPENSSL`（既定 `y`）と、musl の `exit()` の
組み合わせ。** config に書いていなかったので既定の `y` が入っていた。

1. `FEATURE_WGET_OPENSSL` が有効だと、wget は HTTPS のたびにまず
   `openssl s_client` を **`xvfork()`** で起動しようとする
   （`networking/wget.c` の `spawn_https_helper_openssl()`）
2. イメージに `openssl` は無いので exec に失敗し、子は
   `xfunc_die()` → **`exit()`** を呼ぶ（`_exit()` ではない）。
   wget は `child_failed` を見て内蔵 TLS に切り替え、取得は成功する
3. musl の `exit()` は、同じスレッドからの二重呼び出しを検出するため、
   ロックに**自分のスレッド ID** を書く。**vfork の子は親とメモリを
   共有している**ので、このロックが親のスレッド ID のまま残る
4. 取得が終わって親が `exit()` すると、ロックが自分の ID なので
   「二重呼び出し」と判定され、`a_crash()`（アドレス 0 への書き込み）で落ちる

**glibc にはこのロックが無い**ので、glibc 環境では表に出ない。
Alpine の BusyBox が落ちないのは、Alpine は
`0017-properly-fix-wget-https-support.patch` で経路を変えており、
この経路を通らないため。

### どう突き止めたか

- **gdb の下では落ちずに止まる。** vfork と ptrace の相性で挙動が変わるため、
  gdb では追えなかった
- 動的リンクにした BusyBox に、SIGSEGV のハンドラを持つ共有ライブラリを
  `LD_PRELOAD` で差し込み、落ちた瞬間のレジスタを出した:

  ```
  SEGV pid=16 addr=0
  pc  /lib/ld-musl-aarch64.so.1  exit+0x78
  lr  busybox_unstripped         0xf6d4   ← xfunc_die の `bl exit` の直後
  ```

  `addr=0` かつ `exit` の中なので、musl の `a_crash()` と分かる。
  あとは `exit()` を二重に呼ぶ経路を探して、vfork の子に行き着いた

## 修正

`src/busybox/config/{standard,extended}.config` に明示した
（minimal は `wget` を持たない）:

```
CONFIG_FEATURE_WGET_HTTPS=y
# CONFIG_FEATURE_WGET_OPENSSL is not set
```

HTTPS は内蔵の TLS（**fork** した子で処理する）だけを使う。
arm64 ネイティブで、動的リンク・静的リンクとも
`example.com` / `cloudflare.com` に 12/12 回 rc=0 を確認した。

**回帰は `scripts/verify-image.sh` が見る。** ネットワークに頼らず決められるよう、
`/bin/busybox` に openssl を呼ぶ経路の文字列（`s_client`）が残っていないかを
調べる（v3.0.1 では見つかり、修正後は無い）。

## 誤っていた切り分け（記録）

最初の調査では原因を2回取り違えた。同じ遠回りをしないために残す。

| 当時の仮説 | なぜ誤りだったか |
| --- | --- |
| 静的リンクが原因 | 動的リンクにしても落ちた。Alpine の動的版と比べただけで、Kimigayo の動的版を作って確かめていなかった |
| arm64 の clang が原因 | GitHub Actions のネイティブ x86_64（gcc でビルド）でも落ちた。手元の x86_64 は QEMU で `Connection reset by peer` になり判断できていなかった |
| `FEATURE_WGET_OPENSSL` を切っても落ちる | **試験が無効だった。** config に行が無い項目を `sed` で書き換えようとして何も変わらず、`oldconfig` が既定値 `y` を入れ直していた |

**BusyBox の config は「書かないと既定値が入る」。** `DPKG`・`RPM`
（v3.0.0 までパッケージマネージャーが入っていた）、
`FEATURE_PATH_TRAVERSAL_PROTECTION`（cpio が展開先を脱出できた）に続いて
3 件目。項目を切り替えて試すときは、**`oldconfig` のあとの `.config` を
grep して、本当に切り替わったかを確かめる。**

## v3.0.1 以前を使っている場合の回避策

- **HTTP で済むなら HTTP を使う**（rc=0 で正常）
- 取得そのものは成功している（データは壊れていない）。終了コードが
  139 になるので、**シェルスクリプトで成功判定に使えない**
- **`curl` をビルド時に持ち込む**（どのバリアントにも入っていない）。
  手順は [examples/](../../examples/) と
  [インストールガイド](../user/INSTALLATION.md#追加ソフトウェアのインストール)

**証明書は検証しない。** BusyBox の wget は修正後も
`TLS certificate validation not implemented` のまま（上流の仕様）。
信頼できない経路で HTTPS を使うなら `curl` などを持ち込む。

## 関連

- 公開文書への記載: [docs/user/QUICKSTART.md](../user/QUICKSTART.md) の
  「基本コマンド > ネットワーク」
- `ssl_client` は `CONFIG_SSL_CLIENT`（既定 `y`、`select TLS`）で入る。
  内蔵 TLS の経路では使われない

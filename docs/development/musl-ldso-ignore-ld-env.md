# musl の動的ローダーで LD_PRELOAD を無視するパッチ（不採用の記録）

**状態: 不採用（2026-10-12）。** v3.0.2 には入っていない。
実験ブランチ `experiment/dynamic-busybox`（1ff0aa0・e0029b9）にあったものを、
ブランチを消す前にここへ移した。**採り直すときはここから復元する。**

## 何をするパッチか

musl の `ldso/dynlink.c` で、環境変数 `LD_PRELOAD` と `LD_LIBRARY_PATH` を
**常に**読まないようにする。上流の musl は suid / sgid のプロセスでだけ
無視する（`libc.secure`）。

## なぜ作ったか

公開中の v3.0.1 で、動的リンクの OpenRC にコードを注入できることを実測した:

```console
LD_PRELOAD=/root/evil.so /sbin/openrc --version
*** INJECTED via LD_PRELOAD ***
```

コンテナではほぼ全てが suid なしの root で動くので、上流の防御は一度も働かない。
当時の BusyBox が無事だったのは、静的リンクで動的ローダーを通らなかったからにすぎない。
BusyBox を動的リンクにする（v3.0.2 で採用）と `/bin/sh` も同じ面を持つので、
それを塞ぐ目的で作った。

## なぜ採らなかったか

1. **権限の境界ではない。** プロセスに環境変数を渡せる者は、そもそも任意の
   プログラムを実行できる。`LD_PRELOAD` を塞いでも新たに防げるものは無い。
   setuid / setgid では上流の musl が既に無視しており、
   Kimigayo のイメージには setuid / setgid のファイルが 1 つも無い
   （`verify-image.sh` が検査している）
2. **正当な使い方を壊す。** アプリが同梱したライブラリを `LD_LIBRARY_PATH` で
   指す使い方（マルチステージビルドで `/app/lib` に置くなど）が動かなくなる。
   ベースイメージとしては、こちらの方が困る
3. **ローダーを直接叩けば回避できる。** `ld-musl-*.so.1 --preload X prog` は残る

**実行時に注入を止めたいなら、ホスト側で塞ぐ。** `--read-only` と
`noexec` の tmpfs にすれば、注入するライブラリを置く場所が無くなる
（v3.0.1 で実測。→ [HARDENING_GUIDE.md](../security/HARDENING_GUIDE.md)）。

## 採り直すとき

`src/libc/patches/` に置けば `scripts/apply-musl-patches.sh` が当てる
（当たらなければビルドが失敗する）。CVE パッチではないので、
ファイル名に CVE ID は入れない（`PATCHED_CVES` に載らないように）。

### パッチ本体（musl 1.2.6 に対して作成）

```diff
--- a/ldso/dynlink.c
+++ b/ldso/dynlink.c
@@ -1817,11 +1817,20 @@
 	libc.secure = ((aux[0]&0x7800)!=0x7800 || aux[AT_UID]!=aux[AT_EUID]
 		|| aux[AT_GID]!=aux[AT_EGID] || aux[AT_SECURE]);
 
-	/* Only trust user/env if kernel says we're not suid/sgid */
-	if (!libc.secure) {
-		env_path = getenv("LD_LIBRARY_PATH");
-		env_preload = getenv("LD_PRELOAD");
-	}
+	/* Kimigayo: never take LD_LIBRARY_PATH or LD_PRELOAD from the
+	 * environment, regardless of libc.secure.
+	 *
+	 * Upstream only ignores them for suid/sgid processes. In a container
+	 * nearly everything runs as root without suid, so anyone who can set
+	 * an environment variable for a process (a service file, an exec'd
+	 * child, a crafted `docker exec -e`) can inject code into every
+	 * dynamically linked binary - including the init system.
+	 *
+	 * Library search paths that the system genuinely needs belong in
+	 * /etc/ld-musl-$ARCH.path (root-owned file, not caller-controlled).
+	 * Explicitly running the loader (`ld-musl-*.so.1 --preload X prog`)
+	 * still works; that requires the ability to exec arbitrary programs
+	 * already, so it grants nothing new. */
 
 	/* Activate error handler function */
 	error = error_impl;
```

### 回帰テスト（`scripts/verify-image.sh` に入れていたもの）

イメージにはコンパイラが無く、注入用のライブラリを作れない。代わりに
「BusyBox がリンクしていない `libeinfo.so.1` を `LD_PRELOAD` に指定し、
`/proc/self/maps` に現れるか」で判定する。未パッチの musl（alpine:edge）では
3 行現れ、パッチ済みでは 0 行だった。

```bash
if in_image "grep -q ld-musl /bin/busybox && echo dyn" | grep -q dyn; then
    preload_hits="$(in_image "LD_PRELOAD=/lib/libeinfo.so.1 /bin/busybox cat /proc/self/maps | grep -c libeinfo")"
    if [ "$preload_hits" = "0" ]; then
        pass "dynamic loader ignores LD_PRELOAD"
    else
        fail "dynamic loader honours LD_PRELOAD (libeinfo.so.1 was injected)"
        log_error "      src/libc/patches/0001-ldso-ignore-ld-env.patch が当たっていない疑い"
        log_error "      build/musl-patches.log を確認する"
    fi
else
    log_warn "  ! /bin/busybox is static; LD_PRELOAD check skipped (cannot observe the loader)"
fi
```

# Kimigayo OS Kernel Configurations

> **このディレクトリに追跡中の config は無い（2026-10-14 に削除）。**
> `scripts/build-kernel.sh` が読むのは `src/kernel/config/<arch>.config`
> （`x86_64.config` / `arm64.config`）だけで、今はどちらも無いので、
> 両アーキとも上流の defconfig + `apply_security_hardening()` で作られる。
> 削除したのはバリアント別の `minimal-` / `standard-` / `extended-x86_64.config`、
> `kimigayo_{x86_64,arm64}_defconfig`、プレースホルダの `x86_64.config`
> （どれもビルドの経路から読まれていなかった）。
>
> **カーネルは Docker イメージに入らない**（コンテナはホストのカーネルで動く）。
> カーネルを作るのはベアメタル／QEMU で試すときだけで、CI では作らない
> （→ [CLAUDE.md](../../../CLAUDE.md)「カーネルは CI で作らない」節）。

## 実際に使われる経路

`scripts/build-kernel.sh` の `generate_kernel_config()` と
`apply_security_hardening()` がこの順で決める。

1. `src/kernel/config/<arch>.config` が存在し、空でなく、
   `# This is a placeholder` の行を含まなければ、それを `.config` にして
   `olddefconfig` を回す
2. そうでなければ上流の defconfig を使う
   （x86_64 は `x86_64_defconfig`、arm64 は `defconfig`）。
   `<arch>.config` が無くても何も書き出さない（2026-10-13 までは
   プレースホルダを `src/kernel/config/<arch>.config` に書き出していた）
3. どちらの場合も、`scripts/config` で次を上書きしてから `olddefconfig` を回す
   - 有効: `RANDOMIZE_BASE`・`RANDOMIZE_MEMORY`・`SECURITY`・
     `SECURITY_DMESG_RESTRICT`・`HARDENED_USERCOPY`・`FORTIFY_SOURCE`・
     `STACKPROTECTOR`・`STACKPROTECTOR_STRONG`・`PANIC_ON_OOPS`（`PANIC_TIMEOUT=10`）
   - 無効: `NETFILTER` 系（`NETFILTER_ADVANCED`・`NETFILTER_XTABLES`・
     `IP_NF_IPTABLES`・`IP6_NF_IPTABLES`・`BRIDGE_NETFILTER`）
   - 2026-10-13 までは x86_64 で `--disable RETPOLINE` も呼んでいたが、
     6.18 ではシンボル名が `MITIGATION_RETPOLINE` に変わっていて
     何もしていなかったので外した（Spectre v2 の緩和は無効にしない）

**追跡中の `<arch>.config` は無い**ので、両アーキとも手順 2 の上流 defconfig で作られる。

**上書きはすべて効いている**（2026-10-13、6.18.55 を両アーキでビルドした
`.config` で確認。項目ごとの値は
[ARCHITECTURE.md のカーネル設定](../../../docs/developer/ARCHITECTURE.md#カーネル設定)）。
上書きしていない項目は上流の defconfig のままなので、アーキで差が出る
（`USER_NS`・`SQUASHFS` は arm64 だけ有効、`OVERLAY_FS` は arm64 だけモジュール、
`SECURITY_YAMA` はどちらも無効）。

**バリアント（minimal / standard / extended）でカーネル config は変わらない。**
バリアントの違いは BusyBox の config（`src/busybox/config/`）だけ。

## 手元でカーネルを作る

```bash
# カーネルのターゲットはビルドコンテナ内の build-system/Makefile にある
# （ホストの Makefile には無い）。数十分〜数時間かかる
docker compose run --rm kimigayo-build make kernel TARGET_ARCH=x86_64
```

CI で作るなら Actions から `manual-build-image-and-kernel.yml` を `build_kernel=true` で実行する。

### 自分の config を使いたいとき

`src/kernel/config/<arch>.config` として実物の config を置く
（`# This is a placeholder` の行を含めないこと）。それでも手順 3 の `scripts/config` による上書きは
かかる（netfilter は無効になる）。

```bash
cd build/kernel-src/linux-<version>
cp .config /path/to/kimigayo/src/kernel/config/x86_64.config
```

**`build/kernel/output/vmlinuz-<version>-<arch>` があるとビルドを飛ばす**
（config の編集は見ない）。config を変えたら成果物を捨ててからビルドする。

```bash
docker compose run --rm kimigayo-build make clean-kernel
```

## 確認

```bash
# ビルド後の config（<version> は versions.mk の KERNEL_VERSION）
grep -E "RANDOMIZE|STACKPROTECTOR|FORTIFY|NETFILTER=" \
  build/kernel/output/config-<version>-x86_64
```

`scripts/verify-kernel-security.sh` も同じファイルを読む。

## 参考資料

- [Linux Kernel Configuration](https://www.kernel.org/doc/html/latest/admin-guide/README.html)
- [Kernel Hardening](https://kernsec.org/wiki/index.php/Kernel_Self_Protection_Project)
- [Alpine Linux Kernel Config](https://git.alpinelinux.org/aports/tree/main/linux-lts)
- [Kimigayo OS Security Policy](../../../docs/security/SECURITY_POLICY.md)

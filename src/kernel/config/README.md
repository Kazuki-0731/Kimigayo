# Kimigayo OS Kernel Configurations

> **このディレクトリの config は、ビルドでほとんど使われていない（参考資料）。**
> 2026-10-12 時点で、`scripts/build-kernel.sh` が読むのは
> `src/kernel/config/<arch>.config`（`x86_64.config` / `arm64.config`）だけ。
> バリアント別の `minimal-` / `standard-` / `extended-x86_64.config` と
> `kimigayo_{x86_64,arm64}_defconfig` を読むビルド経路は無い。
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
   このとき `<arch>.config` が無ければプレースホルダを書き出す
3. どちらの場合も、`scripts/config` で次を上書きしてから `olddefconfig` を回す
   - 有効: `RANDOMIZE_BASE`・`RANDOMIZE_MEMORY`・`SECURITY`・
     `SECURITY_DMESG_RESTRICT`・`HARDENED_USERCOPY`・`FORTIFY_SOURCE`・
     `STACKPROTECTOR`・`STACKPROTECTOR_STRONG`・`PANIC_ON_OOPS`（`PANIC_TIMEOUT=10`）
   - 無効: `NETFILTER` 系（`NETFILTER_ADVANCED`・`NETFILTER_XTABLES`・
     `IP_NF_IPTABLES`・`IP6_NF_IPTABLES`・`BRIDGE_NETFILTER`）、
     x86_64 では `RETPOLINE`

**追跡中の `x86_64.config` はプレースホルダ**なので、x86_64 は手順 2 の
上流 defconfig で作られる。arm64 は `arm64.config` が追跡されていないため、
初回ビルドで手順 2 のプレースホルダが `src/kernel/config/arm64.config` に
書き出される（未追跡ファイルとして残る）。

**バリアント（minimal / standard / extended）でカーネル config は変わらない。**
バリアントの違いは BusyBox の config（`src/busybox/config/`）だけ。

## ファイル一覧

| ファイル | ビルドで使われるか |
| --- | --- |
| `x86_64.config` | 読まれるが、プレースホルダなので無視される |
| `minimal-x86_64.config` | 使われていない |
| `standard-x86_64.config` | 使われていない |
| `extended-x86_64.config` | 使われていない |
| `kimigayo_x86_64_defconfig` | 使われていない（参照は読まれていない `config.mk` と `src/kernel/build.py`・そのテストだけ） |
| `kimigayo_arm64_defconfig` | 同上 |

使われていない config の中身（モジュールの有無・IPv6・AppArmor など）は、
当時の検討を残したもので、ビルドされるカーネルの性質ではない。

## 手元でカーネルを作る

```bash
# カーネルのターゲットはビルドコンテナ内の build-system/Makefile にある
# （ホストの Makefile には無い）。数十分〜数時間かかる
docker compose run --rm kimigayo-build make kernel TARGET_ARCH=x86_64
```

CI で作るなら Actions から `manual-build.yml` を `build_kernel=true` で実行する。

### 自分の config を使いたいとき

`src/kernel/config/<arch>.config` を、プレースホルダ行を含まない実物の
config で置き換える。それでも手順 3 の `scripts/config` による上書きは
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

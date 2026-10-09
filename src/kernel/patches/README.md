# カーネルパッチ

`scripts/apply-kernel-patches.sh` がこのディレクトリの `*.patch` を
ファイル名順に `patch -p1` で当てる。

## 現在のパッチ

| ファイル | 内容 |
| --- | --- |
| `0001-security-hardening.patch` | **中身はコメントだけのプレースホルダ。実パッチではない。** 将来のセキュリティパッチを置く枠として残っている |

## 削除したパッチ（2026-10-09、Linux 6.6 → 6.18 の更新時）

次の3本はいずれも **GCC 15 で Linux 6.6 系をビルドするための
`-std=gnu11` 回避策**で、6.18 では上流が同じ内容を取り込んでいるため削除した。

| 削除したファイル | 何をしていたか | 6.18 での上流の対応 |
| --- | --- | --- |
| `0002-disable-retpoline-realmode.patch` | `arch/x86/realmode/rm/Makefile` で retpoline / return-thunk 系フラグを `filter-out` していた | `arch/x86/Makefile` の `REALMODE_CFLAGS := -std=gnu11 -m16 ...` が新規代入になっており、retpoline 系フラグを継承しない |
| `0003-efi-stub-std-gnu11.patch` | `drivers/firmware/efi/libstub/Makefile` に `-std=gnu11` を足していた | 同ファイルの `cflags-$(CONFIG_X86) += -m$(BITS) -D__KERNEL__ -std=gnu11 \` に取り込み済み |
| `0004-x86-boot-compressed-std-gnu11.patch` | `arch/x86/boot/compressed/Makefile` に `-std=gnu11` を足していた | 同ファイルの `KBUILD_CFLAGS += -std=gnu11` に取り込み済み |

復元が必要なら `git log --diff-filter=D --follow -- src/kernel/patches/` から辿れる。

### 0002 を消したあとに realmode のリンクが落ちた（2026-10-09）

削除後の CI で x86_64 のカーネルビルドが次で落ちた。

```
ld: arch/x86/realmode/rm/trampoline_64.o: in function `verify_cpu':
(.text+0x183): undefined reference to `__x86_return_thunk'
```

**これはパッチを消したのが原因ではなく、`scripts/build-kernel.sh` が
`REALMODE_CFLAGS` を丸ごと上書きしていたのが原因。** 上流の値にある
`-D__DISABLE_EXPORTS` が落ちるため、`arch/x86/include/asm/linkage.h` の

```c
#if defined(CONFIG_MITIGATION_RETHUNK) && !defined(__DISABLE_EXPORTS) && !defined(BUILD_VDSO)
#define RET	jmp __x86_return_thunk
```

が realmode のアセンブリにも効いてしまう（`RET` はマクロなので、
C のフラグを `filter-out` しても消えない）。上書きをやめて上流の
`REALMODE_CFLAGS` を使うようにしたら通った
（`make ARCH=x86_64 arch/x86/realmode/` で `LD realmode.elf` まで確認、
`CONFIG_MITIGATION_RETHUNK=y`）。

**教訓: 上流の変数を「追加」ではなく「代入」で差し替えると、
そこに入っていた他の定義も一緒に消える。**

## パッチを足す・消すときの注意

**`apply-kernel-patches.sh` は `patch -p1 --dry-run` が通らないパッチを
`log_warn` して `return 0` する。つまり当たらないパッチは黙ってスキップされ、
ビルドは成功したように見える。**

カーネルのバージョンを上げたら必ず確認する:

```bash
grep -i 'not applicable' build/kernel-patches.log
```

「適用されているつもり」のまま進まないこと。詳細は
[CLAUDE.md](../../../CLAUDE.md) の「パッチはなぜ存在するか」節。

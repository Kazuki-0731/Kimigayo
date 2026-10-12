#!/usr/bin/env python3
"""イメージに入っている**すべての** ELF の強化状態を検査する。

使い方（verify-image.sh から呼ぶ）:
    docker export <container> | python3 -I scripts/check-elf-hardening.py -

なぜ必要か:
    2026-10-11 まで、成果物の強化を機械的に見ていたのは /bin/busybox の
    ELF type（PIE か）だけだった。OpenRC・librc・libeinfo・libc.so の
    RELRO / BIND_NOW / 非実行スタックは手で readelf を叩いて確かめただけで、
    ビルドフラグを1つ落としても CI は緑のままになる。

    イメージには readelf が無く、開発機（macOS）にも無い。
    docker export の tar を標準入力で受け、ELF ヘッダを直接読む。
    展開しないので、/etc/shadow の権限やデバイスファイルで詰まらない。

検査項目（1つでも欠けたら失敗）:
    PIE       e_type が ET_DYN（ET_EXEC はアドレスが固定で ASLR が効かない）
    RELRO     PT_GNU_RELRO がある
    BIND_NOW  DT_BIND_NOW / DF_BIND_NOW / DF_1_NOW のいずれか
              （無いと GOT が実行中ずっと書き込み可能のまま残る）
    NX stack  PT_GNU_STACK があり、実行権限が無い
              （PT_GNU_STACK が無いと、カーネルは実行可能スタックとして扱う）
    SSP       動的リンクで libc から SSP_MIN_IMPORTS 個以上の関数を取り込む
              ELF は __stack_chk_fail を参照している
              （-fstack-protector-strong でコンパイルされた痕跡）

SSP を足した経緯（2026-10-13）:
    公開済み v3.0.2 の arm64 では、/sbin/openrc・librc・libeinfo を含む
    OpenRC のほぼ全部が __stack_chk_fail を参照していなかった。
    scripts/build-openrc.sh が arm64 の CFLAGS から
    -fstack-protector-strong を外していたため。x86_64 は付いていたので、
    **片方のアーキだけ強化が抜けていた**（PIE のときと同じ形）。
    上の4項目はリンカの出力で決まるので、コンパイラフラグの抜けは
    見えていなかった。

    判定は「1ファイルずつ」。-fstack-protector-strong は配列や
    アドレスを取る局所変数を持つ関数にしかカナリアを入れないので、
    取り込む関数が数個の小さなヘルパ（OpenRC の is_newer_than・
    shell_var など。x86_64 でも参照が無い）は参照しないのが正常。
    そこで SSP_MIN_IMPORTS 未満のものは見ない。
    v3.0.2 の実測: x86_64 は 20 個以上取り込む ELF が全部参照あり
    （参照の無い最大は get_options の 16 個）、arm64 は rc-status・
    librc・openrc など 20 本以上が参照なしで落ちる。
    （arm64 の start-stop-daemon / supervise-daemon は参照ありになるが、
    静的リンクした Alpine の libcap.a 由来。OpenRC 自身の分ではない）

    静的リンク（static-PIE）は動的シンボル表が無く、ここでは判定しない。
    __stack_chk_fail を定義している側（libc.so）も対象外。

対象は x86_64 / aarch64 の 64bit リトルエンディアンだけ。
それ以外の ELF が入っていたら、それ自体を異常として報告する。
"""
import struct
import sys
import tarfile

ET_EXEC, ET_DYN = 2, 3
PT_DYNAMIC = 2
PT_GNU_STACK, PT_GNU_RELRO = 0x6474E551, 0x6474E552
PF_X = 1
DT_NULL, DT_BIND_NOW, DT_FLAGS, DT_FLAGS_1 = 0, 24, 30, 0x6FFFFFFB
DF_BIND_NOW, DF_1_NOW = 0x8, 0x1
DT_NEEDED = 1
SHT_DYNSYM = 11
SHN_UNDEF = 0
# これ未満しか関数を取り込まない ELF はスタック保護を見ない（→ 冒頭の SSP）
SSP_MIN_IMPORTS = 20
EM_NAMES = {62: "x86_64", 183: "aarch64"}


def inspect(data):
    """問題点のリストを返す（空なら合格）。

    実行ファイル（PIE / static-PIE）・共有ライブラリを区別せず、
    同じ基準で見る。どれも root で動くプロセスに載るので、
    緩めてよい種類は無い。
    """
    if data[4] != 2 or data[5] != 1:
        return ["not 64-bit little-endian"]
    e_type, e_machine = struct.unpack_from("<HH", data, 16)
    e_phoff, = struct.unpack_from("<Q", data, 32)
    e_phentsize, e_phnum = struct.unpack_from("<HH", data, 54)

    problems = []
    if e_machine not in EM_NAMES:
        problems.append("unexpected machine %d" % e_machine)

    segs = []
    for i in range(e_phnum):
        off = e_phoff + i * e_phentsize
        p_type, p_flags, p_offset = struct.unpack_from("<IIQ", data, off)
        p_filesz, = struct.unpack_from("<Q", data, off + 32)
        segs.append((p_type, p_flags, p_offset, p_filesz))
    types = {s[0] for s in segs}

    if e_type == ET_EXEC:
        problems.append("not PIE (ET_EXEC)")
    elif e_type != ET_DYN:
        problems.append("unexpected e_type %d" % e_type)

    if PT_GNU_RELRO not in types:
        problems.append("no RELRO")

    bind_now = False
    needed = False
    for p_type, _, p_offset, p_filesz in segs:
        if p_type != PT_DYNAMIC:
            continue
        for off in range(p_offset, p_offset + p_filesz, 16):
            tag, val = struct.unpack_from("<qQ", data, off)
            if tag == DT_NULL:
                break
            if tag == DT_NEEDED:
                needed = True
            if (tag == DT_BIND_NOW
                    or (tag == DT_FLAGS and val & DF_BIND_NOW)
                    or (tag == DT_FLAGS_1 and val & DF_1_NOW)):
                bind_now = True
    if not bind_now:
        problems.append("no BIND_NOW")

    stack = [s for s in segs if s[0] == PT_GNU_STACK]
    if not stack:
        problems.append("no PT_GNU_STACK (stack is executable)")
    elif stack[0][1] & PF_X:
        problems.append("executable stack")

    if needed:
        problems.extend(check_stack_protector(data))

    return problems


def dynamic_symbols(data):
    """(取り込むシンボル名の集合, 定義するシンボル名の集合) を返す。

    .dynsym をセクションヘッダから探す。strip しても .dynsym は残る
    （動的リンクに必要なため）。見つからなければ None。
    """
    e_shoff, = struct.unpack_from("<Q", data, 40)
    e_shentsize, e_shnum = struct.unpack_from("<HH", data, 58)
    if e_shoff == 0 or e_shnum == 0:
        return None
    secs = []
    for i in range(e_shnum):
        off = e_shoff + i * e_shentsize
        sh_type, = struct.unpack_from("<I", data, off + 4)
        sh_offset, sh_size = struct.unpack_from("<QQ", data, off + 24)
        sh_link, = struct.unpack_from("<I", data, off + 40)
        sh_entsize, = struct.unpack_from("<Q", data, off + 56)
        secs.append((sh_type, sh_offset, sh_size, sh_link, sh_entsize))
    for sh_type, sh_offset, sh_size, sh_link, sh_entsize in secs:
        if sh_type != SHT_DYNSYM or sh_link >= len(secs):
            continue
        str_off = secs[sh_link][1]
        entsize = sh_entsize or 24
        imports, defines = set(), set()
        for j in range(sh_size // entsize):
            st_name, _, _, st_shndx = struct.unpack_from(
                "<IBBH", data, sh_offset + j * entsize)
            if st_name == 0:
                continue
            start = str_off + st_name
            name = data[start:data.index(b"\0", start)].decode("ascii", "replace")
            (imports if st_shndx == SHN_UNDEF else defines).add(name)
        return imports, defines
    return None


def check_stack_protector(data):
    """動的リンクの ELF がスタック保護付きでコンパイルされているか。"""
    syms = dynamic_symbols(data)
    if syms is None:
        return ["no .dynsym (cannot check stack protector)"]
    imports, defines = syms
    if "__stack_chk_fail" in defines:
        return []  # 提供する側（libc.so）
    if len(imports) < SSP_MIN_IMPORTS:
        return []  # 小さすぎて判定できない（→ 冒頭の SSP）
    if "__stack_chk_fail" not in imports:
        return ["no stack protector (__stack_chk_fail not referenced, "
                "%d imports)" % len(imports)]
    return []


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "-"
    tf = (tarfile.open(fileobj=sys.stdin.buffer, mode="r|*") if src == "-"
          else tarfile.open(src, mode="r:*"))

    checked, bad = 0, []
    for m in tf:
        if not m.isfile() or m.size < 64:
            continue
        f = tf.extractfile(m)
        head = f.read(4)
        if head != b"\x7fELF":
            continue
        data = head + f.read()
        checked += 1
        problems = inspect(data)
        if problems:
            bad.append("/%s: %s" % (m.name.lstrip("./"), ", ".join(problems)))

    print("checked=%d bad=%d" % (checked, len(bad)))
    for line in bad:
        print(line)
    # ELF が1つも見つからないのは検査が壊れている（tar を読めていない）
    return 1 if bad or checked == 0 else 0


if __name__ == "__main__":
    sys.exit(main())

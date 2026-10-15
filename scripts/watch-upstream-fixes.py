#!/usr/bin/env python3
"""上流のセキュリティ情報と Kimigayo の差分を確かめる。

使い方:
    python3 -I scripts/watch-upstream-fixes.py                  # 報告を標準出力に
    python3 -I scripts/watch-upstream-fixes.py --json out.json  # 要対応を JSON にも
        （security.yml がこれを読み、まだ非公開の Project に無いものだけ
         Project と Discord で知らせる。公開の Issue にはしない）

なぜ必要か:
    scan-image.sh（Grype）は NVD の CPE で照合するので、CPE がまだ無い CVE と、
    Alpine や Debian だけが持つ修正は見えない。2026-10-14 に初めて突き合わせた
    ところ、Alpine が同じ BusyBox 1.38.0 に当てている CVE パッチを Kimigayo が
    持っていない・Debian で未解決の BusyBox の CVE が 20 件近くある、という
    差分が見つかった。人が見に行かない限り分からないので毎日ここで確かめる。

見るもの（出荷物に入っている 4 つ。カーネルはイメージに入らないので見ない）:
    Debian   security-tracker の source-package ページに載る全 CVE
             （修正待ちの CVE は CVE ページの unstable の Fixed Version も）
    Alpine   aports の APKBUILD（GitHub ミラー）。Kimigayo と同じ上流版を
             持つブランチで当てているパッチと、secfixes の CVE
    上流 git リリース前の修正。BusyBox・musl・OpenRC の公式リポジトリの直近
             GIT_DEPTH コミットのうち、件名か本文がセキュリティらしいもの
             （SECURITY_WORDS）。git で中身なしの浅い clone をして読む。
             GitHub の mirror/busybox は 2024-09 で止まっていて使えない。
             CVE-2026-108119 の修正 382008b はこの経路でしか見えなかった
             （2026-10-09 に上流に入ったが、リリースにも Debian / Alpine にも無い）
    CISA KEV 実際に悪用されている脆弱性の一覧

Kimigayo 側の状態は docs/security/upstream-triage.tsv（仕分け済みの一覧）と
src/*/patches/ のファイル名。**仕分け済みの一覧に無いもの**が「新しい差分」。

要対応として出すもの（JSON の kind）:
    new        仕分けていない CVE / Alpine のパッチが現れた
    fix        watching（修正待ち）の CVE に修正が出た
    exploited  Kimigayo が直していない CVE が KEV に載った（実際に悪用されている）

判定できない（ページの形が変わった・取得に失敗した）ときは黙って
「差分なし」と言わずに失敗する（exit 1）。
"""
import json
import re
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRIAGE = ROOT / "docs" / "security" / "upstream-triage.tsv"

DEBIAN_PKG_URL = "https://security-tracker.debian.org/tracker/source-package/{pkg}"
DEBIAN_CVE_URL = "https://security-tracker.debian.org/tracker/{cve}"
# aports は GitHub の公式ミラーから取る。gitlab.alpinelinux.org は GitHub
# Actions からのアクセスをボット扱いして 418 を返す（2026-10-14 に実測。
# 手元からは通るので気づきにくい）。ミラーの中身は GitLab と同じ
ALPINE_URL = ("https://raw.githubusercontent.com/alpinelinux/aports/"
              "{branch}/main/{pkg}/APKBUILD")
GIT_DEPTH = 150
# 件名・本文がこれに当たるコミットを「セキュリティの修正かもしれない」として出す。
# 取りこぼすより出しすぎる方に倒す（仕分ければ次から出ない）
SECURITY_WORDS = re.compile(
    r"overflow|out[- ]of[- ]bounds|\boob\b|use[- ]after[- ]free|double[- ]free|"
    r"\bCVE-|attack|exploit|secur|sanitiz|inject|traversal|escape|malicious|"
    r"NULL (pointer )?deref|infinite (loop|recursion)|stack exhaustion|"
    r"\bDoS\b|denial of service|privilege|unsafe|toctou|race", re.I)
KEV_URL = ("https://www.cisa.gov/sites/default/files/feeds/"
           "known_exploited_vulnerabilities.json")

# 出荷物に入っている構成要素
#   version   versions.mk の変数名（None は Alpine の <ALPINE_VERSION>-stable の版を使う）
#   patches   Kimigayo のパッチの置き場（None はパッチを当てない）
#   alpine_patches  Alpine のパッチを差分として見るか。libcap は Alpine の
#                   libcap-static をそのままリンクしているので、Alpine の
#                   パッチは最初から入っている
COMPONENTS = [
    {"name": "busybox", "debian": "busybox", "alpine": "busybox",
     "version": "BUSYBOX_VERSION", "patches": "src/busybox/patches",
     "alpine_patches": True, "git": "https://git.busybox.net/busybox.git"},
    {"name": "musl", "debian": "musl", "alpine": "musl",
     "version": "MUSL_VERSION", "patches": "src/libc/patches",
     "alpine_patches": True, "git": "https://git.musl-libc.org/git/musl"},
    {"name": "openrc", "debian": "openrc", "alpine": "openrc",
     "version": "OPENRC_VERSION", "patches": None, "alpine_patches": True,
     "git": "https://github.com/OpenRC/openrc.git"},
    # libcap は Alpine のバイナリをリンクしているので、上流 git ではなく
    # Alpine の更新（secfixes）と Debian で見る
    {"name": "libcap", "debian": "libcap2", "alpine": "libcap",
     "version": None, "patches": None, "alpine_patches": False, "git": None},
]

# 修正済みとして扱う（KEV に載っても知らせない）状態
RESOLVED = {"patched", "fixed-upstream", "not-affected", "baseline"}
STATUSES = RESOLVED | {"todo", "watching", "accepted", "unknown"}


class WatchError(Exception):
    pass


def fetch(url):
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            return r.read().decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001  取得の失敗は全部「判定できない」
        raise WatchError(f"{url}: {e}") from e


def versions():
    out = {}
    for line in (ROOT / "versions.mk").read_text().splitlines():
        m = re.match(r"([A-Z0-9_]+)\s*\?=\s*(\S+)", line)
        if m:
            out[m.group(1)] = m.group(2)
    return out


def load_triage(path=TRIAGE):
    """{ID: (component, status, note)}。形が崩れた行は失敗にする。"""
    triage = {}
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip() or line.startswith("#"):
            continue
        cols = line.split("\t")
        if len(cols) < 3 or cols[2] not in STATUSES:
            raise WatchError(f"{path.name}:{n}: 形が違う（ID<TAB>component<TAB>status<TAB>note）: {line}")
        triage[cols[0]] = (cols[1], cols[2], cols[3] if len(cols) > 3 else "")
    return triage


def debian_package_cves(html):
    """source-package ページに載る全 CVE ID（open・unimportant・resolved）。"""
    if "Resolved issues" not in html and "Open issues" not in html:
        raise WatchError("Debian の source-package ページの形が変わった")
    return set(re.findall(r'href="/tracker/(CVE-\d{4}-\d+)"', html))


def debian_status(html, pkg):
    """CVE ページから unstable の Fixed Version と Notes の URL を返す。表が読めなければ None。"""
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)
    m = re.search(re.escape(pkg) + r" source \(unstable\) (\S+)", text)
    if not m:
        return None
    notes = re.findall(r"https?://\S+", text.split(" Notes ", 1)[1]) if " Notes " in text else []
    return m.group(1), notes


def apkbuild_info(text):
    """(pkgver, source= のパッチ名の一覧, APKBUILD に出てくる CVE ID の集合)"""
    m = re.search(r"^pkgver=(\S+)", text, re.M)
    if not m:
        raise WatchError("APKBUILD に pkgver が無い")
    src = re.search(r'^source="(.*?)"', text, re.M | re.S)
    patches = re.findall(r"([\w.+-]+\.patch)\b", src.group(1)) if src else []
    return m.group(1), patches, set(re.findall(r"CVE-\d{4}-\d+", text))


def upstream_commits(url):
    """[(短い sha, 件名, 本文)]。直近 GIT_DEPTH コミットを中身なしで取って読む。"""
    with tempfile.TemporaryDirectory() as d:
        try:
            subprocess.run(["git", "clone", "-q", "--bare", "--filter=blob:none",
                            f"--depth={GIT_DEPTH}", "--single-branch", url, d],
                           check=True, capture_output=True, timeout=300)
            log = subprocess.run(["git", "-C", d, "log", "--format=%H%x1f%s%x1f%b%x1e"],
                                 check=True, capture_output=True, text=True).stdout
        except (subprocess.SubprocessError, OSError) as e:
            raise WatchError(f"{url}: git で取れない: {e}") from e
    out = []
    for rec in log.split("\x1e"):
        parts = rec.strip("\n").split("\x1f")
        if len(parts) == 3:
            out.append((parts[0][:12], parts[1], parts[2]))
    if not out:
        raise WatchError(f"{url}: コミットが 1 つも読めない")
    return out


def security_commits(commits):
    return [(sha, title) for sha, title, body in commits
            if SECURITY_WORDS.search(title) or SECURITY_WORDS.search(body)]


def our_patches(comp):
    if not comp["patches"]:
        return set(), set()
    files = list((ROOT / comp["patches"]).glob("*.patch"))
    return ({p.name for p in files},
            {c for p in files for c in re.findall(r"CVE-\d{4}-\d+", p.name)})


def main(argv):
    json_out = argv[argv.index("--json") + 1] if "--json" in argv else None
    ver = versions()
    alpine_branches = ["master", f"{ver['ALPINE_VERSION']}-stable"]
    triage = load_triage()
    findings, lines = [], []

    def add(kind, key, text):
        findings.append({"kind": kind, "key": key, "text": text})

    known_cves = {}  # CVE -> component（KEV の照合用）
    for comp in COMPONENTS:
        name = comp["name"]
        patch_names, patched_cves = our_patches(comp)

        # Alpine: 同じ上流版を持つブランチのパッチと secfixes
        apk = {b: apkbuild_info(fetch(ALPINE_URL.format(branch=b, pkg=comp["alpine"])))
               for b in alpine_branches}
        our_ver = ver.get(comp["version"]) if comp["version"] else apk[alpine_branches[1]][0]
        alpine_cves = set()
        for branch, (pkgver, patches, cves) in apk.items():
            alpine_cves |= cves
            if not comp["alpine_patches"] or pkgver != our_ver:
                continue
            for p in patches:
                key = f"alpine:{comp['alpine']}:{p}"
                # 名前が違っても同じ CVE のパッチなら持っている（Alpine は
                # CVE-2026-40200.patch、Kimigayo は 0001-CVE-2026-40200-....patch）
                cves_in_name = set(re.findall(r"CVE-\d{4}-\d+", p))
                if (p in patch_names or key in triage
                        or (cves_in_name and cves_in_name <= patched_cves)):
                    continue
                add("new", key, f"{name} {our_ver}: Alpine（{branch}）が当てているパッチ `{p}` を Kimigayo は持っていない")

        # 上流 git: リリース前の修正（セキュリティらしいコミット）
        if comp["git"]:
            for sha, title in security_commits(upstream_commits(comp["git"])):
                key = f"upstream:{name}:{sha}"
                if key in triage:
                    continue
                add("new", key, f"{name}: 上流のコミット {sha}「{title.strip()}」が"
                    "セキュリティの修正かもしれない（未仕分け）")

        # Debian: 載っている全 CVE
        deb_cves = debian_package_cves(fetch(DEBIAN_PKG_URL.format(pkg=comp["debian"])))
        for cve in sorted(deb_cves | alpine_cves):
            known_cves[cve] = name
            if cve in triage or cve in patched_cves:
                continue
            st = debian_status(fetch(DEBIAN_CVE_URL.format(cve=cve)), comp["debian"])
            where = f"Debian unstable: {st[0]}" if st else "Debian: 表なし"
            add("new", cve, f"{name}: 仕分けていない {cve}（{where}）{DEBIAN_CVE_URL.format(cve=cve)}")

        # 修正待ちの CVE に修正が出たか
        for cve, (c, status, _) in triage.items():
            if c != name or status != "watching" or not cve.startswith("CVE-"):
                continue
            st = debian_status(fetch(DEBIAN_CVE_URL.format(cve=cve)), comp["debian"])
            if st is None:
                raise WatchError(f"{cve}: Debian の表を読めない")
            fixed, notes = st
            hits = [b for b, (_, _, cves) in apk.items() if cve in cves]
            if fixed != "(unfixed)" or hits:
                src = ", ".join(([f"Debian unstable {fixed}"] if fixed != "(unfixed)" else [])
                                + [f"Alpine {b}" for b in hits])
                add("fix", cve, f"{name}: 修正待ちの {cve} に修正が出た（{src}）"
                    + "".join(f" {n}" for n in notes))
            else:
                lines.append(f"- {cve}（{name}）: 修正待ち。まだ修正なし")

    # 実際に悪用されている脆弱性（CISA KEV）
    kev = json.loads(fetch(KEV_URL))
    for v in kev.get("vulnerabilities", []):
        cve = v.get("cveID", "")
        product = (v.get("vendorProject", "") + " " + v.get("product", "")).lower()
        comp = known_cves.get(cve) or next(
            (c["name"] for c in COMPONENTS if c["name"] in product), None)
        if comp is None:
            continue
        status = triage.get(cve, ("", "unknown", ""))[1]
        if status in RESOLVED:
            continue
        add("exploited", cve, f"**{comp}: {cve} が実際に悪用されている（CISA KEV）**。"
            f"Kimigayo の状態: {status}")

    todo = sorted(k for k, (_, s, _) in triage.items() if s == "todo")
    lines.append(f"- 取り込み待ち（todo）: {len(todo)} 件" + (f"（{', '.join(todo)}）" if todo else ""))
    for f in findings:
        lines.insert(0, f"- [{f['kind']}] {f['text']}")
    print("\n".join(lines) if lines else "- 差分なし")

    if json_out:
        Path(json_out).write_text(json.dumps(findings, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except WatchError as e:
        print(f"[ERROR] 判定できない: {e}", file=sys.stderr)
        sys.exit(1)

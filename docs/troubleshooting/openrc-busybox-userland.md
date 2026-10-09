# OpenRC の init スクリプトが BusyBox の userland で動かない

**症状の種類**: サービスが起動しない / `openrc` が ERROR を出す /
サービスは「起動した」と言うのに設定が効いていない

**最初に踏んだ日**: 2026-10-10（Kimigayo v2.0.1 時点のコードで発覚）

---

## 1. `unable to exec '/etc/init.d/<name>'`

### 症状

```
$ docker run --rm kimigayo-os:standard-x86_64 /sbin/openrc default
 * Caching service dependencies ... [ ok ]
unable to exec `/etc/init.d/sysctl': No such file or directory
unable to exec `/etc/init.d/bootmisc': No such file or directory
unable to exec `/etc/init.d/loopback': No such file or directory
...
```

**37 本のうち 36 本が起動できない**状態だった。

### 原因

OpenRC の `prefix` が `/usr` なので、インストールされる init スクリプトの
shebang が `#!/usr/sbin/openrc-run` になっている。Kimigayo は Alpine に
合わせて OpenRC のバイナリを `/sbin` に置いていたため、shebang の指す先が
存在しなかった。

**`execve(2)` はインタプリタが見つからないとき `ENOENT` を返す。**
だからエラーメッセージは「スクリプトが無い」と読めるが、
実際に無いのは**インタプリタ**。

### 直し方

`/usr/sbin/<name> -> ../../sbin/<name>` のシンボリックリンクを張る
（`scripts/build-rootfs.sh` の OpenRC コピー処理）。
シンボリックリンクなのでイメージサイズはほぼ増えない。

### なぜ見逃していたか

- ファイルは存在するので、存在チェックでは通る
- `rc-update show` は init スクリプトを **exec しない**（ファイルを読むだけ）
- `verify-image.sh` も当時は exec していなかった

**いまは `verify-image.sh` が全 init スクリプトの `describe` を実際に実行する。**

---

## 2. BusyBox が持たない長オプション

### 症状

```
$ docker run --rm kimigayo-os:standard-x86_64 /bin/sh -c '/sbin/openrc boot'
sysctl | * Configuring kernel parameters ...
/sbin/sysctl: unrecognized option: system
sysctl | * Unable to configure some kernel parameters [ !! ]
sysctl | * ERROR: sysctl failed to start
```

### 原因

**OpenRC の上流 init スクリプトは GNU procps / coreutils / kmod を前提に
長オプションを使う。** Kimigayo の userland は BusyBox だけなので、
実装されていないオプションはその場で usage を吐いて失敗する。

全スクリプトを走査した結果（BusyBox 1.38.0 / OpenRC 0.63.2）:

| init スクリプト | 使っている長オプション | Docker で実行されるか |
| --- | --- | --- |
| `sysctl` | `sysctl --system` | **される** |
| `bootmisc` | `mount --bind` | **される** |
| `root` | `mount --make-rshared` | されない（`keyword -docker`） |
| `modules` | `modprobe --first-time --use-blacklist --verbose` | されない |
| `hwclock` | `hwclock --adjust` `--hctosys` | されない |
| `fsck` | （`-p` 相当） | されない |

**`depend()` に `keyword -docker` があるスクリプトは、OpenRC が
コンテナを検出して起動しない**（起動時に `[DOCKER]` と表示される）。
Kimigayo はコンテナ向け OS なので、実際に走る 2 本だけを直してある。

### 直し方

`scripts/build-rootfs.sh` の `patch_openrc_for_busybox()` が、
OpenRC をコピーしたあとに置換する。

| 置換前 | 置換後 |
| --- | --- |
| `sysctl ${quiet} --system` | `kimigayo_sysctl ${quiet}`（BusyBox の `-p FILE...` を使う関数を追記） |
| `mount --bind / $dir` | `mount -o bind / $dir` |

**置換は「前にあったこと」と「後に消えたこと」の両方を確認する。**
OpenRC を上げて上流が書き換えたらビルドが止まるようにしてある。

### ここで踏んだ副作用（3 つ）

1. **`awk` の `sub()` は第1引数を正規表現として扱う。**
   `sysctl ${quiet} --system` のような `$` `{` `}` を含む文字列は
   マッチしない。置換が 0 件なのに「✓ 置き換えた」と報告していた。
   → `index()` + `substr()` で文字列として置換する
2. **`awk ... > new && mv new old` は実行権限を落とす。**
   `sysctl` と `bootmisc` が 0644 になり、OpenRC から起動できなくなった。
   → `cat new > old` で書き戻す（inode とモードが保たれる）
3. **検査を `[ -x ]` で絞ると、権限が落ちたスクリプトが検査対象から外れる。**
   上記 2 の事故が起きたのに 22 項目すべて通った。
   → **shebang の有無で対象を決め、実行権限が無いことを失敗として扱う**

---

## 3. サービスが `[ ok ]` なのに設定が効いていない

### 症状

`sysctl` が `[ ok ]` と出るのに `/etc/sysctl.d/*.conf` の値が入っていない。

### 原因（2 つ重なっていた）

1. **非特権コンテナでは `/proc/sys` が read-only で渡される。**
   どのキーも書けない

   ```
   proc /proc/sys proc ro,nosuid,nodev,noexec,relatime 0 0
   ```

2. **BusyBox の `sysctl` は書き込みに失敗しても終了コード 0 を返す**（実測）。
   `error setting key ...: Read-only file system` を 11 行出したうえで
   `[ ok ]` になっていた

### 直し方

- `/proc/mounts` を見て `/proc/sys` が `ro` なら、
  **失敗ではなく「ホストの担当」として抜ける**
  （コンテナのカーネルパラメータはホストが設定する。
  `docker run --sysctl` または `--privileged`）
- 書き込みを試した場合は**出力を見て失敗を判定する**（終了コードは信用しない）

**`[ -w /proc/sys/kernel ]` では判定できない。**
read-only mount でも root には writable と返る（実測）。

### 確認方法

```bash
# 非特権: スキップされること
docker run --rm kimigayo-os:standard-x86_64 /bin/sh -c '/sbin/openrc boot' 2>&1 |
  grep 'managed by the host'

# 特権: 実際に効くこと
docker run --rm --privileged kimigayo-os:standard-x86_64 /bin/sh -c \
  '/sbin/openrc boot >/dev/null 2>&1; sysctl kernel.pid_max vm.swappiness'
# kernel.pid_max = 32768
# vm.swappiness = 0
```

---

## 非特権コンテナで残る「正常な」エラー

これらは OpenRC や Kimigayo の問題ではなく、**権限が無いだけ**。
`--privileged` または必要な capability を付けると消える。

| 出力 | 必要なもの |
| --- | --- |
| `ip: RTNETLINK answers: Operation not permitted` | `CAP_NET_ADMIN` |
| `mount: permission denied (are you root?)` | `CAP_SYS_ADMIN` |
| `umount: can't unmount ...: Operation not permitted` | `CAP_SYS_ADMIN` |
| `dmesg: klogctl: Operation not permitted` | `CAP_SYSLOG` |

---

## 関連

- [busybox-static-linking.md](busybox-static-linking.md) — arm64 のリンクの罠
- `scripts/verify-image.sh` — ここに書いた検査が入っている
- `scripts/build-rootfs.sh` の `patch_openrc_for_busybox()`

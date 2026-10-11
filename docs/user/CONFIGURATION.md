# Kimigayo OS システム設定ガイド

このガイドでは、Kimigayo OS の設定方法について説明します。

## 前提: 設定をどこで行うか

**Kimigayo OS は VPS 上の Docker コンテナで動かすことを想定した OS です。**
rootfs だけを詰めたイメージで、**カーネルはイメージに入りません**
（コンテナはホストのカーネルで動きます）。パッケージマネージャーも
意図的に持ちません。

このため、ブートする OS の設定ガイドとは置き場所が変わります。

| 何を設定するか | どこで行うか |
|---------------|-------------|
| ホスト名・DNS・IP アドレス | **コンテナの外**（`docker run` のオプション、Compose、Kubernetes）|
| カーネルパラメータ・モジュール | **ホスト側**（`/proc/sys` はコンテナから読み取り専用）|
| ファイアウォール | **ホスト側**（`iptables` はイメージに入っていません）|
| 追加ソフトウェア | **ビルド時**（マルチステージビルド。実行中には追加できません）|
| サービス（OpenRC） | **コンテナ内**。ただし OpenRC を PID 1 にする必要があります |
| タイムゾーン・ロケール | 下記のとおり制約があります |

**既定の PID 1 は `/bin/sh` です。** `Dockerfile.runtime` は `ENTRYPOINT` を
持たず `CMD ["/bin/sh"]` なので、`docker run` しただけでは OpenRC は
動いていません（→ [サービス管理](#サービス管理)）。

## 目次

- [基本設定](#基本設定)
- [ネットワーク設定](#ネットワーク設定)
- [サービス管理](#サービス管理)
- [セキュリティ設定](#セキュリティ設定)
- [リソースとチューニング](#リソースとチューニング)
- [カーネルに関わる設定](#カーネルに関わる設定)
- [モニタリング](#モニタリング)
- [バックアップと復元](#バックアップと復元)
- [トラブルシューティング](#トラブルシューティング)
- [参考リソース](#参考リソース)

## 基本設定

### ホスト名の設定

**コンテナの外から指定するのが確実です。** コンテナ内で
`echo ... > /etc/hostname` しても、すでに設定されたホスト名は変わりません。

```bash
docker run -it --hostname my-server ishinokazuki/kimigayo-os:latest
```

```yaml
# docker-compose.yml
services:
  app:
    image: ishinokazuki/kimigayo-os:3.0.1
    hostname: my-server
```

```bash
# コンテナ内で確認
hostname
```

### `/etc/hosts` への追記

**`/etc/hosts` はコンテナランタイムが生成します。** コンテナ内で編集しても
再作成すると消えるので、外から渡します。

```bash
docker run -it --add-host myhost:10.0.0.9 ishinokazuki/kimigayo-os:latest
```

```bash
# コンテナ内で確認
grep myhost /etc/hosts
# => 10.0.0.9	myhost
```

### タイムゾーンの設定

**タイムゾーンのデータベースは入っていません。** `/usr/share/zoneinfo` と
`/etc/localtime` が無いため、既定では UTC になります。

```bash
date +%Z
# => UTC
```

必要なゾーンだけをビルド時に持ち込みます。

```dockerfile
FROM alpine:3.24 AS tz
RUN apk add --no-cache tzdata

# 版を固定する。latest は毎リリースで中身が変わります。
FROM ishinokazuki/kimigayo-os:3.0.1
COPY --from=tz /usr/share/zoneinfo/Asia/Tokyo /etc/localtime
ENV TZ=Asia/Tokyo
```

ゾーン一式が必要なら `/usr/share/zoneinfo/` ごと `COPY` しますが、
数 MB 増えてイメージサイズが倍以上になります。**使うゾーンだけに絞るのが
この OS の趣旨に合います。**

### ロケールの設定

**musl libc はロケールをほぼ実装していません。** `C` と `C.UTF-8` 相当だけが
あり、`ja_JP.UTF-8` を設定しても照合順序や月名の翻訳は変わりません
（文字エンコーディングは常に UTF-8 なので、日本語の表示自体は行えます）。
`/etc/locale.conf` も存在しません。

```bash
# 環境変数として渡すことはできる（アプリ側が見る場合に意味を持つ）
docker run -it -e LANG=ja_JP.UTF-8 ishinokazuki/kimigayo-os:latest
```

**libc のロケール機能に依存するアプリを動かす場合は、この OS は
適していません。** glibc ベースのイメージを検討してください。

### キーボード配列

**コンテナには該当しません。** `/etc/conf.d/keymaps` と `keymaps` サービスは
物理コンソール向けのもので、`docker exec` や `docker attach` の入力は
ホスト側の端末が扱います。

## ネットワーク設定

### ネットワークはランタイムが設定する

**イメージに `networking` サービスは入っていません。**
`/etc/network/interfaces` というファイル自体は置かれていますが、
**それを読むサービスが無いため、書き換えても何も起きません。**

```bash
# 確認はコンテナ内から行える
ip link show
ip addr show
```

### 静的 IP アドレスの設定

コンテナの外からネットワークとアドレスを指定します。

```bash
docker network create --subnet 192.168.100.0/24 kimigayo-net

docker run -it --network kimigayo-net --ip 192.168.100.10 \
  ishinokazuki/kimigayo-os:latest
```

```yaml
# docker-compose.yml
services:
  app:
    image: ishinokazuki/kimigayo-os:3.0.1
    networks:
      kimigayo-net:
        ipv4_address: 192.168.100.10

networks:
  kimigayo-net:
    ipam:
      config:
        - subnet: 192.168.100.0/24
```

### DHCP

**通常は不要です。** `docker run` ではランタイムがアドレスを割り当てます。
`--network host` や特殊な構成で自分で取得する必要がある場合は、
BusyBox の `udhcpc` を使います（`dhclient` は入っていません）。

```bash
udhcpc -i eth0
```

### DNS 設定

**`/etc/resolv.conf` はコンテナランタイムが生成します。** コンテナ内で
編集しても再作成時に消えるので、外から渡します。

```bash
docker run -it --dns 1.1.1.1 --dns 8.8.8.8 ishinokazuki/kimigayo-os:latest
```

```bash
# コンテナ内で確認
grep nameserver /etc/resolv.conf
```

### 無線 LAN

**対象外です。** 無線インターフェースはホストが扱います。

## サービス管理

Kimigayo OS は Init に **OpenRC** を使います。`rc-service`・`rc-update`・
`rc-status`・`openrc-run`・`start-stop-daemon` はすべてイメージに入っています。

### まず OpenRC を PID 1 にする

**既定の PID 1 は `/bin/sh` なので、そのままでは `rc-service` が使えません。**
OpenRC が起動していない状態で叩くと、こう警告されて失敗します。

```
 * You are attempting to run an openrc service on a
 * system which openrc did not boot.
```

**`/sbin/init` を PID 1 にします。** `/etc/inittab` が `openrc sysinit` →
`openrc boot` → `openrc default` を順に実行します。

```bash
docker run -d --name myapp --entrypoint /sbin/init \
  ishinokazuki/kimigayo-os:3.0.1
```

```dockerfile
FROM ishinokazuki/kimigayo-os:3.0.1
COPY myservice /etc/init.d/myservice
RUN chmod +x /etc/init.d/myservice && rc-update add myservice default
CMD ["/sbin/init"]
```

**権限が足りない処理は失敗しますが、起動そのものは続行します。**
通常の `docker run` では次がログに出ます（いずれも無害です）。

| ログ | 理由 |
|------|------|
| `Unable to mount tmpfs on /run` | `--tmpfs /run` を渡せば解消します |
| `kernel parameters are managed by the host (/proc/sys is read-only)` | 設計どおり。ホスト側で設定します |
| `ip: RTNETLINK answers: Operation not permitted` | `lo` の設定はランタイムが済ませています |
| `dmesg: klogctl: Operation not permitted` | `CAP_SYSLOG` が無いため |

**サービスを使わないなら OpenRC を PID 1 にする必要はありません。**
アプリを直接 PID 1 にする方が軽く、シグナルの扱いも素直です。

### サービスの基本操作

```bash
# 状態の一覧
rc-status

# 個別の操作
rc-service <service-name> start
rc-service <service-name> stop
rc-service <service-name> restart
rc-service <service-name> status
```

### 自動起動の設定

```bash
# ランレベルに追加・削除
rc-update add <service-name> default
rc-update del <service-name> default

# 登録内容の確認
rc-update show default
rc-update show
```

### ランレベル

イメージに入っているランレベルは `sysinit` / `boot` / `default` /
`nonetwork` / `shutdown` です。既定の `default` には `local` と `netmount` が
登録されています。

```bash
rc-update show default
# =>                 local | default
# =>              netmount | default
```

### カスタムサービスの作成

```bash
cat > /etc/init.d/myservice <<'EOS'
#!/sbin/openrc-run

name="My Service"
command="/usr/bin/myapp"
command_args="--port 8080"
command_background=true
pidfile="/run/myservice.pid"

depend() {
    need localmount
}
EOS

chmod +x /etc/init.d/myservice
rc-update add myservice default
rc-service myservice start
```

**`depend()` に `net` や `firewall` を書かないこと。** どちらのサービスも
イメージに入っていないので、依存が解決できず起動しません。
ネットワークはコンテナ起動時点で用意されています。

## セキュリティ設定

**この OS の攻撃面の小ささは、まず「無いこと」で成り立っています。**
パッケージマネージャーが無いので、侵入されても追加ツールを
取得・インストールできません。以下はその上に積む設定です。

### ファイアウォール

**`iptables` はイメージに入っていません。** コンテナの通信制御は
ホスト側かオーケストレータで行います。

```bash
# 公開するポートだけを明示する
docker run -d -p 127.0.0.1:8080:8080 ishinokazuki/kimigayo-os:latest

# 外部との通信が不要なら切り離す
docker run -it --network none ishinokazuki/kimigayo-os:latest
```

Kubernetes なら `NetworkPolicy` で制御します。

### SSH

**`sshd` はイメージに入っていません。** コンテナへの接続は
`docker exec` / `kubectl exec` を使います。

```bash
docker exec -it myapp /bin/sh
```

**`sshd` を入れることは推奨しません。** 攻撃面が増え、
不変インフラという前提も崩れます。

### ユーザーと権限

**`sudo` と `wheel` グループはありません。** `/etc/group` に `wheel` が
無いので `adduser username wheel` は失敗します。root からの降格には
BusyBox の `su`、実行ユーザーの指定にはコンテナのオプションを使います。

```bash
# 非 root で実行する
docker run -it --user 1000:1000 ishinokazuki/kimigayo-os:latest

# コンテナ内でユーザーを作る場合（BusyBox の adduser）
adduser username
```

### 権限を落とす

```bash
# ルートファイルシステムを読み取り専用にし、書ける場所だけ tmpfs で与える
docker run -it --read-only --tmpfs /tmp --tmpfs /run \
  ishinokazuki/kimigayo-os:latest

# ケーパビリティを落とす
docker run -it --cap-drop ALL ishinokazuki/kimigayo-os:latest

# 特権昇格を禁じる
docker run -it --security-opt no-new-privileges ishinokazuki/kimigayo-os:latest
```

読み取り専用にすると、`/etc` などへの書き込みは
`Read-only file system` で拒否されます。`/tmp` と `/run` は
tmpfs として書き込めます。

詳細は [セキュリティガイド](../security/SECURITY_GUIDE.md) と
[ハードニングガイド](../security/HARDENING_GUIDE.md) を参照してください。

## リソースとチューニング

### メモリと CPU の制限

**コンテナの外から指定します。** `/etc/fstab` に追記しても効きません。

```bash
# メモリを 512MB に制限し、スワップを無効化する
docker run -it --memory=512m --memory-swap=512m \
  ishinokazuki/kimigayo-os:latest

# CPU を 0.5 コア相当に制限する
docker run -it --cpus=0.5 ishinokazuki/kimigayo-os:latest

# 特定のコアに固定する
docker run -it --cpuset-cpus=0,1 ishinokazuki/kimigayo-os:latest
```

**コンテナ内で `swapon` はできません。** スワップはホストの設定と
`--memory-swap` で決まります。

```bash
# コンテナ内から見た使用量（ホストの値が見えることがあります）
free -m
top
```

**`ps aux --sort=-%mem` は使えません**（BusyBox の `ps` は `--sort` を
解しません）。`top` を使うか、ホストから `docker stats` を見てください。

### 一時ファイルを RAM に置く

```bash
docker run -it --tmpfs /tmp:rw,noexec,nosuid,size=64m \
  ishinokazuki/kimigayo-os:latest
```

### ディスク使用量の確認

```bash
df -h
find / -xdev -type f -size +10M -exec ls -lh {} \;
```

**`logrotate` は入っていません。** ログは `docker logs` 側で扱い、
ランタイムのログドライバで上限を決めます。

```bash
docker run -d --log-opt max-size=10m --log-opt max-file=3 \
  ishinokazuki/kimigayo-os:latest
```

### 起動時間について

**イメージを軽くしても起動は速くなりません。** v3.0.1 の実測は
`docker run` が 0.61 秒ですが、同じ条件で Alpine 0.62 秒・
Ubuntu 24.04 0.59 秒で、**100MB の Ubuntu がいちばん速い**という結果です。
測っている時間のほとんどがコンテナランタイム自身の処理なので、
イメージの中身はほとんど効きません。

差が出るのは常駐メモリ（Kimigayo 232KB / Alpine 276KB / Ubuntu 312KB）と
サイズの方です。測定条件は
[docs/benchmarks/lifecycle.md](../benchmarks/lifecycle.md) を参照してください。

## カーネルに関わる設定

**カーネルはイメージに入りません。コンテナはホストのカーネルで動きます。**
したがって GRUB・`/boot`・`grub-mkconfig`・カーネルの再ビルドは
このガイドの対象外です（`/boot` 自体が存在しません）。

### sysctl

**コンテナからは読めますが書けません。**

```bash
sysctl net.ipv4.ip_forward
# => net.ipv4.ip_forward = 1

sysctl -w net.ipv4.ip_forward=1
# => sysctl: error setting key 'net.ipv4.ip_forward': Read-only file system
```

**名前空間化されたものはコンテナの外から渡せます。**

```bash
docker run -it --sysctl net.ipv4.ip_local_port_range="10000 60000" \
  ishinokazuki/kimigayo-os:latest
```

名前空間化されていないもの（`kernel.kptr_restrict` など）は拒否されます。

```
invalid argument "kernel.kptr_restrict=2" for "--sysctl" flag: sysctl 'kernel.kptr_restrict=2' is not whitelisted
```

**これらはホスト側で設定します。** イメージには
`/etc/sysctl.d/99-kimigayo-performance.conf` が入っており、
ベアメタルや VM でこの rootfs を使う場合にだけ効きます。
コンテナでは `sysctl` サービスが
`kernel parameters are managed by the host` と報告してスキップします。

### カーネルモジュール

**コンテナからは操作できません。** `/lib/modules` が無いためです。

```bash
modprobe overlay
# => modprobe: can't change directory to '/lib/modules': No such file or directory
```

`lsmod` は `/proc/modules` を読むので動きますが、**表示されるのは
ホストのモジュール**です。モジュールのロードはホストで行ってください。

## モニタリング

### ログの確認

**`/var/log` は空で、syslog は動いていません。** 標準出力・標準エラーに
出したものを `docker logs` で読むのが基本です。

```bash
# ホスト側から
docker logs -f myapp
kubectl logs -f <pod>
```

`dmesg` はコンテナからは使えません（`Operation not permitted`。
`CAP_SYSLOG` が必要です）。

### リソース監視

```bash
# コンテナ内から
top

# ホスト側から（こちらが正確）
docker stats
```

## バックアップと復元

**不変インフラなので、コンテナの中身をバックアップする設計にしないでください。**
イメージは Dockerfile から再現し、**残すべきものはボリュームに置きます。**

```bash
# ボリュームのバックアップ（ホスト側で実行）
docker run --rm -v myapp-data:/data -v "$PWD:/backup" \
  ishinokazuki/kimigayo-os:3.0.1 \
  tar czf /backup/data-backup.tar.gz -C /data .

# 復元
docker run --rm -v myapp-data:/data -v "$PWD:/backup" \
  ishinokazuki/kimigayo-os:3.0.1 \
  tar xzf /backup/data-backup.tar.gz -C /data
```

**設定を手で変えてバックアップする運用にしないこと。** 変更は
Dockerfile か `docker run` のオプションに書き、イメージの版で管理します。

## トラブルシューティング

### コンテナが起動しない・即座に終了する

**GRUB のリカバリモードはありません。** まずログを読みます。

```bash
docker logs <container-id>
docker inspect <container-id> --format '{{.State.ExitCode}} {{.State.Error}}'
```

よくある原因:

| 症状 | 原因 |
|------|------|
| すぐ終了する | PID 1 のプロセスが終了した（`CMD` が常駐しない）|
| `exec format error` | アーキテクチャ不一致。`--platform linux/amd64` か `linux/arm64` を指定する |
| `Error relocating ...: symbol not found` | 持ち込んだ実行ファイルの共有ライブラリが足りない（`ldd` で解決する）|
| `rc-service` が警告して失敗 | OpenRC が PID 1 で起動していない（→ [サービス管理](#サービス管理)）|

```bash
# シェルで中を調べる
docker run -it --entrypoint /bin/sh ishinokazuki/kimigayo-os:3.0.1
```

### ネットワークに接続できない

```bash
# コンテナ内から
ip link show
ip addr show
grep nameserver /etc/resolv.conf

# ホスト側から
docker network ls
docker network inspect bridge
```

**`/etc/network/interfaces` を直しても効きません**（読むサービスが
イメージに入っていません）。ネットワークはランタイム側の設定で直します。

### 設定を変えたのに反映されない

**`/etc/hostname`・`/etc/hosts`・`/etc/resolv.conf` はランタイムが管理します。**
コンテナ内で書き換えても再作成で消えます。`--hostname` / `--add-host` /
`--dns` で渡してください。

### ソフトウェアを追加したい

パッケージマネージャーは**意図的に入れていません**。マルチステージビルドで
ビルド時に持ち込みます。手順と動く例は
[インストールガイド](INSTALLATION.md#追加ソフトウェアのインストール)と
[examples/](../../examples/) を参照してください。

## 参考リソース

- **GitHub リポジトリ**: https://github.com/Kazuki-0731/Kimigayo
- **Issue 報告**: https://github.com/Kazuki-0731/Kimigayo/issues
- **Docker 使用ガイド**: [DOCKER_USAGE.md](DOCKER_USAGE.md)
- **インストールガイド**: [INSTALLATION.md](INSTALLATION.md)
- **クイックスタート**: [QUICKSTART.md](QUICKSTART.md)
- **セキュリティガイド**: [../security/SECURITY_GUIDE.md](../security/SECURITY_GUIDE.md)
- **OpenRC ドキュメント**: https://wiki.gentoo.org/wiki/OpenRC
- **BusyBox ドキュメント**: https://busybox.net/downloads/BusyBox.html

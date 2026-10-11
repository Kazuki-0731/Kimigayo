# Kimigayo OS クイックスタートガイド

このガイドでは、Kimigayo OS を使い始めるための基本的な操作を説明します。

## 始める前に

**Kimigayo OS は Docker コンテナのベースイメージとして使う OS です。**

- 成果物は **rootfs だけを詰めた Docker イメージ**で、**カーネルは入りません**
  （コンテナはホストのカーネルで動きます）
- **パッケージマネージャーを持ちません。** これは欠落ではなく意図した設計で、
  侵入されても追加ツールを取得できないようにするためのものです。
  ソフトウェアは**ビルド時**に持ち込みます
- **ベアメタル起動・ISO イメージは対象外です**（ブートローダーも ISO も
  作っていません）

## 目次

- [起動して中に入る](#起動して中に入る)
- [どのバリアントを選ぶか](#どのバリアントを選ぶか)
- [基本コマンド](#基本コマンド)
- [ソフトウェアの追加](#ソフトウェアの追加)
- [システムの設定](#システムの設定)
- [サービスの管理](#サービスの管理)
- [コンテナの停止](#コンテナの停止)
- [パフォーマンス実績](#パフォーマンス実績)
- [トラブルシューティング](#トラブルシューティング)
- [次のステップ](#次のステップ)

## 起動して中に入る

```bash
# Standard バリアント（推奨）
docker run -it ishinokazuki/kimigayo-os:latest

# シェルプロンプトが表示されます
/ #
```

**版を固定する場合**（`latest` は毎リリースで中身が変わります）:

```bash
docker run -it ishinokazuki/kimigayo-os:3.0.1
```

**バックグラウンドで起動して後から入る**:

```bash
docker run -d --name myapp ishinokazuki/kimigayo-os:3.0.1 sleep infinity
docker exec -it myapp /bin/sh
```

**既定の PID 1 は `/bin/sh` です。** `Dockerfile` に `ENTRYPOINT` が無く
`CMD ["/bin/sh"]` なので、**OpenRC（Init）は動いていません。**
サービスを使いたい場合は [サービスの管理](#サービスの管理)を参照してください。

```bash
# 中身の確認
cat /etc/os-release
# => VERSION_ID=3.0.1
# => VERSION_CODENAME=himawari
```

## どのバリアントを選ぶか

| バリアント | イメージ | BusyBox アプレット | タグ |
|-----------|---------|------------------|------|
| Minimal | 2.62MB / arm64 2.98MB | 367 | `latest-minimal` / `3.0.1-minimal` |
| **Standard**（推奨）| 2.76MB / arm64 3.13MB | 400 | `latest` / `latest-standard` / `3.0.1-standard` |
| Extended | 2.78MB / arm64 3.17MB | 411 | `latest-extended` / `3.0.1-extended` |

**Minimal には `vi`・`wget`・`du`・`less` が入っていません。**
対話的に触るなら Standard 以上を選んでください。

```bash
# 使えるコマンドの一覧
busybox --list | wc -l
busybox --list | grep <name>
```

**`curl` はどのバリアントにも入っていません**（`wget` を使うか、
ビルド時に持ち込みます）。

## 基本コマンド

BusyBox ベースなので、標準的な Unix コマンドが使えます。
**ただし GNU 版と比べてオプションが少ないものがあります。**

### ファイル操作

```bash
ls -la
cd /etc
cat /etc/os-release
vi /etc/myapp.conf       # Minimal には入っていません
cp source.txt dest.txt
mv oldname.txt newname.txt
rm file.txt
```

### システム情報

```bash
# OS のバージョン
cat /etc/os-release

# カーネルのバージョン（ホストのカーネルが表示されます）
uname -a

# CPU・メモリ・ディスク
cat /proc/cpuinfo
free -m
df -h
uptime
```

**`uname` と `free` が返すのはホストの情報です。** コンテナに割り当てた
制限は反映されません。制限を見るならホスト側で `docker stats` を使います。

### プロセス管理

```bash
ps aux
top
kill <PID>
kill -9 <PID>
```

**`ps aux --sort=-%mem` は使えません**（BusyBox の `ps` は `--sort` を
解しません）。`top` を使ってください。

### ネットワーク

```bash
# インターフェースとアドレス
ip addr show
ip link show

# 名前解決
nslookup example.com

# リスニングポート
netstat -tuln

# HTTP 取得（Minimal には wget が入っていません）
wget -O- http://example.com
```

**`ping` は既定では失敗します**（ICMP ソケットに `CAP_NET_RAW` が必要で、
通常の `docker run` では付きません）。疎通確認には `nslookup` を使うか、
`--cap-add NET_RAW` を付けて起動してください。

> **既知の問題: `wget` の HTTPS は v3.0.1 では使えません。**
> arm64 ネイティブでは、本文のダウンロード自体は成功するものの直後に
> Segmentation fault（終了コード 139）になります。Standard と Extended の
> 両方で再現します。x86_64（Apple Silicon 上の QEMU エミュレーション）では
> `error getting response: Connection reset by peer`（終了コード 1）で
> 失敗しました。**HTTP（`http://`）は両方とも正常です。**
> HTTPS の取得が必要な場合は、ビルド時に `curl` を持ち込んでください
> （→[ソフトウェアの追加](#ソフトウェアの追加)）。

## ソフトウェアの追加

**パッケージマネージャーはありません。** マルチステージビルドで
ビルド時に持ち込みます。

**実行ファイルだけを `COPY` しても動きません。** 共有ライブラリが
足りないと実行時に `Error relocating ...: symbol not found` で落ちます。
**依存は手で列挙せず `ldd` で解決します。**

```dockerfile
FROM alpine:3.24 AS builder
RUN apk add --no-cache curl

RUN mkdir -p /stage/usr/bin /stage/usr/lib \
    && cp /usr/bin/curl /stage/usr/bin/ \
    && ldd /usr/bin/curl \
       | awk '/=>/ { print $3 } /^\/lib|^\/usr\/lib/ { print $1 }' \
       | grep -v 'ld-musl' \
       | sort -u \
       | xargs -I{} cp -L {} /stage/usr/lib/

# 版を固定する。latest は毎リリースで中身が変わります。
FROM ishinokazuki/kimigayo-os:3.0.1
COPY --from=builder /stage/ /

CMD ["/bin/sh"]
```

動く例は [examples/](../../examples/)（nginx / Node.js / Python）にあります。

## システムの設定

**設定の多くはコンテナの外から渡します。** コンテナ内で
`/etc/hostname`・`/etc/hosts`・`/etc/resolv.conf` を書き換えても、
ランタイムが管理しているため再作成で消えます。

```bash
docker run -it \
  --hostname my-kimigayo \
  --add-host myhost:10.0.0.9 \
  --dns 1.1.1.1 \
  ishinokazuki/kimigayo-os:3.0.1
```

**ネットワークはランタイムが設定します。** `/etc/network/interfaces` という
ファイルは置かれていますが、**それを読む `networking` サービスが
イメージに入っていない**ので、書き換えても何も起きません。静的 IP は
`docker network` 側で指定します。

**タイムゾーンのデータベースは入っていません**（`/usr/share/zoneinfo` が
無いので既定は UTC）。必要なゾーンだけをビルド時に `COPY` します。

詳しい手順は[システム設定ガイド](CONFIGURATION.md)にまとめてあります。

## サービスの管理

Init は **OpenRC** です。`rc-service`・`rc-update`・`rc-status` は
イメージに入っています。

**ただし既定の PID 1 は `/bin/sh` なので、そのままでは使えません。**
OpenRC が起動していない状態で叩くとこう警告されて失敗します。

```
 * You are attempting to run an openrc service on a
 * system which openrc did not boot.
```

**`/sbin/init` を PID 1 にします。**

```bash
docker run -d --name myapp --entrypoint /sbin/init \
  ishinokazuki/kimigayo-os:3.0.1

docker exec -it myapp rc-status
```

```bash
# 起動したあとは通常どおり
rc-service <service-name> start
rc-service <service-name> status
rc-update add <service-name> default
rc-update show default
```

**サービスを使わないなら OpenRC を PID 1 にする必要はありません。**
アプリを直接 PID 1 にする方が軽く、シグナルの扱いも素直です。
詳細は[システム設定ガイド](CONFIGURATION.md#サービス管理)を参照してください。

## コンテナの停止

**`poweroff` / `reboot` / `shutdown` は使わないでください。**
`shutdown` はそもそも入っておらず、`poweroff` と `reboot` は
コンテナ内では何も起きずに終了コード 0 を返します。

```bash
# ホスト側から停止する
docker stop myapp
docker rm myapp

# 対話シェルから抜ける
exit
```

## パフォーマンス実績

v3.0.1 の実測値（2026-10-11、ホストは macOS / Apple Silicon）:

| 指標 | 実測値 | 目標値 |
|------|-------|--------|
| イメージサイズ (Minimal) | 2.62MB / arm64 2.98MB | < 5MB |
| イメージサイズ (Standard) | 2.76MB / arm64 3.13MB | < 15MB |
| イメージサイズ (Extended) | 2.78MB / arm64 3.17MB | < 50MB |
| 起動時間 | 0.61秒 | < 10秒 |
| 常駐メモリ | 232KB | < 128MB |
| BusyBox コマンド性能 | Alpine 比 0.90〜1.12x | Alpine 同等 |

> **起動時間の 0.61 秒は「Kimigayo が速い」という意味ではありません。**
> 同じ条件で測ると Alpine 0.62 秒・Ubuntu 24.04 0.59 秒で、
> **100MB の Ubuntu がいちばん速い**という結果です。測っている時間の
> ほとんどがコンテナランタイム自身の処理なので、イメージの中身は
> ほとんど効きません。差が出るのは常駐メモリ
> （Kimigayo 232KB / Alpine 276KB / Ubuntu 312KB）とサイズの方です。

測定条件は [docs/benchmarks/lifecycle.md](../benchmarks/lifecycle.md) に
記録しています。

## トラブルシューティング

### コマンドが見つからない

```bash
# このイメージで使えるものを確認する
busybox --list | grep <name>
```

Minimal に無いものは Standard / Extended にあることがあります
（→ [どのバリアントを選ぶか](#どのバリアントを選ぶか)）。
どれにも無いものは[ソフトウェアの追加](#ソフトウェアの追加)で持ち込みます。

### コンテナが即座に終了する

PID 1 のプロセスが終了すると、コンテナも終わります。

```bash
docker logs <container-id>
docker inspect <container-id> --format '{{.State.ExitCode}}'
```

常駐させたいなら、常駐するプロセスを PID 1 にしてください
（`sleep infinity`、アプリ本体、`/sbin/init` など）。

### `Error relocating ...: symbol not found`

持ち込んだ実行ファイルの共有ライブラリが足りていません。
`ldd` で解決する形に直してください（→[ソフトウェアの追加](#ソフトウェアの追加)）。

### `exec format error`

アーキテクチャの不一致です。`--platform linux/amd64` または
`--platform linux/arm64` を指定してください。

### ネットワークに接続できない

```bash
ip link show
grep nameserver /etc/resolv.conf
nslookup example.com

# ホスト側から
docker network ls
docker network inspect bridge
```

`/etc/network/interfaces` を直しても効きません（読むサービスが
イメージに入っていません）。

### ディスク容量不足

```bash
df -h
find / -xdev -type f -size +10M -exec ls -lh {} \;
```

## 次のステップ

- [Docker 使用ガイド](DOCKER_USAGE.md) - ユースケース別のサンプル
- [インストールガイド](INSTALLATION.md) - Docker / Kubernetes / Podman
- [システム設定ガイド](CONFIGURATION.md) - 設定の詳細
- [セキュリティガイド](../security/SECURITY_GUIDE.md) - 安全な運用

## ヘルプとサポート

- **GitHub リポジトリ**: https://github.com/Kazuki-0731/Kimigayo
- **Issue 報告**: https://github.com/Kazuki-0731/Kimigayo/issues
- **GitHub Discussions**: https://github.com/Kazuki-0731/Kimigayo/discussions

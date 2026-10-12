# Kimigayo OS

**Google の distroless と Alpine Linux のハイブリッドアプローチ**

軽量・セキュアなコンテナ向けOS

## 設計思想

Kimigayo OSは、**distroless** と **Alpine Linux** の両方の長所を組み合わせています：

### distroless からの継承
- ✅ **不変インフラ**: パッケージマネージャーなし、実行時の変更を排除
- ✅ **最小攻撃面**: 実行時にパッケージをインストールする仕組みを持たない
- ✅ **軽量**: 2.46〜3.01MB のイメージサイズ（v3.0.2、バリアント × アーキテクチャ）

### Alpine Linux からの継承
- ✅ **musl libc**: 軽量でシンプルなCライブラリ
- ✅ **BusyBox**: デバッグ可能なシェルとUnixコマンド
- ✅ **OpenRC**: シンプルで軽量なInitシステム
- ✅ **セキュリティ強化**: 全 ELF を PIE・Full RELRO・非実行スタックでビルド（Stack Protector は x86_64 の全 ELF。arm64 の OpenRC には付いていない）

### Alpine/distroless との違い

| 特徴 | distroless | Alpine | **Kimigayo OS** |
|------|-----------|--------|----------------|
| パッケージマネージャー | ❌ | ✅ apk | ❌ **なし** |
| シェル/ユーティリティ | ❌ | ✅ | ✅ **BusyBox** |
| パッケージマネージャーで実行時に足せるか | ❌ | ✅ | ❌ **足せない** |
| デバッグ容易性 | ❌ | ✅ | ✅ **容易** |

**Kimigayo OS = distrolessのセキュリティ + Alpineの実用性**

## 主な特徴

- 🪶 **超軽量**: Standard（x86_64）**2.60MB** / arm64 2.98MB（v3.0.2、2026-10-12 実測）
- 💾 **常駐メモリ**: 288KB（Alpine 272KB / Ubuntu 24.04 312KB と同程度。同条件で実測）
- 🔒 **セキュリティ強化**: 全実行ファイルを PIE・Full RELRO・非実行スタックでビルド
- 🛡️ **最小攻撃面**: パッケージマネージャーを意図的に排除（`apk` も `dpkg` も無い）
- ✍️ **署名済み**: Cosign のキーレス署名（v3.0.2 から）。SBOM は GitHub Release に添付
- 🏗️ **3 バリアント**: minimal / standard / extended から選べる
- 🌐 **マルチアーキテクチャ**: x86_64とARM64をサポート

## 基盤技術

- musl libc
- BusyBox
- OpenRC initシステム

**イメージに入っているのは rootfs だけです。**
カーネルは含まれません（コンテナはホストのカーネルで動きます）。

## ドキュメント

- [インストールガイド](https://github.com/Kazuki-0731/Kimigayo/blob/main/docs/user/INSTALLATION.md)
- [クイックスタートガイド](https://github.com/Kazuki-0731/Kimigayo/blob/main/docs/user/QUICKSTART.md)
- [セキュリティガイド](https://github.com/Kazuki-0731/Kimigayo/blob/main/docs/security/SECURITY_GUIDE.md)

## クイックスタート

### イメージの取得

```bash
# Standardバリアント（推奨）
docker pull ishinokazuki/kimigayo-os:latest

# Minimalバリアント
docker pull ishinokazuki/kimigayo-os:latest-minimal

# Extendedバリアント
docker pull ishinokazuki/kimigayo-os:latest-extended
```

### コンテナの実行

```bash
# 対話的シェル
docker run -it ishinokazuki/kimigayo-os:latest /bin/sh

# コマンド実行
docker run ishinokazuki/kimigayo-os:latest uname -a
```

### ベースイメージとして使用

**ビルド時にすべてを用意し、実行時には変更しない**のが前提の使い方です。
開発の柔軟さは Alpine 側（`apk`）で、本番の堅さは Kimigayo 側で受け持ちます。

```dockerfile
# マルチステージビルドで必要なものを準備
FROM alpine:3.24 AS builder
RUN apk add --no-cache nginx

# 実行ファイルだけでは動かない。共有ライブラリは ldd で集める
RUN mkdir -p /stage/usr/sbin /stage/usr/lib /stage/etc/nginx \
    && cp /usr/sbin/nginx /stage/usr/sbin/ \
    && cp /etc/nginx/mime.types /stage/etc/nginx/ \
    && ldd /usr/sbin/nginx \
       | awk '/=>/ { print $3 } /^\/lib|^\/usr\/lib/ { print $1 }' \
       | grep -v 'ld-musl' | sort -u \
       | xargs -I{} cp -L {} /stage/usr/lib/

# Kimigayo OSで最小ランタイム環境を構築（版を固定する）
FROM ishinokazuki/kimigayo-os:3.0.2
COPY --from=builder /stage/ /
RUN mkdir -p /var/log/nginx /var/lib/nginx/tmp /var/lib/nginx/logs /var/www/html \
    && chown -R 65534:65534 /var/log/nginx /var/lib/nginx
COPY nginx.conf /etc/nginx/nginx.conf

USER 65534
CMD ["nginx", "-g", "daemon off;"]
```

`nginx.conf` を含む動く完全な例は
[examples/nginx](https://github.com/Kazuki-0731/Kimigayo/tree/main/examples/nginx)（Python・Node.js もあり）。

## イメージバリアント

- **kimigayo-os:latest** - Standardバリアント（x86_64 2.60MB / arm64 2.98MB）
  - 一般的なユーティリティを含む
  - 汎用コンテナベースイメージとして推奨

- **kimigayo-os:latest-minimal** - Minimalバリアント（x86_64 2.46MB / arm64 2.83MB）
  - musl libc + 最小限のBusyBox + OpenRC
  - Standard から `vi`・`wget`・`less`・`tr`・`tee` など 33 アプレットを除いたもの

- **kimigayo-os:latest-extended** - Extendedバリアント（x86_64 2.62MB / arm64 3.01MB）
  - Standard に `ar`・`ed`・`inotifyd`・`rfkill`・MTD/flash・framebuffer 系など 11 アプレットを足したもの
  - コンパイラなどの開発ツールは含まない

## タグ一覧

### バージョン指定タグ（本番ではこれを使ってください）
```
kimigayo-os:3.0.2               # Standardバリアント
kimigayo-os:3.0.2-minimal       # Minimalバリアント
kimigayo-os:3.0.2-extended      # Extendedバリアント
```

### アーキテクチャ指定タグ

**バリアント名が必要です**（`3.0.2-amd64` というタグはありません）。

```
kimigayo-os:3.0.2-standard-amd64    # x86_64
kimigayo-os:3.0.2-standard-arm64    # ARM64
```

アーキテクチャ名を含まないタグ（`3.0.2`・`3.0.2-minimal`・`latest` など）はマルチアーキの
マニフェストなので、`docker pull` が自動で合うものを選びます。
`latest-amd64`・`latest-arm64` は Standard の単一プラットフォームの別名です。

### ローリングタグ（リリースごとに更新）
```
kimigayo-os:latest              # 最新Standardバリアント
kimigayo-os:latest-minimal      # 最新Minimalバリアント
kimigayo-os:latest-extended     # 最新Extendedバリアント
kimigayo-os:latest-amd64        # 最新Standardのx86_64
kimigayo-os:latest-arm64        # 最新StandardのARM64
```

## セキュリティ

### 完全性の検証

**v3.0.2 から Cosign でキーレス署名しています。** 検証には **cosign v3 以降**が必要です（v2 では `no signatures found` になります）。

```bash
cosign verify ishinokazuki/kimigayo-os:latest \
  --certificate-identity-regexp '^https://github.com/Kazuki-0731/Kimigayo/' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com
```

**v3.0.1 以前のイメージは署名されていません。** その場合は次の2つを
使ってください。

- **ダイジェスト指定での pull**: タグではなくダイジェストで固定する

  ```bash
  docker pull ishinokazuki/kimigayo-os@sha256:<digest>
  ```

- **GitHub Release のハッシュ**: rootfs の tarball には `SHA256SUMS` と
  `SHA512SUMS` が添付されています

### 脆弱性スキャン

**出荷するイメージそのものを照合しています。** イメージ内のバイナリから
読んだ版で SBOM（CycloneDX）を作り、Grype で NVD と照合します。
CI（毎 push）とリリースの公開前に走り、公開中の `latest` も毎週照合します。
v3.0.2 は公開時点で **0 件**でした（NVD の CPE に載っている範囲で。NVD に新しい CVE が載れば変わります）。

- 上流が修正版を出していない CVE はパッチを当てて出荷し、
  `/.kimigayo-build-info` の `PATCHED_CVES` に記録しています
- **SBOM は [GitHub Release](https://github.com/Kazuki-0731/Kimigayo/releases) に添付しています。**
  手元の照合器で確かめられます
- Trivy でイメージをスキャンしても、パッケージデータベースが無いため
  中のソフトウェアを識別できません（「0 件」ではなく「認識できない」）

### 更新ポリシー

**正本は [SECURITY_POLICY.md](https://github.com/Kazuki-0731/Kimigayo/blob/main/docs/security/SECURITY_POLICY.md)。**

- **脆弱性報告の受領確認**: 24時間以内
- **初期評価**: 72時間以内
- **修正のリリース**: Critical 7日以内 / High 30日以内 / Medium 90日以内 / Low 次回リリース
- **サポート対象**: 最新のリリースだけ（古い版へのバックポートはしない）

## ライセンス

構成要素ごとに元のライセンスに従います（BusyBox: GPL-2.0 / musl libc: MIT / OpenRC: BSD-2-Clause / ビルドシステム: MIT）。詳細は[LICENSE](https://github.com/Kazuki-0731/Kimigayo/blob/main/LICENSE)ファイルを参照してください。

## サポート

- **GitHub Issues**: https://github.com/Kazuki-0731/Kimigayo/issues
- **セキュリティ問題**: [VULNERABILITY_REPORTING.md](https://github.com/Kazuki-0731/Kimigayo/blob/main/docs/security/VULNERABILITY_REPORTING.md)を参照

## 謝辞

- [Google Distroless](https://github.com/GoogleContainerTools/distroless) — 不変インフラとセキュリティ優先の設計思想
- [Alpine Linux](https://alpinelinux.org/) — 軽量性とセキュリティの実践

## プロジェクトリンク

- **ソースコード**: https://github.com/Kazuki-0731/Kimigayo
- **ドキュメント**: https://github.com/Kazuki-0731/Kimigayo/tree/main/docs
- **Docker Hub**: https://hub.docker.com/r/ishinokazuki/kimigayo-os

# Kimigayo OS

軽量・高速・セキュアなコンテナ向けOS

## 主な特徴

- 🪶 **超軽量**: Standard（x86_64）**2.78MB** / arm64 3.16MB（2026-10-10 実測）
- 🪶 **常駐メモリ 232KB**（Alpine 280KB / Ubuntu 316KB。2026-10-10 実測）
- 🔒 **セキュリティ強化**: 全実行ファイルを PIE でビルド、ASLR / DEP 対応
- 🛡️ **最小攻撃面**: パッケージマネージャーを持たない（`apk` も `dpkg` も無い）
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

```dockerfile
# マルチステージビルドで必要なものを準備
FROM alpine:3.24 AS builder
RUN apk add --no-cache nginx

# Kimigayo OSで最小ランタイム環境を構築
FROM ishinokazuki/kimigayo-os:latest
COPY --from=builder /usr/sbin/nginx /usr/sbin/nginx
COPY --from=builder /usr/lib/nginx /usr/lib/nginx

# アプリケーションのセットアップ
COPY . /app
WORKDIR /app

CMD ["/usr/sbin/nginx", "-g", "daemon off;"]
```

## イメージバリアント

- **kimigayo-os:latest** - Standardバリアント（x86_64 2.78MB / arm64 3.16MB）
  - 一般的なユーティリティを含む
  - 汎用コンテナベースイメージとして推奨

- **kimigayo-os:latest-minimal** - Minimalバリアント（x86_64 2.65MB / arm64 3.02MB）
  - musl libc + 最小限のBusyBox + OpenRC
  - 特化したコンテナ向けの絶対最小フットプリント

- **kimigayo-os:latest-extended** - Extendedバリアント（x86_64 2.81MB / arm64 3.20MB）
  - 開発ツールと追加ユーティリティを含む
  - 開発環境と機能豊富なコンテナ向け

## タグ一覧

### バージョン指定タグ（本番ではこれを使ってください）
```
kimigayo-os:3.0.0               # Standardバリアント
kimigayo-os:3.0.0-minimal       # Minimalバリアント
kimigayo-os:3.0.0-extended      # Extendedバリアント
```

### アーキテクチャ指定タグ

**バリアント名が必要です**（`3.0.0-amd64` というタグはありません）。

```
kimigayo-os:3.0.0-standard-amd64    # x86_64
kimigayo-os:3.0.0-standard-arm64    # ARM64
```

バリアント名なしのタグ（`3.0.0`・`latest` など）はマルチアーキの
マニフェストなので、`docker pull` が自動で合うものを選びます。

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

**イメージ署名（Docker Content Trust / Cosign）は未実装です。**
検証したい場合は次の2つを使ってください。

- **ダイジェスト指定での pull**: タグではなくダイジェストで固定する

  ```bash
  docker pull ishinokazuki/kimigayo-os@sha256:<digest>
  ```

- **GitHub Release のハッシュ**: rootfs の tarball には `SHA256SUMS` と
  `SHA512SUMS` が添付されています

### 脆弱性スキャン

ソースツリーとビルド環境は Trivy で自動スキャンし、結果を GitHub の
Security タブに公開しています。

**ただしイメージ自体のスキャンは成立しません。** Kimigayo は
パッケージマネージャーを持たずパッケージデータベースも無いため、
Trivy はイメージ内のソフトウェアを1つも識別できません
（「脆弱性 0 件」ではなく「スキャン対象を認識できない」状態です）。
構成要素（musl / BusyBox / OpenRC / カーネル）の脆弱性は、
バージョンを手で追跡しています。

### 更新ポリシー

**正本は [SECURITY_POLICY.md](https://github.com/Kazuki-0731/Kimigayo/blob/main/docs/security/SECURITY_POLICY.md)。**

- **脆弱性報告の受領確認**: 24時間以内
- **初期評価**: 72時間以内
- **修正のリリース**: Critical 7日以内 / High 30日以内 / Medium 90日以内
- **バグ修正**: 定期的なパッチリリースに含める
- **機能更新**: SemVer のマイナー版で出す

## ライセンス

GPL-2.0 - 詳細は[LICENSE](https://github.com/Kazuki-0731/Kimigayo/blob/main/LICENSE)ファイルを参照してください。

## サポート

- **GitHub Issues**: https://github.com/Kazuki-0731/Kimigayo/issues
- **セキュリティ問題**: [VULNERABILITY_REPORTING.md](https://github.com/Kazuki-0731/Kimigayo/blob/main/docs/security/VULNERABILITY_REPORTING.md)を参照

## プロジェクトリンク

- **ソースコード**: https://github.com/Kazuki-0731/Kimigayo
- **ドキュメント**: https://github.com/Kazuki-0731/Kimigayo/tree/main/docs
- **Docker Hub**: https://hub.docker.com/r/ishinokazuki/kimigayo-os

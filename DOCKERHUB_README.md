# Kimigayo OS

軽量・高速・セキュアなコンテナ向けOS

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
FROM ishinokazuki/kimigayo-os:latest

# isnを使用してパッケージをインストール
RUN isn install nginx

# アプリケーションのセットアップ
COPY . /app
WORKDIR /app

CMD ["/usr/sbin/nginx", "-g", "daemon off;"]
```

## イメージバリアント

- **kimigayo-os:latest** - Standardバリアント（< 15MB）
  - 一般的なユーティリティとisnパッケージマネージャを含む
  - 汎用コンテナベースイメージとして推奨

- **kimigayo-os:latest-minimal** - Minimalバリアント（< 5MB）
  - カーネル + musl libc + 最小限のBusyBox
  - 特化したコンテナ向けの絶対最小フットプリント

- **kimigayo-os:latest-extended** - Extendedバリアント（< 50MB）
  - 開発ツールと追加ユーティリティを含む
  - 開発環境と機能豊富なコンテナ向け

## タグ一覧

### バージョン指定タグ
```
kimigayo-os:0.1.0               # Standardバリアント、バージョン0.1.0
kimigayo-os:0.1.0-minimal       # Minimalバリアント、バージョン0.1.0
kimigayo-os:0.1.0-extended      # Extendedバリアント、バージョン0.1.0
```

### アーキテクチャ指定タグ
```
kimigayo-os:0.1.0-amd64         # x86_64アーキテクチャ
kimigayo-os:0.1.0-arm64         # ARM64アーキテクチャ
```

### ローリングタグ（自動更新）
```
kimigayo-os:latest              # 最新安定版Standardバリアント
kimigayo-os:latest-minimal      # 最新安定版Minimalバリアント
kimigayo-os:latest-extended     # 最新安定版Extendedバリアント
kimigayo-os:stable              # 最新安定版リリース（latestのエイリアス）
kimigayo-os:edge                # 最新開発ビルド（不安定版）
```

## 主な特徴

- 🪶 **超軽量**: ベースイメージ5MB未満
- ⚡ **高速起動**: 10秒以内のシステム起動
- 🔒 **セキュリティ強化**: ASLR、DEP、PIE、seccomp-BPFをデフォルトで有効化
- 📦 **パッケージマネージャ**: Ed25519署名検証を備えた`isn`パッケージマネージャを内蔵
- 🏗️ **モジュラー設計**: 必要なコンポーネントのみを選択可能
- 🔁 **再現可能ビルド**: 検証のためのビット同一なビルド出力
- 🌐 **マルチアーキテクチャ**: x86_64とARM64をサポート

## 基盤技術

- Linuxカーネル（強化版）
- musl libc
- BusyBox
- OpenRC initシステム

## ドキュメント

- [インストールガイド](https://github.com/Kazuki-0731/Kimigayo/blob/main/docs/user/INSTALLATION.md)
- [クイックスタートガイド](https://github.com/Kazuki-0731/Kimigayo/blob/main/docs/user/QUICKSTART.md)
- [パッケージマネージャガイド](https://github.com/Kazuki-0731/Kimigayo/blob/main/docs/user/PACKAGE_MANAGER.md)
- [セキュリティガイド](https://github.com/Kazuki-0731/Kimigayo/blob/main/docs/security/SECURITY_GUIDE.md)

## セキュリティ

### イメージ署名

すべての公式イメージは以下を使用して署名されます:
- Docker Content Trust（DCT）
- 追加検証用のCosign

### 脆弱性スキャン

イメージは以下で自動スキャンされます:
- Trivy
- 結果はGitHub Securityタブに公開

### 更新ポリシー

- **セキュリティパッチ**: 開示後24〜48時間以内にリリース
- **バグ修正**: 定期的なパッチリリースに含める
- **機能更新**: SemVerマイナーバージョン増分に従う

## ライセンス

GPL-2.0 - 詳細は[LICENSE](https://github.com/Kazuki-0731/Kimigayo/blob/main/LICENSE)ファイルを参照してください。

## サポート

- **GitHub Issues**: https://github.com/Kazuki-0731/Kimigayo/issues
- **セキュリティ問題**: [VULNERABILITY_REPORTING.md](https://github.com/Kazuki-0731/Kimigayo/blob/main/docs/security/VULNERABILITY_REPORTING.md)を参照

## プロジェクトリンク

- **ソースコード**: https://github.com/Kazuki-0731/Kimigayo
- **ドキュメント**: https://github.com/Kazuki-0731/Kimigayo/tree/main/docs
- **Docker Hub**: https://hub.docker.com/r/ishinokazuki/kimigayo-os

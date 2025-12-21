# Docker Hub リポジトリ設定

## リポジトリ情報

### アカウント詳細
- **組織名/ユーザー名**: kimigayo-os（作成予定）
- **リポジトリ名**: kimigayo-os
- **公開範囲**: Public
- **説明**: Alpine Linuxにインスパイアされた軽量・高速・セキュアなコンテナ向けOS

### リポジトリ説明文

Kimigayo OSは、Docker環境向けに設計された軽量・高速・セキュアなコンテナ向けOSです。セキュリティファーストの原則と最小限のフットプリントで構築され、コンテナ化されたアプリケーションとマイクロサービスの優れた基盤を提供します。

**主な特徴:**
- 🪶 **超軽量**: ベースイメージ5MB未満
- ⚡ **高速起動**: 10秒以内のシステム起動
- 🔒 **セキュリティ強化**: ASLR、DEP、PIE、seccomp-BPFをデフォルトで有効化
- 📦 **パッケージマネージャ**: Ed25519署名検証を備えた`isn`パッケージマネージャを内蔵
- 🏗️ **モジュラー設計**: 必要なコンポーネントのみを選択可能
- 🔁 **再現可能ビルド**: 検証のためのビット同一なビルド出力
- 🌐 **マルチアーキテクチャ**: x86_64とARM64をサポート

**基盤技術:**
- Linuxカーネル（強化版）
- musl libc
- BusyBox
- OpenRC initシステム

## タグ戦略

### バージョンタグ

すべてのリリースで**セマンティックバージョニング（SemVer）**に従います:

#### フォーマット
- `MAJOR.MINOR.PATCH`（例: `1.0.0`）
  - **MAJOR**: 互換性のないAPI変更
  - **MINOR**: 後方互換性のある新機能
  - **PATCH**: 後方互換性のあるバグ修正

#### イメージバリアント

各バージョンは、イメージサイズと含まれる機能に基づいて3つのバリアントで提供されます:

1. **Minimal**（`-minimal`接尾辞）
   - サイズ: < 5MB
   - 含まれるもの: カーネル + musl libc + 最小限のBusyBox
   - 用途: 特化したコンテナ向けの絶対最小フットプリント

2. **Standard**（接尾辞なし、デフォルト）
   - サイズ: < 15MB
   - 含まれるもの: Minimal + 一般的なユーティリティ + isnパッケージマネージャ
   - 用途: 汎用コンテナベースイメージ

3. **Extended**（`-extended`接尾辞）
   - サイズ: < 50MB
   - 含まれるもの: Standard + 開発ツール + 追加ユーティリティ
   - 用途: 開発環境と機能豊富なコンテナ

#### タグの例

```
# バージョン指定タグ
kimigayo-os:0.1.0               # Standardバリアント、バージョン0.1.0
kimigayo-os:0.1.0-minimal       # Minimalバリアント、バージョン0.1.0
kimigayo-os:0.1.0-extended      # Extendedバリアント、バージョン0.1.0

# アーキテクチャ指定タグ
kimigayo-os:0.1.0-amd64         # x86_64アーキテクチャ
kimigayo-os:0.1.0-arm64         # ARM64アーキテクチャ

# バリアントとアーキテクチャの組み合わせ
kimigayo-os:0.1.0-minimal-amd64
kimigayo-os:0.1.0-extended-arm64

# ローリングタグ（自動更新）
kimigayo-os:latest              # 最新安定版Standardバリアント
kimigayo-os:latest-minimal      # 最新安定版Minimalバリアント
kimigayo-os:latest-extended     # 最新安定版Extendedバリアント
kimigayo-os:stable              # 最新安定版リリース（latestのエイリアス）
kimigayo-os:edge                # 最新開発ビルド（不安定版）
```

### タグ付けワークフロー

1. **開発ビルド**（`edge`タグ）
   - `main`ブランチへのコミット毎にプッシュ
   - 本番環境での使用は非推奨
   - フォーマット: `edge`、`edge-minimal`、`edge-extended`

2. **ベータ/RCリリース**
   - テスト用のプレリリースバージョン
   - フォーマット: `0.1.0-beta.1`、`1.0.0-rc.2`

3. **安定版リリース**
   - 本番環境対応バージョン
   - フォーマット: `0.1.0`、`1.0.0`
   - `latest`および`stable`としてもタグ付け

4. **パッチアップデート**
   - バグ修正とセキュリティパッチ
   - フォーマット: `1.0.1`、`1.0.2`
   - `latest`タグを自動更新

## リポジトリセットアップ手順

### ステップ1: Docker Hubアカウント作成

1. https://hub.docker.com/signup にアクセス
2. ユーザー名`kimigayo-os`でアカウント登録
3. メールアドレスを検証
4. プロフィール設定を完了

### ステップ2: リポジトリ作成

1. Docker Hubにログイン
2. "Create Repository"をクリック
3. リポジトリ詳細を入力:
   - **名前**: `kimigayo-os`
   - **説明**: （上記の説明を使用）
   - **公開範囲**: Public
4. "Create"をクリック

### ステップ3: リポジトリ設定

以下の設定を行います:

#### Overviewタブ
- 上記の完全な説明を追加
- 以下のリンクを追加:
  - GitHubリポジトリ: `https://github.com/kimigayo-os/kimigayo`
  - ドキュメント: `https://docs.kimigayo-os.org`（作成予定）
  - Issues: `https://github.com/kimigayo-os/kimigayo/issues`

#### Buildsタブ（将来のCI/CD統合用）
- GitHub Actionsで設定予定
- タグプッシュ時の自動ビルド
- buildxを使用したマルチアーキテクチャビルド

#### Collaboratorsタブ
- 必要に応じてチームメンバーを追加
- 適切な権限レベルを設定

### ステップ4: Docker Hub README

Docker Hub READMEには以下を含めます:

```markdown
# Kimigayo OS

軽量・高速・セキュアなコンテナ向けOS

## クイックスタート

### イメージの取得

```bash
# Standardバリアント（推奨）
docker pull kimigayo-os:latest

# Minimalバリアント
docker pull kimigayo-os:latest-minimal

# Extendedバリアント
docker pull kimigayo-os:latest-extended
```

### コンテナの実行

```bash
# 対話的シェル
docker run -it kimigayo-os:latest /bin/sh

# コマンド実行
docker run kimigayo-os:latest uname -a
```

### ベースイメージとして使用

```dockerfile
FROM kimigayo-os:latest

# isnを使用してパッケージをインストール
RUN isn install nginx

# アプリケーションのセットアップ
COPY . /app
WORKDIR /app

CMD ["/usr/sbin/nginx", "-g", "daemon off;"]
```

## イメージバリアント

- **kimigayo-os:latest** - Standardバリアント（< 15MB）
- **kimigayo-os:latest-minimal** - Minimalバリアント（< 5MB）
- **kimigayo-os:latest-extended** - Extendedバリアント（< 50MB）

## ドキュメント

- [インストールガイド](https://github.com/kimigayo-os/kimigayo/blob/main/docs/user/INSTALLATION.md)
- [クイックスタートガイド](https://github.com/kimigayo-os/kimigayo/blob/main/docs/user/QUICKSTART.md)
- [パッケージマネージャガイド](https://github.com/kimigayo-os/kimigayo/blob/main/docs/user/PACKAGE_MANAGER.md)
- [セキュリティガイド](https://github.com/kimigayo-os/kimigayo/blob/main/docs/security/SECURITY_GUIDE.md)

## 機能

- ✅ 超軽量（< 5MBベースイメージ）
- ✅ 高速起動（< 10秒）
- ✅ デフォルトでセキュリティ強化
- ✅ 再現可能ビルド
- ✅ マルチアーキテクチャサポート（x86_64、ARM64）
- ✅ 内蔵パッケージマネージャ（isn）
- ✅ 実績ある技術に基づく（musl libc、BusyBox、OpenRC）

## ライセンス

[LICENSE](https://github.com/kimigayo-os/kimigayo/blob/main/LICENSE)ファイルを参照してください。

## サポート

- GitHub Issues: https://github.com/kimigayo-os/kimigayo/issues
- セキュリティ問題: [SECURITY.md](https://github.com/kimigayo-os/kimigayo/blob/main/docs/security/VULNERABILITY_REPORTING.md)を参照
```

## セキュリティに関する考慮事項

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

## メタデータラベル

すべてのイメージにOpenContainer Initiative（OCI）ラベルを含めます:

```dockerfile
LABEL org.opencontainers.image.title="Kimigayo OS"
LABEL org.opencontainers.image.description="軽量・高速・セキュアなコンテナ向けOS"
LABEL org.opencontainers.image.authors="Kimigayo OS Team"
LABEL org.opencontainers.image.url="https://github.com/kimigayo-os/kimigayo"
LABEL org.opencontainers.image.documentation="https://github.com/kimigayo-os/kimigayo/tree/main/docs"
LABEL org.opencontainers.image.source="https://github.com/kimigayo-os/kimigayo"
LABEL org.opencontainers.image.version="${VERSION}"
LABEL org.opencontainers.image.revision="${GIT_COMMIT}"
LABEL org.opencontainers.image.created="${BUILD_DATE}"
LABEL org.opencontainers.image.licenses="GPL-2.0"
```

## 次のステップ

リポジトリセットアップ後:
1. 自動ビルド用のGitHub Actions設定（タスク26）
2. セキュリティスキャンの実装（タスク27）
3. マルチアーキテクチャビルドの設定（タスク28）
4. 最初のリリース準備（タスク29）

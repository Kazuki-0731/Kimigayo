# Kimigayo OS

**Google の distroless と Alpine Linux のハイブリッドアプローチ**

軽量・高速・セキュアなコンテナ向けOS

## 設計思想

Kimigayo OSは、**distroless** と **Alpine Linux** の両方の長所を組み合わせています：

### distroless からの継承
- ✅ **不変インフラ**: パッケージマネージャーなし、実行時の変更を排除
- ✅ **最小攻撃面**: 実行時のパッケージインストール機能を物理的に排除
- ✅ **超軽量**: 1-3MBの極小イメージサイズ

### Alpine Linux からの継承
- ✅ **musl libc**: 軽量で高速なCライブラリ（glibcの1/10）
- ✅ **BusyBox**: デバッグ可能なシェルとUnixコマンド
- ✅ **OpenRC**: シンプルで軽量なInitシステム
- ✅ **セキュリティ強化**: PIE、ASLR、Stack Protector等

## 主な特徴

- 🪶 **超軽量**: ベースイメージ1-3MB
- ⚡ **高速起動**: 10秒以内のシステム起動
- 🔒 **セキュリティ強化**: ASLR、DEP、PIE、seccomp-BPFをデフォルトで有効化
- 🛡️ **最小攻撃面**: パッケージマネージャーを意図的に排除
- 🏗️ **モジュラー設計**: 必要なコンポーネントのみを選択可能
- 🔁 **再現可能ビルド**: ビット同一なビルド出力
- 🌐 **マルチアーキテクチャ**: x86_64とARM64をサポート（GCC 15対応済み）

## 基盤技術

- Linuxカーネル 6.6.11（強化版、GCC 15対応パッチ適用）
- musl libc 1.2.4
- BusyBox 1.36.1
- OpenRC initシステム

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

### ベースイメージとして使用（推奨パターン）

**不変インフラの実践**: ビルド時に全てを準備、実行時は変更なし

```dockerfile
# マルチステージビルドで必要なものを準備
FROM alpine:3.19 AS builder
RUN apk add --no-cache python3 py3-pip
COPY requirements.txt .
RUN pip install -r requirements.txt

# Kimigayo OSで最小ランタイム環境を構築
FROM ishinokazuki/kimigayo-os:latest
COPY --from=builder /usr/lib/python3.11 /usr/lib/python3.11
COPY app.py .

# パッケージマネージャーがないので実行時の変更は不可能
# → セキュリティ向上、完全な再現性

CMD ["python3", "app.py"]
```

このアプローチにより：
- 開発環境の柔軟性（Alpine + apk）
- 本番環境のセキュリティ（Kimigayo + パッケージマネージャーなし）

を両立できます。

## イメージバリアント

- **kimigayo-os:latest** - Standardバリアント（< 15MB）
  - 一般的なユーティリティを含む
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

## Alpine/distroless との違い

| 特徴 | distroless | Alpine | **Kimigayo OS** |
|------|-----------|--------|----------------|
| パッケージマネージャー | ❌ | ✅ apk | ❌ **なし** |
| シェル/ユーティリティ | ❌ | ✅ | ✅ **BusyBox** |
| 不変インフラ | ✅ | ⚠️ 任意 | ✅ **強制** |
| デバッグ容易性 | ❌ | ✅ | ✅ **容易** |
| セキュリティ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ **最高** |

**Kimigayo OS = distrolessのセキュリティ + Alpineの実用性**

## プロジェクトリンク

- **GitHub**: https://github.com/Kazuki-0731/Kimigayo
- **Wiki**: https://github.com/Kazuki-0731/Kimigayo/wiki
- **ドキュメント**: https://github.com/Kazuki-0731/Kimigayo/tree/main/docs
- **Docker Hub**: https://hub.docker.com/r/ishinokazuki/kimigayo-os

## 謝辞

- [Google Distroless](https://github.com/GoogleContainerTools/distroless) - 不変インフラとセキュリティ優先の設計思想
- [Alpine Linux](https://alpinelinux.org/) - 軽量性とセキュリティのベストプラクティス

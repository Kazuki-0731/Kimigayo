# Kimigayo OS セキュリティアドバイザリ

> アドバイザリは [GitHub Security Advisories](https://github.com/Kazuki-0731/Kimigayo/security/advisories)
> で公開します。この雛形はその本文の下書き用です。

**アドバイザリID**: GHSA-xxxx-xxxx-xxxx（GitHub が採番）
**CVE**: CVE-YYYY-NNNNN（取得した場合）
**公開日**: YYYY年MM月DD日
**最終更新日**: YYYY年MM月DD日

---

## 概要

Kimigayo OS [影響を受けるバージョン]において、[脆弱性の簡潔な説明]が発見されました。この脆弱性により、[影響の概要]が可能となります。

---

## 影響を受けるバージョン

### 影響あり

- Kimigayo OS v[バージョン]（イメージのタグ: `[バージョン]-[variant]`。variant: minimal, standard, extended）
- [その他の影響を受けるバージョン]

### 影響なし

- Kimigayo OS v[バージョン以降]
- [その他の影響を受けないバージョン]

---

## 脆弱性の詳細

### CWE分類

**CWE**: CWE-NNN ([脆弱性タイプ名])

### CVSS v3.1スコア

**ベーススコア**: X.X ([重大度レベル])
**ベクトル文字列**: `CVSS:3.1/AV:[値]/AC:[値]/PR:[値]/UI:[値]/S:[値]/C:[値]/I:[値]/A:[値]`

**スコア内訳**:
- 攻撃元区分 (Attack Vector): [ネットワーク/隣接/ローカル/物理]
- 攻撃条件の複雑さ (Attack Complexity): [低/高]
- 必要な特権レベル (Privileges Required): [不要/低/高]
- ユーザー関与 (User Interaction): [不要/要]
- スコープ (Scope): [変更なし/変更あり]
- 機密性への影響 (Confidentiality): [なし/低/高]
- 完全性への影響 (Integrity): [なし/低/高]
- 可用性への影響 (Availability): [なし/低/高]

### 脆弱性の説明

[脆弱性の技術的な詳細説明]

#### 技術的背景

[なぜこの脆弱性が存在するのか、その技術的背景]

#### 攻撃シナリオ

攻撃者は以下の手順で脆弱性を悪用する可能性があります：

1. [攻撃ステップ1]
2. [攻撃ステップ2]
3. [攻撃ステップ3]

#### 影響

この脆弱性が悪用された場合、以下の影響が発生する可能性があります：

- **機密性**: [影響の詳細]
- **完全性**: [影響の詳細]
- **可用性**: [影響の詳細]

---

## 修正情報

### 修正バージョン

この脆弱性は以下のバージョンで修正されています：

- **Kimigayo OS v[バージョン]** (リリース日: YYYY-MM-DD)
- Docker Hub: `ishinokazuki/kimigayo-os:[タグ]`

### 修正内容

[修正の詳細説明]

### 修正コミット

- GitHub コミット: `https://github.com/Kazuki-0731/Kimigayo/commit/[ハッシュ]`

---

## 回避策・緩和策

修正版へのアップデートが即座に実施できない場合、以下の回避策を検討してください：

### 暫定回避策

1. **[回避策1のタイトル]**
   ```bash
   # 実施コマンド例
   ```
   ⚠️ 注意: [回避策の注意事項]

2. **[回避策2のタイトル]**
   ```bash
   # 実施コマンド例
   ```
   ⚠️ 注意: [回避策の注意事項]

### 緩和策

以下の設定により、脆弱性の影響を軽減できます：

- [緩和策1]
- [緩和策2]

---

## 推奨される対応

### 即座に実施すべき対応（Critical/High の場合）

1. ✅ **影響評価**: 使用中の環境が影響を受けるか確認
2. ✅ **修正版へのアップデート**: 可能な限り早急に実施
3. ✅ **ログ確認**: 悪用の兆候がないか確認
4. ✅ **監視強化**: 関連するイベントの監視を強化

### 優先度別対応スケジュール

| 重大度 | 推奨対応期限 | アクション |
|--------|------------|-----------|
| Critical | 24時間以内 | 即座にアップデート |
| High | 1週間以内 | 優先的にアップデート |
| Medium | 1ヶ月以内 | 計画的にアップデート |
| Low | 次回定期メンテナンス時 | 通常のアップデートサイクルで対応 |

---

## アップデート手順

### Dockerイメージのアップデート

```bash
# 最新イメージの取得
docker pull ishinokazuki/kimigayo-os:[修正版タグ]

# コンテナの再作成
docker stop [container-name]
docker rm [container-name]
docker run -d \
  --name [container-name] \
  ishinokazuki/kimigayo-os:[修正版タグ]

# アップデート確認
docker exec [container-name] cat /etc/os-release
```

### ソースからのビルド

```bash
git fetch --tags origin
git checkout v[修正版バージョン]
```

ビルドの手順は [BUILD_GUIDE.md](../developer/BUILD_GUIDE.md) を参照してください
（`make build` は構成要素をビルドするだけで、Docker イメージは作りません）。

---

## 検証方法

修正が適用されたことを確認するには：

```bash
# バージョン確認
docker exec [container-name] cat /etc/os-release | grep VERSION

# 署名の確認（cosign v3 以上。v2 では no signatures found になる）
cosign verify ishinokazuki/kimigayo-os:[修正版タグ] \
  --certificate-identity-regexp '^https://github.com/Kazuki-0731/Kimigayo/' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com

# 既知の CVE の照合（リポジトリで実行。kimigayo-os:<variant>-<arch> を対象にする）
make scan-image VARIANT=standard ARCH=x86_64
```

期待される出力：
```
# cosign verify が成功し、scan-image が該当の CVE を検出しない
# （パッチで塞いだ CVE は /.kimigayo-build-info の PATCHED_CVES に記録され、照合から除外される）
```

`trivy image` は使いません（パッケージ DB の無い Kimigayo を識別できず、何も検査しない）。
公開イメージの SBOM（CycloneDX）は GitHub Release に添付しています。

---

## タイムライン

| 日付 | イベント |
|------|---------|
| YYYY-MM-DD | 脆弱性を発見（報告を受領） |
| YYYY-MM-DD | 内部での影響評価完了 |
| YYYY-MM-DD | 修正実装開始 |
| YYYY-MM-DD | 修正完了・内部テスト |
| YYYY-MM-DD | 修正版リリース |
| YYYY-MM-DD | セキュリティアドバイザリ公開 |
| YYYY-MM-DD | CVE登録（該当する場合） |

---

## クレジット

この脆弱性を報告していただいた以下の方々に感謝いたします：

- [報告者名/組織名]（発見者）
- [協力者名]（検証協力）

Kimigayo OSプロジェクトは、責任ある脆弱性開示プロセスに従って報告していただいたセキュリティ研究者の皆様に感謝いたします。

---

## 参考情報

### 関連リンク

- **CVE詳細**: https://www.cve.org/CVERecord?id=CVE-YYYY-NNNNN
- **修正コミット**: https://github.com/Kazuki-0731/Kimigayo/commit/[ハッシュ]
- **CHANGELOG**: [CHANGELOG.md](../../CHANGELOG.md) の該当版の Security 節
- **Kimigayo OSセキュリティポリシー**: [SECURITY_POLICY.md](./SECURITY_POLICY.md)

### 技術資料

- [関連する技術ドキュメント1]
- [関連する技術ドキュメント2]

---

## お問い合わせ

### セキュリティに関する問い合わせ

セキュリティに関する質問や懸念がある場合は、以下にご連絡ください：

- **GitHub Security Advisories**: https://github.com/Kazuki-0731/Kimigayo/security/advisories
  （窓口はここだけです。メールの窓口はありません）
- **質問・相談**: https://github.com/Kazuki-0731/Kimigayo/discussions

### 脆弱性報告

新たな脆弱性を発見した場合は、[脆弱性報告手順](./VULNERABILITY_REPORTING.md)に従って報告してください。

---

## 免責事項

本アドバイザリは、現時点で入手可能な情報に基づいています。Kimigayo OSプロジェクトは、本アドバイザリの情報の正確性および完全性について、いかなる保証も行いません。

本アドバイザリに記載された緩和策や回避策は、あくまで一時的な対応であり、修正版へのアップデートが推奨されます。

---

## 改訂履歴

| バージョン | 日付 | 変更内容 |
|----------|------|---------|
| 1.0 | YYYY-MM-DD | 初版公開 |
| 1.1 | YYYY-MM-DD | [変更内容] |

---

**公開ステータス**: [Draft / Published]
**機密性**: Public

ライセンスはリポジトリの [LICENSE](../../LICENSE) に従います。

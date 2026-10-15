# Kimigayo OS セキュリティ監査ガイドライン

このドキュメントでは、Kimigayo OSのセキュリティ監査プロセスとガイドラインを定義します。

## 目次

1. [監査の目的](#監査の目的)
2. [監査の種類](#監査の種類)
3. [監査スコープ](#監査スコープ)
4. [監査手順](#監査手順)
5. [自動化された監査](#自動化された監査)
6. [外部監査](#外部監査)
7. [監査結果の報告](#監査結果の報告)

## 監査の目的

Kimigayo OSのセキュリティ監査は以下の目的で実施されます：

- **脆弱性の早期発見**: システムの脆弱性を本番環境展開前に発見
- **コンプライアンス確保**: セキュリティ基準とベストプラクティスへの準拠
- **継続的改善**: セキュリティ姿勢の継続的な向上
- **透明性**: 何を検査していて何を検査していないかを、利用者が確かめられるようにする

## 監査の種類

### 1. 自動化監査（継続的）

#### a. 脆弱性スキャン
- **出荷物（イメージ）**: `scripts/scan-image.sh`（`make scan-image`）
  - イメージ内のバイナリを実行して読んだ BusyBox / musl / OpenRC の版から
    CycloneDX の SBOM を作り、Grype で NVD の CPE と照合する
  - 公開イメージ（Docker Hub の `latest`）に対して毎週月曜 04:00 UTC
    （`dependency-review.yml` の `published-image-scan`）
  - 加えて CI（毎 push）とリリース（Docker Hub への push 前）でも照合する
    （下記「自動化された監査」）
- **リポジトリ**: Trivy のファイルシステムスキャン（push / PR・毎日・毎週）
- **重大度**: 出荷物は `FAIL_ON`（既定 `low`、Grype の `--fail-on`）で、
  見つかればジョブが落ちる。リポジトリは CI と `security.yml` が CRITICAL, HIGH、
  `dependency-review.yml` の週次とローカルの `make trivy-fs-scan` は MEDIUM も含む。
  **リポジトリの Trivy は SARIF を Security タブに送るだけで、結果ではジョブは落ちない**

#### b. 静的解析
- **ツール**: ShellCheck
- **頻度**: コミット/プッシュ時
- **スコープ**: `scripts/`（`scripts/lib/` を含む）と `.claude/hooks/` のシェルスクリプト

#### c. 構成監査
- **ツール**: Trivy（`scanners: config`）
- **頻度**: 毎日（`security.yml`）と週次（`dependency-review.yml`）
- **スコープ**: Dockerfile などリポジトリ内の設定ファイル（GitHub Actions の
  ワークフローを Trivy が検査対象にしているかは確かめていない）

### 2. 手動監査（指針）

> **以下は目安で、定期実施を約束するものではありません。** 開発は
> メンテナー 1 人で、約束の正本は [SECURITY_POLICY.md](SECURITY_POLICY.md) です。
> 実施した記録はまだありません。

#### a. コードレビュー
- **頻度（目安）**: 四半期ごと
- **スコープ**:
  - セキュリティクリティカルなコンポーネント
  - 認証・認可機能
  - 暗号化実装
  - ネットワーク設定

#### b. アーキテクチャレビュー
- **頻度（目安）**: メジャーリリース前
- **スコープ**:
  - セキュリティアーキテクチャ設計
  - 信頼境界の定義
  - データフロー分析

### 3. 外部監査（予定なし）

**外部監査とペネトレーションテストは、これまで実施していません**
（v3.0.0 のメジャーリリースも外部監査なしで出しています）。
定期実施の予定もありません。第三者による監査は歓迎します
（[SECURITY_POLICY.md](SECURITY_POLICY.md#外部監査)）。

- 外部セキュリティ監査: 第三者が行う場合のスコープはシステム全体
- ペネトレーションテスト: 手順は [PENETRATION_TEST.md](./PENETRATION_TEST.md)

## 監査スコープ

### コンポーネント別監査項目

#### 1. Linuxカーネル（対象外）
カーネルはイメージに入らず、コンテナはホストのカーネルで動きます。
ASLR・NX・KASLR・カーネルの CVE はホスト側の監査項目です。

#### 2. musl libc
- [ ] メモリ安全性機能の確認
- [ ] 既知の脆弱性（CVE）の確認
- [ ] ヒープ/スタック保護機能
- [ ] 整数オーバーフロー保護

#### 3. BusyBox
- [ ] 有効化コマンドのセキュリティリスク評価
- [ ] SetUID/SetGIDバイナリの監査
- [ ] 既知の脆弱性（CVE）の確認
- [ ] アプレット権限設定の検証

#### 4. OpenRC (initシステム)
- [ ] サービス起動権限の検証
- [ ] init スクリプトの安全性確認
- [ ] サービス間依存関係の検証
- [ ] ログ記録機能の確認

#### 5. ビルドシステム
- [ ] 再現可能ビルドの検証
      — `build-system/Makefile` が `REPRODUCIBLE_BUILD ?= yes` と
      `SOURCE_DATE_EPOCH` を設定している。**rootfs の tarball は
      2026-10-12 にビット同一を確認**（同じコミット 46b05da を CI と
      Manual Build で別々にビルドした standard / x86_64 の 1 組）。
      **Docker イメージの digest は未確認**
- [ ] ビルド環境の隔離確認
- [ ] 依存関係の完全性検証
      — 版は [versions.mk](../../versions.mk) に単一化し、
      チェックサムを上流（および Alpine aports）と突合している
- [ ] サプライチェーン攻撃対策
      — 外部 Action はコミット SHA で固定済み

#### 6. Dockerイメージ
- [ ] レイヤー構成の最適性
- [ ] 不要なファイルの除外確認
- [ ] 出荷物の脆弱性スキャン（ベースは `scratch` なので、構成要素の CVE を
      `scripts/scan-image.sh` で照合する）
- [ ] イメージ署名の検証
      — v3.0.2 から Cosign のキーレス署名（Sigstore OIDC）を
      `release.yml` の `sign` ジョブで行う。**v3.0.1 以前は未署名**。
      検証には cosign v3 以上が要る（手順は
      [SECURITY_POLICY.md](SECURITY_POLICY.md#イメージの署名)）

## 監査手順

### Phase 1: 準備（1-2日）

1. **監査計画の策定**
   - 監査スコープの確定
   - 監査チームの編成
   - スケジュール作成

2. **環境準備**
   - 監査用環境の構築
   - ツールのセットアップ
   - アクセス権限の設定

### Phase 2: 自動スキャン（1日）

1. **脆弱性スキャン実行**
   ```bash
   # 出荷物の CVE 照合（SBOM + Grype）と秘密情報スキャン
   make scan-image VARIANT=standard ARCH=x86_64

   # ファイルシステムスキャン
   make trivy-fs-scan

   # ShellCheck実行
   make shellcheck-scan
   ```

2. **結果の収集**
   - GitHub Security Tabの確認（Trivy fs の SARIF。`scan-image` の結果は
     SARIF にならないのでジョブのログで見る）
   - 優先度の判定

### Phase 3: 手動監査（3-5日）

1. **設定監査**
   - `scripts/build-rootfs.sh` が生成する設定（`/etc/passwd`・`/etc/shadow`・
     `/etc/sysctl.d/`・init スクリプト）のレビュー
   - `src/busybox/config/` の有効なアプレットのレビュー

2. **コード監査**
   - セキュリティクリティカルコードのレビュー
   - 権限管理コードの確認
   - 入力検証の実装確認

3. **ドキュメント監査**
   - セキュリティドキュメントの完全性確認
   - 運用手順書の妥当性検証
   - インシデント対応手順の確認

### Phase 4: ペネトレーションテスト（2-3日）

詳細は [PENETRATION_TEST.md](./PENETRATION_TEST.md) を参照。

### Phase 5: 報告（1-2日）

1. **監査レポート作成**
   - 発見事項の一覧化
   - リスク評価とCVSS採点
   - 修正推奨事項

2. **結果の報告**
   - ステークホルダーへの報告
   - GitHub Issueの作成
   - セキュリティアドバイザリの発行（必要に応じて）

## 自動化された監査

### GitHub Actionsによる継続的監査

#### 1. PR / push 時（`build-and-verify.yml`）

**外部 Action はコミット SHA で固定します**（`@master` は供給網の
リスクかつ再現性がない）。

ShellCheck は Action を使わず、ダイジェストで固定した `koalaman/shellcheck` の
イメージを直接動かします（`release.yml` も同じ。2026-10-13 まで使っていた
`ludeeus/action-shellcheck` は `.claude/hooks` を実際には検査していなかった）。

```yaml
- name: Run ShellCheck
  run: |
    docker run --rm -v "${PWD}:/mnt" -w /mnt \
      koalaman/shellcheck:v0.11.0@sha256:61862eba... \
      --severity=warning \
      scripts/*.sh scripts/lib/*.sh .claude/hooks/*.sh

- name: Run Trivy (filesystem)
  uses: aquasecurity/trivy-action@ed142fd0673e97e23eac54620cfb913e5ce36c25 # v0.36.0
  with:
    scan-type: 'fs'
    severity: 'CRITICAL,HIGH'
```

#### 2. リリース時（`release.yml`）

ShellCheck と `scripts/verify-image.sh`（34 項目、minimal は 33）、push 前に
`scripts/scan-image.sh`（CVE 照合 + 秘密情報）。作った SBOM（CycloneDX）は
GitHub Release に添付します。
**Trivy のイメージスキャンは 2026-10-09 に外しました**（下記の理由）。

`verify-image.sh` のうちセキュリティに関わる検査:

- イメージ内の**全 ELF**の PIE / RELRO / BIND_NOW / 非実行スタック / スタック保護
  （`scripts/check-elf-hardening.py` が `docker export` の tar を読む）
- イメージ内のバイナリを実行して読んだ BusyBox / musl / OpenRC の版と
  `versions.mk` の突合（`scripts/lib/image-components.sh`）
- cpio のパストラバーサルの回帰テスト（v3.0.1 の公開イメージは
  `ESCAPED` で落ちる。現在の `main` は `CONTAINED`）
- ash の関数の無限再帰がエラーで止まるか（CVE-2026-38755 の回帰。
  v3.0.1 は Segmentation fault で落ちる）
- setuid/setgid・`/etc/shadow` の権限・パッケージマネージャーの不在 など

#### 2b. ビルドごと（`build-workflow.yml`）

`build-and-verify.yml`・`manual-build.yml` が呼ぶビルド本体で、`verify-image.sh` の
あとに `scripts/scan-image.sh` を実行します
（CVE 照合と rootfs の秘密情報。見つかればジョブが落ちる）。
NVD に新しい CVE が載ると、コードを変えていない push でも落ちます。

#### 3. 定期監査（`security.yml`）
- **頻度**: **毎日 02:00 UTC**
- **スコープ**: 構成要素の版確認 + **ファイルシステム**スキャン
- **通知**: musl / BusyBox の新版を検知したときに Issue を自動作成
  （Trivy の結果は SARIF を Security タブに送るだけで、Issue は作らない）

> **イメージの Trivy スキャンは行っていません。** Kimigayo は
> `scratch` 上の手組み rootfs でパッケージデータベースを持たないため、
> Trivy は対象を 1 つも識別できません
> （実測で `Target: -` / `Not scanned` / `Metadata.OS: null` / `Results: 0`）。
> **「脆弱性 0 件」ではなく「スキャンしていない」。**
> 構成要素（musl / BusyBox / OpenRC）の CVE 照合は
> **`scripts/scan-image.sh` が出荷物の版で行います**（下記 4.）。
> カーネルはイメージに入らないので対象外です。

#### 4. 依存レビューと公開イメージの照合（`dependency-review.yml`）
`main` への PR と毎週月曜 04:00 UTC、手動。

- `dependency-review`（PR のみ）: `fail-on-severity: high`
- `published-image-scan`（定期・手動のみ）: Docker Hub の `latest` を pull し、
  `scripts/scan-image.sh` で CVE 照合と秘密情報スキャン。定期実行で
  失敗すると `add-to-project` が非公開の Project に項目を足します

> 以前の「Check component versions against CVE databases」ステップは
> CVE データベースを照会せず、`versions.mk` の版を表示するだけでした
> （2026-10-11 に置き換え）。

#### 検出された CVE と対応（2026-10-11）

v3.0.1 の公開イメージで `scan-image.sh` が 5 件を検出しました。
5 件すべてにパッチを当て、v3.0.2 で出荷しています。

| 構成要素 | CVE | 内容 | 対応 |
| --- | --- | --- | --- |
| BusyBox 1.38.0 | CVE-2026-38754 | ash の `ifsbreakup` の範囲外アクセス | **パッチ済み**（`src/busybox/patches/0002-...`、Alpine aports と同じもの） |
| musl 1.2.6 | CVE-2026-40200 | `qsort` のスタック破壊（64bit では非現実的） | **パッチ済み**（`src/libc/patches/0001-...`） |
| musl 1.2.6 | CVE-2026-6042 | `iconv` の GB18030 による CPU DoS | **パッチ済み**（`src/libc/patches/0002-...`） |
| BusyBox 1.38.0 | CVE-2026-38753 | awk の use-after-free | **パッチ済み**（`src/busybox/patches/0003-...`）。Alpine にも無いため BusyBox の ML の修正を読んで取り込んだ |
| BusyBox 1.38.0 | CVE-2026-38755 | ash の関数の無限再帰によるスタック枯渇 | **パッチ済み**（`src/busybox/patches/0004-...`、同上）。深さ 1000 で打ち切る |

パッチ済みの CVE はイメージの `/.kimigayo-build-info` の `PATCHED_CVES` に
記録され、`scan-image.sh` はそれを照合結果から除外します（除外したものは
ログに出します）。**パッチ前に出した v3.0.1 の公開イメージには記録が無いので、
5 件とも検出されます。** **v3.0.2（2026-10-12 公開）で 5 件とも解消し、
`latest` に対する `published-image-scan` は 0 件で通っています**（run 38163985679。
手動実行、2026-10-11 UTC）。
**CI（毎 push）とリリース（push 前）でも CVE を照合する**ので、
未対応の CVE があるイメージは公開されません。

#### 上流との突き合わせで取り込んだ修正（2026-10-14）

`scan-image.sh` は NVD の CPE しか見ないので、Alpine・Debian だけが持つ修正や、
リリース前の上流の修正は見えません。2026-10-14 に `watch-upstream-fixes.py` で
初めて突き合わせ、**修正があるのに持っていなかった 33 件**が見つかりました。

- **30 件を取り込みました**（BusyBox 19 本・musl 5 本のパッチと、OpenRC の
  bootmisc の既定の変更）。BusyBox の CVE は 13 件で、httpd の認証・ACL、
  libpwdgrp の heap overflow、TLS、awk、wget、tar・netstat の端末エスケープ。
  CVE ID の無いものでは、bunzip2 のメモリ破壊（v3.0.2 の bzcat が攻撃サンプルで
  segfault）と musl の floatscan の範囲外書き込みが重い
- **wget の https は証明書を検証できないので、既定で失敗させる**ようにしました
  （CVE-2018-1000500。`--no-check-certificate` で従来どおり）
- **minimal から httpd・ssl_server・udhcpc など 38 個のネットワーク系アプレットを
  外しました。** config に書いていない項目が既定値で有効になっていたためで、
  上の CVE の多くが minimal にも当たっていた原因です
- **CVE-2026-108119（tar）は待ちます。** 上流 git に修正はあるがリリースされて
  いないため、リリースか Debian / Alpine に入るまで取り込みません

1 件ずつの根拠と状態は [upstream-triage.tsv](upstream-triage.tsv)、
出所は各パッチの冒頭にあります。

#### 5. 上流更新の検知（`base-image-update.yml`）
毎週月曜 03:00 UTC。構成要素の新版を検知して PR を作成します。

### ローカル監査実行

```bash
# 総合（scan-image + trivy-fs-scan + shellcheck-scan）
make security-scan

# 個別スキャン
make scan-image          # 出荷物の CVE 照合（SBOM + Grype）と秘密情報（有効）
make trivy-fs-scan       # ファイルシステム（有効）
make shellcheck-scan     # シェルスクリプト（有効）
make trivy-scan          # Dockerイメージ（**何も検査しない**。security-scan には含まれない）
```

`make scan-image` は `kimigayo-os:$(VARIANT)-$(ARCH)` を対象にするので、
先にイメージをビルドしておきます。`SCANS`（既定 `secret vuln`）・
`SBOM_OUT`・`FAIL_ON`（既定 `low`）で挙動を変えられます。

**`make trivy-scan` は何も検査しなくても終了します。沈黙を安全と
読まないこと**（2026-10-11 に `security-scan` から外しました）。

## 外部監査

### 外部セキュリティ監査の実施

> **この節は、第三者が監査を申し出た場合の進め方の目安です。**
> 監査業者を選定・契約する予定はありません。

#### 監査プロセス（目安）
1. **キックオフミーティング**（Week 0）
   - スコープ確定
   - 情報提供リスト作成
   - スケジュール調整

2. **情報収集フェーズ**（Week 1-2）
   - ドキュメント提供
   - アーキテクチャ説明
   - テスト環境準備

3. **監査実施フェーズ**（Week 3-5）
   - 自動スキャン
   - 手動監査
   - ペネトレーションテスト

4. **報告フェーズ**（Week 6）
   - 監査レポート受領
   - 発見事項の確認
   - 質疑応答

5. **フォローアップ**（Week 7-12）
   - 修正実施
   - 再テスト
   - 最終レポート

### 提供する情報

- ソースコードリポジトリ（読み取り専用アクセス）
- ビルド手順ドキュメント
- セキュリティアーキテクチャドキュメント
- 既知の問題リスト（この文書の「検出された CVE と対応」と
  [HARDENING_GUIDE.md](HARDENING_GUIDE.md) の既知の指摘）
- 過去の監査レポートは無い（外部監査の実施歴が無い）

## 監査結果の報告

### 報告フォーマット

#### 1. エグゼクティブサマリー
- 監査期間と範囲
- 主要な発見事項（3-5項目）
- リスクレベル評価
- 総合評価

#### 2. 詳細発見事項
各発見事項について：
- **ID**: AUDIT-YYYY-MM-NNN（レポート自体の ID は [AUDIT_REPORT_TEMPLATE.md](AUDIT_REPORT_TEMPLATE.md) と同じ AUDIT-YYYY-MM）
- **タイトル**: 問題の簡潔な説明
- **重大度**: Critical / High / Medium / Low
- **CVSS Score**: 該当する場合
- **影響範囲**: 影響を受けるコンポーネント
- **詳細**: 技術的な詳細説明
- **再現手順**: 問題の再現方法
- **推奨対策**: 修正方法の提案
- **参考情報**: CVE, CWE, 関連ドキュメント

#### 3. 修正計画
- 優先度順の修正リスト
- 推定工数
- 実施スケジュール

### GitHub Issueテンプレート

```markdown
## セキュリティ監査発見事項: [タイトル]

**監査ID**: AUDIT-2025-12-001
**発見日**: 2025-12-21
**重大度**: High
**CVSS**: 7.5

### 問題の概要
[問題の簡潔な説明]

### 影響範囲
- コンポーネント: [影響を受けるコンポーネント]
- バージョン: [影響を受けるバージョン]

### 再現手順
1. [ステップ1]
2. [ステップ2]

### 推奨対策
[修正方法の提案]

### 参考情報
- CVE: CVE-YYYY-NNNNN
- CWE: CWE-NNN
```

## 監査チェックリスト

### 実施前チェックリスト
- [ ] 監査計画書作成完了
- [ ] 監査チーム編成完了
- [ ] 監査環境準備完了
- [ ] ツール導入完了
- [ ] スケジュール確定

### 実施中チェックリスト
- [ ] 自動スキャン実行完了
- [ ] 設定監査完了
- [ ] コード監査完了
- [ ] ペネトレーションテスト完了
- [ ] 発見事項記録完了

### 実施後チェックリスト
- [ ] 監査レポート作成完了
- [ ] ステークホルダー報告完了
- [ ] GitHub Issue作成完了
- [ ] 修正計画策定完了
- [ ] 監査アーカイブ完了

## 継続的改善

### 監査プロセスの改善（指針）
- ツールの評価と更新（例: Trivy のイメージスキャンが機能しないと分かり、
  2026-10-11 に `scan-image.sh` に置き換えた）
- 新たな脅威への対応
- ベストプラクティスの取り込み

### 修正の期限

指標（KPI）は計測していません。修正の期限は
[SECURITY_POLICY.md](SECURITY_POLICY.md#報告後の流れ) のとおりです
（Critical 7日 / High 30日 / Medium 90日 / Low 次回リリース）。

## 関連ドキュメント

- [ペネトレーションテストガイド](./PENETRATION_TEST.md)
- [脆弱性報告手順](./VULNERABILITY_REPORTING.md)
- [セキュリティポリシー](./SECURITY_POLICY.md)
- [セキュリティ強化ガイド](./HARDENING_GUIDE.md)

## 履歴

| バージョン | 日付 | 変更内容 |
|----------|------|---------|
| 1.0.0 | 2025-12-21 | 初版作成 |
| 1.1.0 | 2026-10-12 | 出荷物の CVE 照合（scan-image）・署名・再現可能ビルドの現状に合わせ、実施していない監査を「指針」と明記 |

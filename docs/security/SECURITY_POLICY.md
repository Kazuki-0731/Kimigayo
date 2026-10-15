# Kimigayo OS セキュリティポリシー

## セキュリティ哲学

Kimigayo OSは**セキュアバイデフォルト**を目指しています。バイナリは強化フラグを付けてビルドし、パッケージマネージャーや sshd・sudo のような道具は入れていません。
ただし既定のユーザーは root で、seccomp プロファイルも配布していないので、実行時の強化は利用者が `docker run` のオプションで行います（→ 下記「利用者向け」）。

成果物は **rootfs だけを詰めた Docker イメージ**で、カーネルを含みません。
コンテナはホストのカーネルとコンテナランタイムの上で動くので、
このポリシーが対象にするのはイメージの中身（musl libc / BusyBox / OpenRC と
ビルド経路）です。

## サポートバージョン

**最新のリリースだけ**がセキュリティアップデートの対象です。
修正は新しいパッチリリース（例: 3.0.1 → 3.0.2）として出し、
Docker Hub の `latest` 系のタグを差し替えます。
古い版へのバックポートはしません（利用者は新しい版に上げてください）。

| バージョン | サポート状況 |
|-----------|-------------|
| 最新の 3.0.x（現在 3.0.2） | ✅ サポート中 |
| それより前（3.0.1 以前） | ❌ サポート終了 |

## 脆弱性報告

セキュリティ脆弱性を発見した場合は、以下の手順に従って報告してください。

### 報告方法

**重要**: 公開のIssue Trackerに脆弱性を報告しないでください。

**報告の窓口は GitHub Security Advisories だけです**（非公開で届きます）。

1. [GitHub Security Advisories](https://github.com/Kazuki-0731/Kimigayo/security/advisories/new)にアクセス
2. "Report a vulnerability"をクリック
3. 脆弱性の詳細を記入して送信

メールや PGP による報告窓口はありません。

### 報告に含めるべき情報

脆弱性報告には以下の情報を含めてください：

1. **脆弱性の種類**
   - バッファオーバーフロー、権限昇格、情報漏洩など

2. **影響を受けるコンポーネント**
   - musl libc / BusyBox / OpenRC / ビルドスクリプト・ワークフロー など
     （**パッケージマネージャーは持ちません**。カーネルはイメージに入りません）

3. **再現手順**
   ```bash
   # 具体的なコマンドやスクリプト
   ```

4. **影響範囲**
   - どのバージョン（イメージのタグ）が影響を受けるか
   - 悪用の条件（ローカル/リモート、認証の有無など）

5. **概念実証（PoC）**（任意）
   - 脆弱性を実証するコードやスクリプト

6. **推奨される緩和策**（分かる場合）

### 報告後の流れ

1. **受領確認**: 24時間以内に受領を確認
2. **初期評価**: 72時間以内に脆弱性の評価を実施
3. **修正作業**: 重大度に応じて優先度を設定
   - **Critical**: 7日以内
   - **High**: 30日以内
   - **Medium**: 90日以内
   - **Low**: 次回リリース時
4. **セキュリティアドバイザリ公開**: 報告を受けた脆弱性は、修正版リリースと同時に GitHub Security Advisories で公開
   （上流が公表済みの CVE にパッチを当てた場合は、[CHANGELOG.md](../../CHANGELOG.md) の Security 節に記録します）

## セキュリティアップデート

### セキュリティアドバイザリの購読

- **GitHubリポジトリWatch**: リポジトリの Watch → Custom → Security alerts
  （[Security Advisories](https://github.com/Kazuki-0731/Kimigayo/security/advisories)）
- **リリース**: [GitHub Releases](https://github.com/Kazuki-0731/Kimigayo/releases)。
  修正の内容は [CHANGELOG.md](../../CHANGELOG.md) の Security 節に書きます

## 構成要素の既知の脆弱性（CVE）

上流（musl / BusyBox / OpenRC）の CVE は、**出荷するイメージそのもの**で
照合します（`scripts/scan-image.sh`）。

- イメージ内のバイナリを実行して読んだ版から SBOM（CycloneDX）を作り、
  Grype で NVD の CPE と照合します
- **CI（毎 push）と、リリースの Docker Hub への push 前**に走り、
  未対応の CVE があれば止めます。公開中の `latest` も毎週照合します
- 上流がまだ修正版を出していない CVE には、パッチを当てて出荷します。
  当てたものはイメージの `/.kimigayo-build-info` の `PATCHED_CVES` に
  記録され、照合結果から除外されます
- **SBOM は GitHub Release に添付します**（v3.0.2 から。イメージの
  attestation ではなく Release の添付ファイルです）。
  自分の照合器にかけて確かめられます

**「0 件」は「NVD の CPE に載っている範囲で 0 件」です。** CPE の版範囲が
不正確な CVE は取りこぼしや誤検知があり得ます。
対応の記録は [SECURITY_AUDIT.md](SECURITY_AUDIT.md) にあります。

## セキュリティ機能

### コンパイル時のセキュリティ強化

フラグの実体は `scripts/build-{musl,busybox,openrc}.sh` にあります。

| 機能 | 説明 | 状態 |
|------|------|------|
| **PIE** | Position Independent Executables | ✅ 全 ELF（`verify-image.sh` が検査） |
| **RELRO** | Relocation Read-Only | ✅ Full RELRO（BIND_NOW）。全 ELF（検査あり） |
| **非実行スタック** | `PT_GNU_STACK` に実行権限なし | ✅ 全 ELF（検査あり） |
| **Stack Protector** | スタックバッファオーバーフロー保護 | ⚠️ x86_64 は全 ELF。**v3.0.2 の arm64 の OpenRC（`openrc`・`openrc-run`・`librc`・`libeinfo` など）には付いていません**（`build-openrc.sh` が arm64 だけ外していた。v3.1.0 で修正しました）。`verify-image.sh` が検査 |
| **FORTIFY_SOURCE** | バッファオーバーフロー検出 | ✅ `-D_FORTIFY_SOURCE=2`（Alpine の `fortify-headers` 経由。musl 自身は実装しない）。**v3.0.2 の arm64 には効いていません**（v3.1.0 で修正）。`verify-image.sh` が BusyBox のトラップの数で検査 |

確認方法（イメージ内の**全 ELF** の PIE / RELRO / BIND_NOW / 非実行スタック・
スタック保護（libc から 20 個以上の関数を取り込む動的 ELF が `__stack_chk_fail` を
参照しているか）・FORTIFY（`/bin/busybox` に検査のトラップがあるか）を検査します。
イメージに `checksec` は入っていません）：
```bash
bash scripts/verify-image.sh <image> <variant> <arch>
```

### イメージの署名

v3.0.2 から、公開イメージは `release.yml` の `sign` ジョブで
Cosign のキーレス署名（Sigstore OIDC）をしています。v3.0.1 以前は未署名です。
**検証には cosign v3 以上が必要です**（v2 では `no signatures found` になります）。

```bash
cosign verify ishinokazuki/kimigayo-os:3.1.0 \
  --certificate-identity-regexp '^https://github.com/Kazuki-0731/Kimigayo/' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com
```

Docker Content Trust（DCT）は使っていません。

### ランタイムセキュリティ

| 機能 | 説明 | デフォルト |
|------|------|-----------|
| **ASLR** | Address Space Layout Randomization | **ホストのカーネル**が有効なら効く（イメージ側は PIE で対応） |
| **DEP** | Data Execution Prevention (NX bit) | **ホストのカーネル**が有効なら効く（イメージ側は非実行スタックで対応） |
| **Seccomp-BPF** | システムコールフィルタリング | **ホスト側で指定**（`docker run --security-opt seccomp=...`）|
| **Namespaces** | プロセス隔離 | **ホスト側**（コンテナランタイムが提供）|

> **どれもイメージの属性ではありません。** 成果物は rootfs だけで
> カーネルを含まないため、ASLR・NX を効かせるのも、seccomp プロファイルを
> 適用するのも namespace を張るのもホストです。
> イメージ側が保証できるのは、それが効くようにバイナリを作ること
> （PIE と非実行スタック）だけです。

確認方法（ホストの設定がコンテナからも見えます）:
```bash
# ASLRの状態確認（2 = 完全なランダム化）
cat /proc/sys/kernel/randomize_va_space
```

## セキュリティ監査

### 自動の検査

- **依存関係スキャン**: 毎週（`dependency-review.yml`）
- **構成要素の版の確認・リポジトリの脆弱性スキャン**: 毎日（`security.yml`）
- **出荷物の CVE 照合と秘密情報スキャン**: 毎 push とリリース前（上記）

### 外部監査

独立した第三者によるセキュリティ監査を歓迎します。
GitHub Security Advisories か [Discussions](https://github.com/Kazuki-0731/Kimigayo/discussions) で連絡してください。

## セキュリティベストプラクティス

### 利用者向け（コンテナの実行）

Kimigayo OS はコンテナとして動かす前提です。強化はホスト側の
`docker run` のオプションで行います。

```bash
docker run --rm \
  --read-only \
  --cap-drop ALL \
  --security-opt no-new-privileges \
  --user 1000:1000 \
  --tmpfs /tmp:rw,noexec,nosuid \
  ishinokazuki/kimigayo-os:latest <command>
```

- イメージは `USER` を指定していません（OS のベースイメージのため root）。
  自分のアプリのイメージで `USER` を指定してください
- 詳しくは [HARDENING_GUIDE.md](HARDENING_GUIDE.md)

### 開発者向け

```bash
# コンパイルオプションの概略（実体は scripts/build-{musl,busybox,openrc}.sh。
# 構成要素とアーキテクチャで少しずつ違う。v3.0.2 の arm64 の OpenRC には
# -fstack-protector-strong が無い。v3.1.0 で修正）
CFLAGS="-Os -fPIE -fstack-protector-strong -D_FORTIFY_SOURCE=2"
LDFLAGS="-Wl,-z,relro -Wl,-z,now -Wl,-z,noexecstack"

# 静的解析と出荷物の検査（make static-analysis は存在しない）
make shellcheck-scan
make security-scan
```

## 既知の制限事項

1. **カーネルの緩和策（Spectre/Meltdown など）・SELinux/AppArmor**: ホストの設定に依存します。イメージ側では設定できません
2. **`wget` の HTTPS**: v3.0.1 以前は取得後に Segmentation fault で落ちます（v3.0.2 で修正）。
   → [busybox-wget-https-segfault.md](../troubleshooting/busybox-wget-https-segfault.md)
3. **TLS 証明書の検証**: BusyBox の `wget` は証明書を検証しません。
   v3.0.2 までは注意を出して取得を続けていました。v3.1.0 からは、
   `--no-check-certificate` を付けない限り `https://` の取得を失敗させます
   （CVE-2018-1000500。Alpine と同じ）。
   信頼できない経路で HTTPS を使うなら `curl` などを持ち込んでください

## 参考リソース

- **セキュリティガイド**: [SECURITY_GUIDE.md](SECURITY_GUIDE.md)
- **脆弱性報告手順**: [VULNERABILITY_REPORTING.md](VULNERABILITY_REPORTING.md)
- **セキュリティ強化設定**: [HARDENING_GUIDE.md](HARDENING_GUIDE.md)
- **監査レポート**: [SECURITY_AUDIT.md](SECURITY_AUDIT.md)（`audits/` は未作成）

## 連絡先

- **脆弱性の報告**: [GitHub Security Advisories](https://github.com/Kazuki-0731/Kimigayo/security/advisories/new)（非公開）
- **質問・相談**: [GitHub Discussions](https://github.com/Kazuki-0731/Kimigayo/discussions)

---

**最終更新**: 2026-10-12

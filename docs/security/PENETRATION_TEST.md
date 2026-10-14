# Kimigayo OS ペネトレーションテストガイド

このドキュメントでは、Kimigayo OSに対するペネトレーションテスト（侵入テスト）の実施方法とガイドラインを定義します。

## 目次

1. [ペネトレーションテストの目的](#ペネトレーションテストの目的)
   - [攻撃面のベースライン](#攻撃面のベースラインv302-実測2026-10-12)
2. [テストスコープ](#テストスコープ)
3. [テスト環境](#テスト環境)
4. [テスト手法](#テスト手法)
5. [テストツール](#テストツール)
6. [テストシナリオ](#テストシナリオ)
7. [報告とフォローアップ](#報告とフォローアップ)

## ペネトレーションテストの目的

Kimigayo OSのペネトレーションテストは以下の目的で実施されます：

- **実環境での脆弱性検証**: 理論上の脆弱性が実際に悪用可能かを検証
- **防御機能の評価**: セキュリティ強化機能の有効性を検証
- **攻撃シナリオの理解**: 実際の攻撃者の視点でシステムを評価
- **インシデント対応の訓練**: セキュリティインシデント対応手順の検証

## 攻撃面のベースライン（v3.0.2 実測、2026-10-12）

**テストを始める前に、何が「無い」かを把握してください。**
Kimigayo の攻撃面の小ささは、まず欠落によって成り立っています。

| 項目 | 実測 |
| --- | --- |
| setuid / setgid バイナリ | **0 個**（`find / -xdev -perm /6000 -type f`）|
| world-writable なファイル | **0 個**（`find / -xdev -type f -perm -0002`）|
| 既定のリスニングポート | **0 個**（`netstat -tuln`）|
| 共有ライブラリ | **3 個のみ**（musl の `libc.so`、OpenRC の `librc` / `libeinfo`）|
| 既定のユーザー | **root**（`USER` 指定なし）|
| パッケージマネージャー | **無し**（`apk` / `apt` / `dpkg` / `rpm` / `yum` / `pacman`）|

**イメージに入っていないもの**（権限昇格・横展開の道具として想定されるもの）:
`sudo` / `/etc/sudoers` / `wheel` グループ / `sshd` / `/etc/ssh` /
`iptables` / `curl` / `gcc` / `strace` / `tcpdump` / `logrotate` /
`auditd` / `capsh` / `bash` / `/etc/cron.*` / `/usr/share/zoneinfo` / `/boot`。

**入っているが起動していないもの**（BusyBox のアプレット）:
`crond`・`su`・`nsenter`・`unshare`（全バリアント）、
`telnetd`・`ftpd`・`httpd`・`nc`・`telnet`・`wget`（standard 以上）、`ar`（extended のみ）。
v3.0.2 までは minimal にも `telnetd`・`ftpd`・`httpd`・`ssl_server`・`udhcpc` などが
入っていた（config に書いていない項目が既定値で有効になっていた。次の版から外す）。
サーバー系のアプレットは、利用者が起動しない限り待ち受けません。

**既定の PID 1 は `/bin/sh`** で、OpenRC は起動していません。
`/etc/init.d/` のサービスは `/sbin/init` を PID 1 にしたときだけ動きます。

### 既知の弱点

- **`cpio` と `ar` のディレクトリ脱出は v3.0.2 で修正済み**
  （`CONFIG_FEATURE_PATH_TRAVERSAL_PROTECTION=y`。v3.0.1 までは `../` を
  剥がさなかった。`verify-image.sh` が回帰を見る）。
  `tar` のリンク経由の脱出（CVE-2026-108119）は **1.38.0 も影響を受ける**
  （2 本の tar を同じ展開先に続けて展開すると抜ける。2026-10-13 に実測）。
  上流 BusyBox に修正コミット（`382008b3f07d`）はあるがリリースされておらず、Kimigayo は
  リリースか Debian / Alpine に入るまで待つ（2026-10-14 に決定）。
  NVD に CPE が無いので `make scan-image` でも検出できない。
  → [HARDENING_GUIDE.md](HARDENING_GUIDE.md#busybox-の-cpio-はディレクトリを脱出できたv301-まで修正済み)
- **`wget` の HTTPS は v3.0.1 以前で、取得後に Segmentation fault で落ちる**
  （x86_64 / arm64 とも。v3.0.2 で修正）。可用性の問題であり、情報漏洩の
  経路ではない。**証明書は検証しない**（BusyBox の仕様。中間者攻撃に弱い）。
  次の版からは `--no-check-certificate` なしの `https://` を失敗させる
  （CVE-2018-1000500。Alpine の 0017 を取り込んだ）。
  → [busybox-wget-https-segfault.md](../troubleshooting/busybox-wget-https-segfault.md)
- **root で動く。** `Dockerfile.runtime` は `USER` を指定していません
  （OS ベースイメージなので利用側が決める方針）。
  テストでは `--user` を付けた場合と付けない場合の両方を見てください。

## テストスコープ

### インスコープ

#### 1. コンテナ環境
- [ ] Dockerコンテナのエスケープ
- [ ] コンテナ間の不正アクセス
- [ ] ホストシステムへの影響
- [ ] リソース制限のバイパス

#### 2. ネットワーク
- [ ] ポートスキャンと開放ポート検証
- [ ] ネットワークサービスの脆弱性
- [ ] man-in-the-middle攻撃の可能性
- [ ] ネットワーク分離の有効性

#### 3. 認証・認可
- [ ] 権限昇格の可能性
- [ ] 不適切な権限設定
- [ ] SetUID/SetGIDバイナリの悪用
- [ ] サービス間認証のバイパス

#### 4. ファイルシステム
- [ ] ディレクトリトラバーサル
- [ ] シンボリックリンク攻撃
- [ ] ファイル権限の不備
- [ ] 機密情報の露出

#### 5. Init システム (OpenRC)
- [ ] サービス設定の改ざん
- [ ] サービス起動時の権限昇格
- [ ] サービス間依存関係の悪用
- [ ] ログファイルの改ざん

### アウトオブスコープ

以下は通常テスト対象外（特別な許可がない限り）：
- 本番環境への直接的な攻撃
- DoS/DDoS攻撃
- ソーシャルエンジニアリング
- 物理的セキュリティ
- 第三者システムへの攻撃

## テスト環境

### 推奨テスト環境

```yaml
環境タイプ: 隔離されたテスト環境
ホストOS: Ubuntu 22.04 LTS または相当
Docker: 最新安定版
ネットワーク: 専用VLAN（インターネットから隔離）
監視: 全アクティビティのログ記録
```

### 環境構築手順

```bash
# 1. テスト用ネットワークの作成
docker network create --driver bridge pentest-network

# 2. Kimigayo OSコンテナの起動（既定の CMD は /bin/sh なので常駐させる）
docker run -d \
  --name kimigayo-target \
  --network pentest-network \
  --cap-drop=ALL \
  ishinokazuki/kimigayo-os:3.0.2 sleep infinity

# 3. 攻撃用コンテナの起動（Kali Linux）
docker run -d \
  --name pentest-kali \
  --network pentest-network \
  --privileged \
  kalilinux/kali-rolling

# 4. ログ収集の設定
mkdir -p logs
docker logs -f kimigayo-target > logs/target.log &
docker logs -f pentest-kali > logs/attacker.log &
```

## テスト手法

### 1. ブラックボックステスト

**前提条件**: システムの内部情報なし（外部攻撃者の視点）

**フェーズ**:
1. 情報収集（Reconnaissance）
2. スキャンと列挙（Scanning & Enumeration）
3. 脆弱性分析（Vulnerability Analysis）
4. エクスプロイト（Exploitation）
5. 権限昇格（Privilege Escalation）
6. 永続化（Persistence）

### 2. グレーボックステスト

**前提条件**: 限定的な内部情報あり（内部者の視点）

**追加情報**:
- ユーザーアカウント（非特権）
- 基本的なシステム構成情報
- ネットワークトポロジー

### 3. ホワイトボックステスト

**前提条件**: 完全な内部情報あり（開発者/管理者の視点）

**提供情報**:
- ソースコード
- アーキテクチャドキュメント
- 設定ファイル
- 既知の問題リスト

## テストツール

### 基本ツール

#### 1. ポートスキャン・列挙
```bash
# Nmap - ポートスキャン
nmap -sV -sC -p- <target-ip>

# Netcat - バナーグラビング
nc -v <target-ip> <port>

# Masscan - 高速ポートスキャン
masscan -p1-65535 <target-ip> --rate=1000
```

#### 2. 脆弱性スキャン
```bash
# 出荷物の CVE 照合（リポジトリで実行。SBOM + Grype）
# `trivy image` はパッケージ DB の無い Kimigayo を識別できず、何も検査しない
make scan-image VARIANT=standard ARCH=x86_64

# Nikto - Webサーバースキャン（該当する場合）
nikto -h http://<target-ip>
```

#### 3. エクスプロイト
```bash
# Metasploit Framework
msfconsole
use exploit/linux/...

# Exploit-DB検索
searchsploit <software-name>
```

#### 4. 権限昇格
```bash
# LinPEAS - Linux権限昇格スクリプト
./linpeas.sh

# Linux Exploit Suggester
./linux-exploit-suggester.sh

# GTFOBins - SetUIDバイナリ悪用
# https://gtfobins.github.io/
```

#### 5. コンテナエスケープ
```bash
# Docker脱出テスト
# ケーパビリティ確認（capsh はイメージに無い）
grep Cap /proc/self/status

# マウントポイント確認
mount | grep docker

# cgroup確認
cat /proc/1/cgroup

# Namespace確認
ls -la /proc/self/ns/
```

### 専門ツール

#### コンテナセキュリティ
- **amicontained**: コンテナランタイム情報の取得
- **docker-bench-security**: Docker環境のセキュリティベンチマーク
- **clair**: コンテナイメージの静的解析

#### ネットワーク
- **Wireshark**: パケットキャプチャと解析
- **tcpdump**: コマンドラインパケットキャプチャ
- **Burp Suite**: HTTP/HTTPSプロキシ（該当する場合）

## テストシナリオ

### シナリオ 1: コンテナエスケープ

**目的**: コンテナから脱出してホストシステムにアクセス

**ステップ**:

1. **ケーパビリティの確認**
   ```bash
   # コンテナ内で実行（capsh はイメージに無いので /proc で見る）
   grep Cap /proc/self/status
   ```
   期待結果: `--cap-drop=ALL` なら `CapEff` が 0（CAP_NET_ADMIN 等の危険なケーパビリティなし）

2. **マウントの確認**
   ```bash
   mount | grep -E "(docker|overlay)"
   cat /proc/mounts
   ```
   期待結果: ホストファイルシステムへの危険なマウントなし

3. **デバイスアクセステスト**
   ```bash
   ls -la /dev
   ```
   期待結果: 最小限のデバイスのみアクセス可能

4. **Namespace脱出試行**
   ```bash
   nsenter --target 1 --mount --uts --ipc --net --pid /bin/sh
   ```
   期待結果: 失敗（権限不足）

### シナリオ 2: 権限昇格

**目的**: 非特権ユーザーからroot権限を取得

**ステップ**:

1. **SetUIDバイナリの検索**
   ```bash
   find / -perm -4000 -type f 2>/dev/null
   ```
   期待結果: 0 個（公開イメージに setuid / setgid は無い。`verify-image.sh` が検査）

2. **書き込み可能なcronジョブ確認**
   ```bash
   ls -la /etc/crontabs /var/spool/cron 2>&1
   ```
   期待結果: 存在しない（`crond` のアプレットはあるが、設定も起動も無い）

3. **sudoers設定確認**
   ```bash
   command -v sudo; ls /etc/sudoers
   ```
   期待結果: どちらも無い（`su` はあるが、root 以外のユーザーは `nobody` だけ）

4. **カーネル脆弱性確認**（**ホスト側の評価**）
   ```bash
   uname -a
   # Linux Exploit Suggesterで既知の脆弱性確認
   ```
   カーネルはホストのもので、イメージの性質ではありません。
   結果はホストの評価として記録します

### シナリオ 3: ネットワーク攻撃

**目的**: ネットワーク経由での不正アクセス

**ステップ**:

1. **ポートスキャン**
   ```bash
   nmap -sV -p- <target-ip>
   ```
   期待結果: 既定では開放ポートなし（待ち受けるのは利用者が起動したアプリだけ）

2. **サービス脆弱性スキャン**
   ```bash
   nmap --script vuln <target-ip>
   ```
   期待結果: 既知の脆弱性なし

3. **DoS耐性テスト**（承認された環境のみ）
   ```bash
   hping3 -S --flood -p 80 <target-ip>
   ```
   期待結果: イメージ側にレート制限は無い。結果はホスト・ランタイム側（`--pids-limit`・`--memory`・ホストのファイアウォール）の評価として記録する

### シナリオ 4: ファイルシステム攻撃

**目的**: ファイルシステムの不適切な設定を悪用

**ステップ**:

1. **ワールドライタブルファイル検索**
   ```bash
   find / -perm -002 -type f 2>/dev/null
   ```
   期待結果: なし（world-writable なのは `/tmp`・`/var/tmp` のディレクトリだけで、どちらも sticky bit 付き）

2. **シンボリックリンク攻撃**
   ```bash
   # /tmpでシンボリックリンクを使った攻撃試行
   ln -s /etc/shadow /tmp/symlink
   ```
   期待結果: 攻撃失敗。ただし防ぐのはホストのカーネルの `fs.protected_symlinks` で、
   イメージの性質ではない（結果はホストの評価として記録する）

3. **ディレクトリトラバーサル**
   ```bash
   # アプリケーションがファイルパスを扱う場合
   cat ../../../../etc/passwd
   ```
   期待結果: パス検証により攻撃失敗

## テスト実施チェックリスト

### 事前準備
- [ ] テスト計画書作成完了
- [ ] テストスコープ合意取得
- [ ] テスト環境構築完了
- [ ] ツール準備完了
- [ ] ログ記録設定完了
- [ ] バックアップ取得完了

### テスト実施中
- [ ] 全テストシナリオ実行
- [ ] 発見事項の記録
- [ ] スクリーンショット/証跡取得
- [ ] 重大な問題の即時報告

### テスト完了後
- [ ] テスト環境のクリーンアップ
- [ ] ログの保存とアーカイブ
- [ ] テストレポート作成
- [ ] 発見事項のGitHub Issue登録

## 報告とフォローアップ

### レポート構成

#### 1. エグゼクティブサマリー
- テスト期間と範囲
- 主要な発見事項
- リスク評価
- 推奨事項

#### 2. テスト詳細
- 実施したテストシナリオ
- 使用したツールとテクニック
- タイムライン

#### 3. 発見事項
各脆弱性について：
- **ID**: PENTEST-YYYY-MM-NNN
- **タイトル**: 脆弱性名
- **重大度**: Critical / High / Medium / Low / Info
- **CVSS Score**: v3.1スコア
- **再現手順**: 詳細なステップ
- **PoC**: 概念実証コード
- **影響**: 悪用された場合の影響
- **推奨対策**: 修正方法

#### 4. ポジティブな発見
- 効果的なセキュリティ対策
- 期待通りに機能した防御機能

### 発見事項の重大度基準

| 重大度 | CVSS | 説明 | 例 |
|--------|------|------|-----|
| Critical | 9.0-10.0 | リモートコード実行、完全な権限昇格 | リモートroot取得 |
| High | 7.0-8.9 | 重要な情報漏洩、限定的な権限昇格 | ユーザーデータ読み取り |
| Medium | 4.0-6.9 | 情報漏洩、DoS、設定不備 | バージョン情報露出 |
| Low | 0.1-3.9 | 限定的な情報漏洩 | エラーメッセージ詳細 |
| Info | 0.0 | セキュリティ上の問題なし | ベストプラクティス推奨 |

### フォローアップ

修正の期限は[セキュリティポリシー](SECURITY_POLICY.md#報告後の流れ)に合わせます。

| 重大度 | 修正の期限 |
| --- | --- |
| Critical | 7日以内 |
| High | 30日以内 |
| Medium | 90日以内 |
| Low | 次回リリース時 |

修正後は、該当するシナリオを再実行して確認します。

## セキュリティに関する注意事項

### 実施者の責任
- 承認されたスコープ内でのみテスト実施
- 発見した脆弱性の機密保持
- テスト環境の適切な管理
- 証跡の完全な記録

### 禁止事項
- 承認されていない攻撃
- 本番環境への影響
- データの破壊・改ざん
- 第三者への情報漏洩

## 関連ドキュメント

- [セキュリティ監査ガイドライン](./SECURITY_AUDIT.md)
- [脆弱性報告手順](./VULNERABILITY_REPORTING.md)
- [インシデント対応](./SECURITY_GUIDE.md#インシデント対応)
- [セキュリティポリシー](./SECURITY_POLICY.md)

## 参考資料

### ペネトレーションテスト標準
- [PTES (Penetration Testing Execution Standard)](http://www.pentest-standard.org/)
- [OWASP Testing Guide](https://owasp.org/www-project-web-security-testing-guide/)
- [NIST SP 800-115](https://csrc.nist.gov/publications/detail/sp/800-115/final)

### コンテナセキュリティ
- [CIS Docker Benchmark](https://www.cisecurity.org/benchmark/docker)
- [NIST SP 800-190 (Application Container Security)](https://csrc.nist.gov/publications/detail/sp/800-190/final)

## 履歴

| バージョン | 日付 | 変更内容 |
|----------|------|---------|
| 1.0.0 | 2025-12-21 | 初版作成 |
| 1.1.0 | 2026-10-12 | 攻撃面のベースラインを v3.0.2 で測り直し、コンテナ前提に合わせて手順と期待結果を修正 |

# ランタイム脅威検知ガイド

**Kimigayo を VPS で動かすときに、「もし破られたら気づく」ための手順。**
侵入そのものを防ぐ（非 root・setuid 0・待ち受け 0）に加えて、**破られたときに
検知し、記録し、通知する**ところまでを扱う。

> このガイドの背景（なぜ必要か）は実測に基づく。2026-10-16 に、わざと脆弱にした
> Kimigayo コンテナへ外部から root を奪取する検証を行い、**既定では検知・記録・
> 通知のどれも起きない**ことを確かめた。詳細はこのページの「3. なぜ必要か」。

関連: [HARDENING_GUIDE.md](HARDENING_GUIDE.md)（防御の設定）・
[SECURITY_GUIDE.md](SECURITY_GUIDE.md)・Falco ルール
[falco/kimigayo_rules.yaml](falco/kimigayo_rules.yaml)。

---

## 1. 考え方: 防御 → 検知 → 対応

| 段 | どこでやるか | 何を |
| --- | --- | --- |
| **防御** | イメージ側（既にある） | 非 root・setuid 0・sudo 無し・パッケージマネージャー無し・待ち受け 0。侵入されても昇格・横展開させない。`verify-image.sh` が毎リリース保証する |
| **検知** | **ホスト／カーネル側** | eBPF（Falco / Tetragon）・auditd で、コンテナのプロセスと syscall を外から見る |
| **対応・通知** | ホスト側 → 外部 | 検知を Discord などへ飛ばす。ログはコンテナ外へ逃がして保全する |

**検知ロジックをイメージに入れない。** 入れると (1) 攻撃面が増え、(2) 侵入した
攻撃者に監視を止められる・欺かれる、(3) root を取られるとログを消される。
だから監視は**コンテナの外（ホスト／VM、別の特権コンテナ）**で動かす。

---

## 2. Kimigayo は検知が効きやすい

普通のコンテナは、シェルも root もパッケージ操作も「正常の一部」なので、
「異常」を定義しにくい。Kimigayo は逆で、**正常時に起きないことが多い**:

- アプリは非 root（例: `USER 65534`）で動く → **uid 0 のプロセス = 異常**
- setuid バイナリは 0 個 → **setuid の実行 = 異常**
- 対話シェルを常用しない → **`sh` の起動 = ほぼ異常**
- 待ち受けは 0（#122 で telnetd などを削除）→ **想定外の着信 = 異常**

**異常の定義が狭いほど、検知は正確でアラートが意味を持つ。** これは最小・非 root
設計の副産物の強み。

---

## 3. なぜ必要か（2026-10-16 の実測）

わざと 3 つ壊した Kimigayo コンテナ（アプリに RCE + SQLi、`setuid root` の
ヘルパ、アプリは nobody で起動）に、外部の別コンテナから攻撃した:

1. SQLi でログイン認証をバイパス
2. RCE でコマンド実行（この時点では `uid=65534(nobody)`）
3. `setuid` ヘルパで `uid=0(root)` に昇格し、任意のファイルを書き込み

**この root 奪取は、既定ではどこにも残らなかった:**

| 防御側が見る場所 | 結果 |
| --- | --- |
| `docker events` | アプリ内の RCE・昇格は 1 件も出ない（コンテナのライフサイクルとホスト発の `docker exec` しか出ない） |
| `docker logs` | アプリの起動行だけ。攻撃の痕跡なし |
| コンテナ内 `/var/log` | 空。auth.log も auditd も wtmp も無い |
| 残った痕跡 | 攻撃者が自分で書いたファイルだけ（消せば痕跡ゼロ） |

**防御（非 root・setuid 0）は効いていた**（それをわざと壊して初めて奪取できた）。
だが「破られたら気づく」手段が無い。これがこのガイドの出発点。

**検知は追加できることも確かめた。** 対象の PID 名前空間を共有する特権コンテナで
`/proc` を見張ると、昇格した root のプロセスとシェルの起動を捉えられた。
ただし **ポーリングは一瞬で終わる昇格を取りこぼし、正常なプロセス（`runc init` 等）
も拾ってノイズが多い。** 確実・低ノイズにするには、syscall を見る Falco /
Tetragon / auditd が要る（→ 4）。

---

## 4. 権限奪取（root 昇格）の検知

**ホスト／VM に Falco を入れ、Kimigayo 向けのルールで uid 0・setuid・シェル起動を
検知する。** ルールは [falco/kimigayo_rules.yaml](falco/kimigayo_rules.yaml)。

```bash
# ホスト（VPS）で。eBPF ドライバを使う（カーネルは Kimigayo ではなくホストのもの）
docker run -d --name falco --privileged \
  -v /var/run/docker.sock:/host/var/run/docker.sock \
  -v /proc:/host/proc:ro \
  -v "$PWD/docs/security/falco/kimigayo_rules.yaml:/etc/falco/rules.d/kimigayo_rules.yaml:ro" \
  falcosecurity/falco:latest
# 検知は falco の標準出力 → ログドライバ → 集約先（→ 6）。通知は falcosidekick で Discord へ
```

ルールの要点（Kimigayo の正常時には起きない事象だけを見る）:

- **uid 0 のプロセスの起動** → `CRITICAL`。非 root 運用が前提。
- **setuid バイナリの exec** → `CRITICAL`。Kimigayo は setuid 0 個。
- **シェルの起動** → `WARNING`。アプリが `shell=True` で外部コマンドを叩く作りだと
  誤検知するので、その場合は**アプリ側を直す**（シェルを介さないのが本来）。

**前提:** 本番で**非 root で動かしていること**（`USER` 指定か `--user`）。root で
動かすと「uid 0 = 異常」が成り立たず、ルールの前提が崩れる。
→ [HARDENING_GUIDE.md](HARDENING_GUIDE.md) の `--user` 運用とセットで使う。

**auditd での代替**（Falco を入れられない場合）。ホストで:

```bash
# setuid 系 syscall と execve を監査（コンテナのプロセスもホストから見える）
auditctl -a always,exit -F arch=b64 -S setuid -S setreuid -S setresuid -k privesc
auditctl -a always,exit -F arch=b64 -S execve -F euid=0 -k root_exec
# ausearch -k privesc / -k root_exec で追う
```

---

## 5. 外部からの不審アクセス・ログインの検知

Kimigayo には SSH も login も無い（設計）。「ログイン」は**利用者のアプリが持つ
認証**のこと。層が 2 つある。

**アプリ層（認証イベント）。** アプリがログインの成功・失敗・ロックを
**構造化ログで標準出力に**出す（→ 6）。集約先で「失敗の連続」「見知らぬ IP からの
成功」を拾う。最小の例:

```python
import json, sys, time
def audit(event, **kw):
    print(json.dumps({"ts": time.time(), "event": event, **kw}), file=sys.stdout, flush=True)
# 例: audit("login_failed", user=u, ip=client_ip)
#     audit("login_ok",     user=u, ip=client_ip)
```

**ネットワーク／ホスト層。** 想定外の着信、開くはずのないポートへの接続、
想定外の外向き接続を Falco（[falco/kimigayo_rules.yaml](falco/kimigayo_rules.yaml) の
外向き接続ルール）と nftables のログで拾う。#122 で待ち受けを 0 にしたので、
「正常時の入口はアプリの 1 ポートだけ。そこ以外へのアクセスは全部異常」と言い切れる。

```bash
# 公開ポート以外への着信をログ（DOCKER-USER チェーン。外向きの制限は HARDENING_GUIDE 参照）
nft add rule inet filter DOCKER-USER tcp dport != { 8080 } ct state new log prefix \"kimigayo-unexpected: \"
```

---

## 6. ログの吐き出しと集約（コンテナ外・改竄耐性）

**ログをコンテナの外へ即座に逃がす。** コンテナ内に貯めると、root を取られた
攻撃者に消される（2026-10-16 の検証で、攻撃者は root で任意のファイルを書けた）。

1. **アプリ・サービスは stdout / stderr に出す**（12-factor）。OpenRC のサービスも
   stdout へ。確認済み: Kimigayo コンテナの stdout は `docker logs` に出る。
2. **Docker のログドライバでホスト外へ送る。** `json-file`（保管上限つき）・
   `journald`・`syslog` / `fluentd` で**別ホストの集約先**へ転送する。

   ```bash
   docker run --log-driver syslog \
     --log-opt syslog-address=tcp://logs.example:514 \
     --log-opt tag="kimigayo/{{.Name}}" ...
   ```
3. **集約先は追記のみ（append-only）**にする。ホスト内に残すと、ホストまで
   取られたときに消される。検知（4・5）の出力もここへ送って一本化する。

**注意:** 標準出力に秘密情報（トークン・パスワード）を出さない。マスキングを規約にする。

---

## 7. 検証のしかた

手元の Linux か使い捨ての VM で、わざと脆弱なコンテナに対してルールが発火するかを
確かめる（他人のホストには向けない）。2026-10-16 の検証では、脆弱コンテナ
（RCE + setuid root、アプリは nobody）に外部から root を奪取し、PID 名前空間を
共有する検知器で昇格を捉えられることを確認した。**Falco 自体の発火確認は、eBPF が
使える Linux ホストで行う**（macOS の Docker Desktop では VM 側の準備が要る）。

## まとめ

- 防御はイメージが保証する。**検知・通知・ログ保全はホスト側で用意する**。
- Kimigayo は正常時にシェルも root も出ないので、ルールを厳しくしても誤検知が少ない。
- ログは即座にコンテナ外・ホスト外へ。root を取られても過去のログは消せない形にする。

# サーバーメンテナンス手順（Kimigayo コンテナの運用）

**本番で動いている Kimigayo コンテナを、昇格を塞いだまま安全にメンテナンスする手順。**

Kimigayo は「侵入されても root を奪取できない」運用ができる（下の「実行プロファイル」）。
このとき**メンテナンスのために昇格を解く必要はない。** root 作業はコンテナの外
（ホスト）から行う。この文書はその手順。

関連: [HARDENING_GUIDE.md](../security/HARDENING_GUIDE.md)（強化の全体）・
[RUNTIME_DETECTION.md](../security/RUNTIME_DETECTION.md)（破られたときの検知）。

---

## 前提: 昇格を塞ぐのは「実行時フラグ」。イメージは 1 つ

`no-new-privileges` / `--cap-drop` / `--user` は **`docker run`（実行時）** で指定する。
イメージに焼き込むものではない。**同じイメージ 1 つで、昇格不可でも root でも動かせる。**
2 種類ビルドしない。

実測（2026-10-16、setuid バイナリを足した脆弱イメージで確認）:

| 実行フラグ | コンテナ内から setuid で昇格 |
| --- | --- |
| 無し | `uid=0(root)` ← 奪取できてしまう |
| `--security-opt no-new-privileges --cap-drop ALL` | `uid=65534` のまま ← **奪取できない** |

決め手は **`no-new-privileges`**。カーネルに「この先 setuid などで権限を上げるな」と
命じるので、setuid バイナリがあっても昇格できない。

---

## 実行プロファイル（3 つ）

### 1. 通常（推奨・昇格不可）

**侵入されても root を取れない。既定はこれを使う。**

```bash
docker run -d --name app \
  --user 65532:65532 \
  --cap-drop ALL \
  --security-opt no-new-privileges \
  --read-only --tmpfs /tmp:rw,noexec,nosuid \
  -p 127.0.0.1:8080:8080 \
  ishinokazuki/kimigayo-os:<tag>
```

- `--user` は非 root。1024 未満のポートは待ち受けられないので、アプリは 8080 等にして
  `-p` で公開する。
- 詳細は [HARDENING_GUIDE.md](../security/HARDENING_GUIDE.md)。

### 2. root が要るサービス（必要な分だけ開ける）

`:80` を直接 bind する等、どうしても特権が要るサービスだけ、**必要な権限を 1 つずつ**渡す。
`--privileged` や無条件の root は使わない。

```bash
# 例: 80 番を bind したいだけなら NET_BIND_SERVICE だけ渡す（root にはしない）
docker run -d --name web \
  --user 65532:65532 \
  --cap-drop ALL --cap-add NET_BIND_SERVICE \
  --security-opt no-new-privileges \
  -p 80:80 \
  ishinokazuki/kimigayo-os:<tag>
```

本当に実行時 root が要る場合だけ `--user 0`。**その 1 コンテナだけの判断**で、
イメージを変えるわけではない。

### 3. メンテナンス（ホストから root で入る）

→ 下の「メンテナンス作業」。**コンテナの強化を解かずに** root 作業ができる。

---

## メンテナンス作業

**コンテナは使い捨て（不変）。** 走っているコンテナを中から直さない。やり方は 3 つ。

### A. パッチ・更新 → 新しいイメージに入れ替える（基本）

Kimigayo はパッケージマネージャーを持たない。更新は**新しいイメージをビルドして
差し替える**（イメージの中で `apk upgrade` のような手当てはしない）。

ローリングで入れ替える（流入を止めてから差し替える）:

```bash
# 1) 新しい版を用意
docker pull ishinokazuki/kimigayo-os:<new-tag>   # または自分でビルド

# 2) 流入を止める（LB / リバースプロキシで 503 を返す等）
#    直接公開なら新コンテナを別ポートで立ててから切り替える

# 3) 新コンテナを立てる（プロファイル 1 のフラグで）
docker run -d --name app-new --user 65532:65532 --cap-drop ALL \
  --security-opt no-new-privileges -p 127.0.0.1:8081:8080 ishinokazuki/kimigayo-os:<new-tag>

# 4) 疎通を確認して切り替え、古いコンテナを捨てる
docker rm -f app && docker rename app-new app
```

> 「停止して root フラグを付けて再起動してメンテ」は不要。コンテナでは
> **「新しいイメージに入れ替える」**がメンテナンス。昇格を一時的に解く必要はない。

### B. 調査・ファイルの確認 → ホストから `docker exec --user 0`

**強化したコンテナ（プロファイル 1）でも、ホストからは root で入れる。**
`docker exec --user 0` はホストの Docker デーモンが root プロセスを作るので、
コンテナ内の `no-new-privileges` に縛られない。攻撃者はコンテナの中にいるので
昇格できず、運用者はホスト側にいるので root になれる。

```bash
docker exec --user 0 app sh        # root で入って調査
docker exec --user 0 app cat /etc/shadow   # root 専用ファイルも読める（実測で確認）
```

実測（2026-10-16）: `no-new-privileges --cap-drop ALL --user 65534` のコンテナに対し、
コンテナ内からの昇格は失敗、ホストからの `docker exec --user 0` は `uid=0` で成功した。

> `docker exec` で入った root は、コンテナの capability 集合（ALL drop）を継ぐので、
> ファイルの読み書きはできても特権操作は制限される。もっと強い権限が要るなら C。

### C. 強い権限が要るデバッグ → 特権サイドカー

対象コンテナの名前空間を共有する特権コンテナを**別に**立てて調べる。**対象は
強化したまま**で、ツールも対象イメージに入れない（攻撃面を増やさない）。

```bash
docker run --rm -it \
  --pid container:app --network container:app \
  --privileged \
  nicolaka/netshoot        # 調査ツール入りの使い捨てイメージ
# 対象のプロセス・ネットワークが見える。strace / tcpdump などはここで使う
```

---

## まとめ

- 昇格を塞ぐのは実行時フラグ。**同じイメージで通常運用も root サービスもメンテもできる。**
- **メンテのために昇格を解かない。** 更新は新イメージに入れ替え、root 作業は
  ホストから（`docker exec --user 0` / 特権サイドカー）。
- root が要るサービスは、そのコンテナだけ必要な capability を渡す（`--privileged` にしない）。
- 破られたときに気づく仕組みは [RUNTIME_DETECTION.md](../security/RUNTIME_DETECTION.md)。

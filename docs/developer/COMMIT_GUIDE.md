# コミットメッセージガイド

**日本語で書き、先頭に絵文字を1つ置く。`feat:` のようなテキスト
プレフィックスは付けない。**

作業ルールの正本は [CLAUDE.md](../../CLAUDE.md) の「Git の運用ルール」です。
ここはその補足（例とツール）です。

> 2026-10-11 までこのファイルは Conventional Commits（`✨ feat: ...`）を
> 推奨していましたが、**実態と違っていました**。
> このリポジトリの 723 コミット（2026-10-12 時点）のうち、
> テキストプレフィックスが付いているのは 1 件だけです。

---

## フォーマット

```
<絵文字> <何をしたか>

<なぜそうしたか>
```

- **件名に「何をしたか」、本文に「なぜ」。** 何を変えたかは `git diff` で
  分かるので、本文は理由に使う
- 絵文字は**先頭に1つだけ**。`✨ feat: ...` のように併記しない
- 1 コミット 1 目的。複数の修正をまとめない
  （→ CLAUDE.md「コミットの粒度は細かいほどよい」）

## 絵文字の一覧

| 種類 | 絵文字 | | 種類 | 絵文字 |
| --- | --- | --- | --- | --- |
| 機能追加 | ✨ | | リファクタ | ♻️ |
| バグ修正 | 🐛 | | テスト | ✅ |
| ドキュメント・記録 | 📝 | | 取り消し | ⏪ |
| 雑務・設定 | 🔧 | | マージ | 🔀 |
| 性能改善 | ⚡ | | 統計・計測の保存 | 📊 |
| 依存・バージョン更新 | ⬆️ | | 片付け・削除 | 🧹 |
| Docker 関連 | 🐳 | | セキュリティ | 🔒 |

**どれにも当てはまらないものは 📌。**

## 実例（このリポジトリの実際のコミット）

```bash
git commit -m "🔒 dpkg / rpm がイメージに入っていた

SPECIFICATION.md 2.2 / 3.5 は「パッケージマネージャーを意図的に排除」と
書いているが、公開イメージには /bin/dpkg が入っており、実際に
\`dpkg -i\` でパッケージをインストールできた。

原因は config の書き忘れ。BusyBox の archival/Config.in は
DPKG を default y にしており、書いていない項目には既定値が入る。"
```

```bash
git commit -m "🐛 比較ベンチマークが既定で v2.0.1 のイメージを引いていた"
git commit -m "🧹 Kimigayo では絶対に動かない init スクリプト9本を落とす"
git commit -m "📊 起動時間・メモリ・コマンド性能を実測して「未測定」を消す"
git commit -m "🧹 カーネル 6.18 で不要になったパッチ3本を削除する"
```

**避ける形:**

```bash
git commit -m "✨ feat: 新機能を追加"          # テキストプレフィックスは付けない
git commit -m "✨ 新機能追加とバグ修正"         # 1 コミット 1 目的
git commit -m "🐛 修正"                        # 何を直したか分からない
```

## CHANGELOG

**[CHANGELOG.md](../../CHANGELOG.md) は手で書きます。**
コミットの件名は「何を変えたか」しか持っていませんが、CHANGELOG には
「なぜ」と「利用者への影響」が必要です。

```bash
make changelog     # build/CHANGELOG.generated.md に下書きを出す
```

**このコマンドは `CHANGELOG.md` を書き換えません。** 下書きを `build/` に
出すだけです（2026-10-11 までは `cat > CHANGELOG.md` で丸ごと上書きする
作りで、手で書いた内容が消える状態でした）。使える行をコピーして、
理由を足してください。

分類先の無い絵文字（表にある ⏪ 🔀 📌 と、表に無い絵文字）のコミットは
`Uncategorized` に入ります。黙って落とさないためです（以前は7種類しか分類できず、
🧹 📊 🔧 ⚡ ⬆️ 🐳 ✅ のコミットが消えていました）。

> **Dependabot の PR は形式が違います。** `.github/dependabot.yml` が
> `prefix: "⬆️"`（Docker は `🐳`）と `include: "scope"` を指定しているため、
> `⬆️(deps): Bump ...` のような件名になります。テキストの scope が付く点で
> 上の規則とは食い違っています（扱いは決めていません）。
> CHANGELOG の下書きでは先頭の絵文字で分類されるので、`⬆️` は `Changed`、
> `🐳` は `Build/CI` に入ります。

## 間違えたとき

```bash
git commit --amend -m "📝 正しいメッセージ"
```

**push 済みのものは直さない**（履歴の改変になる）。

**push が non-fast-forward で弾かれたら `rebase` ではなく `merge`。**
`git rebase origin/main` は自分のコミットのハッシュを書き換えます。

```bash
git pull origin main        # または git merge origin/main
git push origin main
```

## コミットテンプレート

リポジトリの中に置くと未追跡ファイルになる（`.gitignore` の対象外）ので、
ホームディレクトリに置きます。

```bash
cat > ~/.gitmessage <<'EOF'
# <絵文字> <何をしたか>
#
# <なぜそうしたか>
#
# 絵文字: ✨ 機能追加 / 🐛 バグ修正 / 🔒 セキュリティ / 📝 ドキュメント
#         🔧 雑務 / 🧹 削除 / ♻️ リファクタ / ✅ テスト / ⚡ 性能
#         ⬆️ 依存更新 / 🐳 Docker / 📊 計測 / ⏪ 取り消し / 📌 その他
EOF

git config commit.template ~/.gitmessage
```

## 参考資料

- [Keep a Changelog](https://keepachangelog.com/)
- [Semantic Versioning](https://semver.org/)
- [Gitmoji](https://gitmoji.dev/)

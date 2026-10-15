# メンテナーのアカウントを守る

Kimigayo のリポジトリには、管理者の権限を奪われたときにそれを止める仕組みが
**リポジトリの中には無い**。管理者は `gh pr merge --admin` で merge でき、
ルールセットも書き換えられる。だから守るのはリポジトリの外、
**メンテナーの GitHub アカウントと手元のトークン**になる。

Dependabot の PR を自動 merge にせず、手元の
`scripts/merge-dependabot-prs.sh` で merge しているのも同じ考え方で、
管理者より弱い権限（書き込みだけのトークン・乗っ取られた Action）から
main に届く経路をリポジトリに置かないため。

---

## gh のトークンは OS の保管庫に置く

**`GITHUB_TOKEN` / `GH_TOKEN` をシェルの設定ファイル（`.zshrc` など）に
書かない。** そこに書いたトークンは平文でバックアップや dotfiles の同期に
乗り、環境変数として起動したすべてのプログラムに渡る。
`repo` スコープのクラシックトークンは、自分のリポジトリでは管理者と
同じことができる。

`gh auth login` でログインすると、トークンは OS の保管庫に入る。

| 環境 | 保存先 |
| --- | --- |
| macOS | キーチェーン |
| Windows | 資格情報マネージャー |
| Linux（デスクトップ） | Secret Service（GNOME キーリング・KWallet） |
| Linux（画面の無いサーバー・コンテナ） | 保管庫が無く `~/.config/gh/hosts.yml` に平文で残る（`gh` が警告を出す） |

ログインは端末ごとに別のトークンになる。1 台をなくしても、
<https://github.com/settings/applications> からその端末の分だけ取り消せる。
GitHub Actions はワークフローごとに発行されるトークンを使うので、
手元の設定を変えても CI には影響しない。

### 環境変数のトークンから切り替える手順

1. 環境変数を使っているかを確かめる

   ```bash
   gh auth status
   # "(GITHUB_TOKEN)" や "(GH_TOKEN)" と出たら環境変数のトークンが使われている
   # "(keyring)" なら OS の保管庫
   grep -nE 'GITHUB_TOKEN|GH_TOKEN' ~/.zshrc ~/.zshenv ~/.zprofile ~/.bashrc ~/.bash_profile ~/.profile 2>/dev/null
   ```

2. 見つかった `export GITHUB_TOKEN=...` の行を消し、ターミナルを開き直す
3. 保管庫のログインがあるか確かめる。無ければログインする

   ```bash
   gh auth status            # "(keyring)" の行が Active になっていること
   gh auth login             # 無ければ（GitHub.com / SSH / ブラウザで認証）
   ```

4. いつもの操作が通るか確かめる

   ```bash
   gh pr list --repo Kazuki-0731/Kimigayo
   ```

5. 消した行のトークンを GitHub 側で取り消す
   （<https://github.com/settings/tokens>）。**ファイルから消しただけでは
   トークンは生きている。** バックアップに残っていれば使える

環境変数がどうしても要るときは、有効期限つきで、対象のリポジトリだけに
絞った fine-grained トークン（<https://github.com/settings/personal-access-tokens>）
にする。

---

## 非公開の Project に書き込むトークン

`security.yml` と `dependency-review.yml` は、見つけた脆弱性を公開の Issue ではなく
非公開の Project に足す（CLAUDE.md「危険度の高いものは Issue にしない」節）。
ワークフローの `GITHUB_TOKEN` は個人の Project に届かないので、専用のトークンを
シークレット `KIMIGAYO_PROJECT_TOKEN` に置いている。足す先の Project は
リポジトリの変数 `KIMIGAYO_PROJECT_ID`。

- **クラシックトークンで、スコープは `project` だけ。** fine-grained トークンは
  個人の Project を扱えない。`repo` などを足さない（漏れたときに届く範囲を
  Project だけにする）
- **有効期限を付け、切れる前に作り直す。** 切れると Project に足せず、
  `security.yml` の失敗が Discord に届く
- 作り直したら `gh secret set KIMIGAYO_PROJECT_TOKEN --repo Kazuki-0731/Kimigayo`
  （値は対話で入力し、コマンドラインに書かない）

## ブラウザで見る項目（API では確かめられない）

半年に 1 回、またはトークンや端末をなくしたときに見る。

| 何を | どこで | 見ること |
| --- | --- | --- |
| 2 段階認証・パスキー | <https://github.com/settings/security> | 有効か。リカバリーコードを保管しているか |
| ログイン中のセッション | <https://github.com/settings/sessions> | 心当たりの無い端末が無いか |
| クラシックトークン | <https://github.com/settings/tokens> | 使っていないもの・期限の無いものが無いか |
| fine-grained トークン | <https://github.com/settings/personal-access-tokens> | 同上 |
| 連携を許可したアプリ | <https://github.com/settings/applications> | 使っていないアプリ・端末が無いか |
| SSH キー | <https://github.com/settings/keys> | 使っていない鍵が無いか |

## API で確かめられる項目

```bash
R=Kazuki-0731/Kimigayo
gh api "repos/$R/collaborators" --jq '.[] | "\(.login) \(.role_name)"'   # 管理者が自分だけか
gh api "repos/$R/invitations"   --jq '.[].invitee.login'                  # 招待中の人がいないか
gh api "repos/$R/keys"          --jq '.[].title'                          # デプロイキー
gh api "repos/$R/hooks"         --jq '.[].config.url'                     # Webhook
gh api "repos/$R/actions/secrets" --jq '.secrets[].name'                  # シークレット（名前だけ）
gh api "repos/$R/rulesets" --jq '.[].id' | while read -r id; do
  gh api "repos/$R/rulesets/$id" --jq '"\(.name): \(.bypass_actors)"'     # ルールセットを迂回できるのは誰か
done
gh api "repos/$R/actions/permissions/workflow"                            # ワークフローの既定のトークン
```

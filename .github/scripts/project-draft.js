// 非公開の Project に下書きの項目を足す（actions/github-script から require する）。
//
// 出荷物に当たっていて、まだ直っていない脆弱性を公開の Issue に書くと、攻撃の
// 手がかりを渡すことになる（CLAUDE.md「危険度の高いものは Issue にしない」節）。
// upstream-security-watch.yml と published-image-cve-scan.yml は、見つけたものをここから Project に足す。
//
// github は Project を書き換えられるトークン（classic PAT の project スコープ）で
// 作ったものを渡す。ワークフローの GITHUB_TOKEN は個人の Project に届かない。
//
// 同じものを毎日足さないよう、下書きの本文に <!-- key:... --> を埋め、既にある
// key は飛ばす（呼ぶ側が seen で確かめる）。

const LOAD = `
query($id: ID!, $after: String) {
  node(id: $id) {
    ... on ProjectV2 {
      url
      fields(first: 50) {
        nodes { ... on ProjectV2SingleSelectField { id name options { id name } } }
      }
      items(first: 100, after: $after) {
        pageInfo { hasNextPage endCursor }
        nodes {
          content {
            ... on DraftIssue { body }
            ... on Issue { body }
          }
        }
      }
    }
  }
}`;

const ADD = `
mutation($project: ID!, $title: String!, $body: String) {
  addProjectV2DraftIssue(input: { projectId: $project, title: $title, body: $body }) {
    projectItem { id }
  }
}`;

const SET = `
mutation($project: ID!, $item: ID!, $field: ID!, $option: String!) {
  updateProjectV2ItemFieldValue(input: {
    projectId: $project, itemId: $item, fieldId: $field,
    value: { singleSelectOptionId: $option }
  }) { projectV2Item { id } }
}`;

// Project の URL・既にある key・Priority の項目を読む。
async function load(github, projectId) {
  if (!projectId) {
    throw new Error('KIMIGAYO_PROJECT_ID（リポジトリの変数）が設定されていない');
  }
  const seen = new Set();
  let url = '';
  let priority = null;
  let after = null;
  do {
    const res = await github.graphql(LOAD, { id: projectId, after });
    const p = res.node;
    if (!p) throw new Error(`Project ${projectId} が見つからない（トークンの project スコープを確認する）`);
    url = p.url;
    priority = priority || p.fields.nodes.find(f => f && f.name === 'Priority') || null;
    for (const n of p.items.nodes) {
      for (const m of ((n.content && n.content.body) || '').matchAll(/<!-- key:(\S+) -->/g)) seen.add(m[1]);
    }
    after = p.items.pageInfo.hasNextPage ? p.items.pageInfo.endCursor : null;
  } while (after);
  return { url, seen, priority };
}

// 下書きを 1 件足し、Priority（High / Middle / Low）を付ける。
async function add(github, projectId, state, { title, body, priority }) {
  const res = await github.graphql(ADD, { project: projectId, title, body });
  const item = res.addProjectV2DraftIssue.projectItem.id;
  const option = state.priority && state.priority.options.find(o => o.name === priority);
  if (option) {
    await github.graphql(SET, { project: projectId, item, field: state.priority.id, option: option.id });
  }
  return item;
}

module.exports = { load, add };

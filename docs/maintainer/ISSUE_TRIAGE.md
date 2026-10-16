# Issue Triage Process

**Last Updated:** 2026-10-12

---

## Overview

This document defines the issue triage process for Kimigayo OS to ensure efficient handling of bug reports, feature requests, and security issues.

The project currently has one maintainer. There is no separate maintainer team,
no project board and no priority labels; priority is decided case by case and
written in a comment.

---

## Triage Schedule

### Weekly Tasks (Monday)
- **Review new issues** opened in the past week
- **Respond to security reports** (GitHub Security Advisories) within the
  [SECURITY_POLICY.md](../security/SECURITY_POLICY.md) deadlines
- **Review open issues** for stale items
- **Close resolved issues**
- **Review automated security scan results** (issues labelled `セキュリティ` + `自動`)

### Monthly Tasks (First Monday)
- **Review issue backlog** and prioritize
- **Update issue templates** based on common patterns

---

## Labels

Only these 12 labels exist in the repository (2026-10-12). Use them; do not
assume any other label exists.

| Label | Used for |
|-------|----------|
| `バグ` | Something is broken |
| `機能追加` | New feature or improvement |
| `ドキュメント` | Documentation improvement or correction |
| `セキュリティ` | Security-related issue (vulnerabilities themselves go to Security Advisories) |
| `question` | User question or support |
| `good first issue` | Good for new contributors |
| `help wanted` | Community help needed |
| `duplicate` | Duplicate of another issue |
| `invalid` | Not a valid issue |
| `wontfix` | Won't be fixed (explain why) |
| `自動` | Created by a workflow |
| `依存` | Component / dependency updates |

> The issue templates apply only `バグ`, `ドキュメント`, `機能追加` and
> `セキュリティ`. There is no "needs triage" label, so untriaged issues are found
> by date, not by label (see "Tools and Resources").

---

## Issue Categories

### 🐛 Bugs

**Definition:** Something is broken or not working as intended

**Labels:** `バグ`

**Triage Checklist:**
- [ ] Severity assessed (data loss / security impact / broken feature / cosmetic)
- [ ] Reproducible steps verified
- [ ] Affected versions identified (`cat /etc/os-release`, image tag)
- [ ] Workaround documented (if available)

### 🚀 Feature Requests

**Definition:** New functionality or enhancement

**Labels:** `機能追加`

**Triage Checklist:**
- [ ] Use case validated
- [ ] Checked against the requirements in README.md ("Distroless + Alpine"
      design: no package manager, rootfs-only Docker image, VPS Docker use)
- [ ] Breaking changes identified
- [ ] Implementation complexity estimated

### 📚 Documentation

**Definition:** Documentation improvements or corrections

**Labels:**
- `ドキュメント`
- `good first issue` (simple doc fixes)

**Triage Checklist:**
- [ ] Documentation gap identified
- [ ] Affected docs listed
- [ ] Complexity assessed

### 🔒 Security

**Definition:** Security vulnerability or security-related issue

**Labels:** `セキュリティ`

**Special Handling:**
- **Vulnerabilities:** must be reported privately via GitHub Security
  Advisories (the only channel; there is no email address). If one is posted as
  a public issue, ask the reporter to use an advisory and hide the details
- **Deadlines:** as in [SECURITY_POLICY.md](../security/SECURITY_POLICY.md):
  acknowledge within 24 hours, initial assessment within 72 hours, fix by
  severity — Critical within 7 days, High within 30 days, Medium within
  90 days, Low in the next release
- **Disclosure:** advisory published together with the fixed release

**Triage Checklist:**
- [ ] Severity assessed (CVSS score)
- [ ] Affected versions identified
- [ ] Exploitation difficulty assessed
- [ ] Fix timeline established
- [ ] Security advisory created (if needed)

### ❓ Questions

**Definition:** User needs help or clarification

**Labels:** `question`

**Triage Checklist:**
- [ ] Check if documentation exists
- [ ] Link to relevant docs
- [ ] Consider moving to GitHub Discussions
- [ ] Close after resolution

---

## Triage Workflow

```
New Issue Created
    ↓
1. Initial Assessment
   - Read issue description
   - Check for duplicates
   - Assess completeness (ask for info if needed)
    ↓
2. Categorization
   - Apply one of the existing labels
   - Decide priority and say it in a comment
    ↓
3. Validation
   - Reproduce bugs
   - Validate use cases against the requirements
   - Assess security impact
    ↓
4. Response
   - Thank reporter
   - Provide initial feedback
   - Set expectations
```

---

## Response Templates

### Bug Report Response

```markdown
Thank you for reporting this issue!

I've triaged this as a **[severity]** bug affecting **[component]**.

**Next Steps:**
- [ ] Reproduce the issue
- [ ] Investigate root cause
- [ ] Develop fix
- [ ] Test fix
- [ ] Release patch

**Workaround:** [if available]

If you have additional information, please add it to this issue.
```

### Feature Request Response

```markdown
Thank you for the feature request!

**Use Case:** [summarize]
**Fits the design (no package manager, minimal rootfs image):** [yes/no, why]
**Complexity:** [low/medium/high]
**Breaking Changes:** [yes/no]

If others are interested in this feature, please 👍 the original post to help us prioritize.
```

### Security Issue Response

```markdown
Thank you for reporting this security issue.

Please continue in a **private security advisory**:
https://github.com/Kazuki-0731/Kimigayo/security/advisories/new

**Timeline (docs/security/SECURITY_POLICY.md):**
- Acknowledgement: within 24 hours
- Initial assessment: within 72 hours
- Fix: Critical within 7 days / High within 30 days / Medium within 90 days
- Public disclosure: together with the fixed release
```

### Needs Info Response

```markdown
Thank you for opening this issue!

To help us investigate, could you please provide:

- [ ] Kimigayo OS version (`cat /etc/os-release`) and image tag
- [ ] Architecture (`uname -m`)
- [ ] Steps to reproduce
- [ ] Expected behavior
- [ ] Actual behavior
- [ ] Relevant logs or error messages

This will help us identify the root cause faster.
```

---

## Stale Issue Management

There is no `stale` label and no automatic closing. An issue with no activity
for 90 days is reviewed by hand:

1. Comment:
   ```
   This issue has been inactive for 90 days.
   If there's no activity within 14 days, it will be closed.
   Please comment if this is still relevant.
   ```

2. **Wait 14 days** for response

3. **Close issue** if no response:
   ```
   Closing due to inactivity.
   Feel free to reopen if this is still an issue.
   ```

**Exceptions:**
- Security issues (never closed for inactivity)
- Feature requests with significant community interest

---

## Automated Issue Management

### Component Update Check

**Source:** `.github/workflows/upstream-security-watch.yml`

**Triggers:**
- Daily at 02:00 UTC
- On-demand via workflow_dispatch

**Creates Issues:** only when a newer musl or BusyBox release is found
(one issue, updated with a comment on later runs)

**Labels:** `セキュリティ`, `自動`, `依存`

### Weekly Security Scan

**Source:** `.github/workflows/published-image-cve-scan.yml`

**Triggers:**
- Weekly on Monday at 04:00 UTC (and manual runs)

**Creates no public issue.** When a **scheduled** run fails, for example because the
published `latest` image matches a CVE (`published-image-scan` →
`scripts/scan-image.sh`), `add-to-project` adds a draft item to the private Project

**Labels:** `セキュリティ`, `自動`
(the last one does not exist as a repository label)

**Handling (both):**
1. Review automated issue
2. Assess impact against [SECURITY_POLICY.md](../security/SECURITY_POLICY.md)
3. Fix or update the component (`version-bump` / `security-review` skills)
4. Update issue with the action taken

### Automated Base Image Updates

**Source:** `.github/workflows/component-update-pr.yml`

**Triggers:**
- Weekly on Monday at 03:00 UTC
- On-demand via workflow_dispatch

**Creates Pull Requests:**
- Component version updates (musl, BusyBox, OpenRC) in `versions.mk`
- The summary and a review checklist are in the PR body (no `UPDATES.md` is committed)
- Fails instead of opening a PR when a fetched version is empty, not a version,
  or not newer than the current one

**Labels:** `依存`, `自動`

**Handling:**
1. Review automated PR
2. Check the `on-push-and-pr-build-and-verify-all-images.yml` run on the PR branch — the PR is created with `GITHUB_TOKEN`,
   which does not trigger workflows, so the workflow starts `on-push-and-pr-build-and-verify-all-images.yml` itself
   via `workflow_dispatch` (the PR body links to the run)
3. Update checksums and verify patches (`version-bump` skill)
4. Merge if all checks pass
5. Update CHANGELOG.md / RELEASE_NOTES.md at the next release

---

## Tools and Resources

### GitHub CLI Commands

```bash
# Issues opened in the past week (GNU date; macOS: date -v-7d +%Y-%m-%d)
gh issue list --search "created:>$(date -d '7 days ago' +%Y-%m-%d)" --state open

# List security issues
gh issue list --label "security" --state open

# List stale issues (macOS: date -v-90d +%Y-%m-%d)
gh issue list --search "updated:<$(date -d '90 days ago' +%Y-%m-%d)" --state open

# Close stale issue
gh issue close <number> --comment "Closing due to inactivity"
```

Security advisories are created from the web UI
(Security → Advisories → New draft security advisory).

### Issue Templates

See `.github/ISSUE_TEMPLATE/` for:
- Bug report template
- Feature request template
- Security vulnerability template (points to private advisories)
- Documentation improvement template

---

## References

- [GitHub Issues documentation](https://docs.github.com/en/issues)
- [Alpine Linux Security Tracker](https://security.alpinelinux.org/)
- [Common Vulnerability Scoring System (CVSS)](https://www.first.org/cvss/)

---

**Maintainer:** Kimigayo OS maintainer
**Contact:** GitHub Issues or Discussions (security: GitHub Security Advisories)
**Last Review:** 2026-10-12

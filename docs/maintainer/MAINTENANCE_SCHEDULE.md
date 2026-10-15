# Maintenance Schedule

**Last Updated:** 2026-10-13

---

## Overview

This document defines the regular maintenance schedule for Kimigayo OS to ensure security, stability, and continuous improvement.

The project currently has one maintainer and a single branch (`main`).
The schedule below is what that maintainer aims for, not a staffed rota.

---

## Automated Workflows

### Daily Tasks

#### Security Update Check
- **Workflow:** `.github/workflows/security.yml`
- **Schedule:** Daily at 02:00 UTC
- **Actions:**
  - Check musl libc version updates
  - Check BusyBox version updates
  - Run Trivy filesystem scan (the repository, not the image) and upload SARIF
  - Create a GitHub issue (labels `security`, `automated`, `dependencies`) if a
    musl / BusyBox update is available

OpenRC and the kernel are not checked daily (OpenRC is checked weekly below;
the kernel is not built into the image).

**Manual Review Required:** If security issue is created

---

### Weekly Tasks

#### Base Image Update Check
- **Workflow:** `.github/workflows/base-image-update.yml`
- **Schedule:** Weekly on Monday at 03:00 UTC
- **Actions:**
  - Check component versions (musl, BusyBox, OpenRC)
  - Bump `versions.mk` and open a pull request (labels `dependencies`, `automated`)
    if updates are available. The summary and a review checklist are in the PR
    body (no `UPDATES.md` is committed). An empty, non-version or not-newer
    version fails the run instead of opening a PR
  - It does not build anything itself, but it starts `ci.yml` on the PR branch
    via `workflow_dispatch` (a PR created with `GITHUB_TOKEN` does not trigger
    workflows by itself)
  - `force_rebuild=true` on a manual run opens an empty-commit PR even without
    updates (to check the workflow itself)

**Manual Review Required:** Check the `ci.yml` run linked from the PR body,
update the checksums in `scripts/download-*.sh`, and follow the `version-bump`
skill before merging.

#### Dependabot
- **Config:** `.github/dependabot.yml`
- **Schedule:** Weekly on Monday at 03:00 UTC (GitHub Actions only)
- **Actions:** Open PRs for outdated actions (labels `dependencies`, `automated`;
  subject `⬆️ Bump ...`). Docker base images are not watched by Dependabot:
  `FROM alpine:${ALPINE_VERSION}` comes from `versions.mk`, which
  `base-image-update.yml` handles

**Manual Review Required:** Review and merge the PRs

#### Dependency Vulnerability Scan
- **Workflow:** `.github/workflows/dependency-review.yml`
- **Schedule:** Weekly on Monday at 04:00 UTC
- **Actions:**
  - Run filesystem vulnerability scan (`vulnerability-scan`)
  - Check build scripts for `http://` URLs and `eval` outside comments; any hit
    fails the job (only the `eval` in `scripts/lib/versions.sh` is allowed).
    Secrets are covered by Trivy and `scripts/scan-image.sh`, not by a grep
  - Upload scan results to Security tab
  - Pull the published image (`ishinokazuki/kimigayo-os:latest`) and match
    its shipped component versions against CVEs, plus scan it for secrets
    (`published-image-scan` → `scripts/scan-image.sh`)
  - Create a GitHub issue if a scheduled run fails (`create-security-issue`)

**Manual Review Required:** Review Security tab for findings, and the
issue / SBOM artifact (`sbom-published-latest`) if `published-image-scan` failed.
It failed on v3.0.1 (5 known CVEs in BusyBox 1.38.0 / musl 1.2.6). All 5 were
patched in v3.0.2, which replaced `latest` on 2026-10-12 — see
[SECURITY_AUDIT.md](../security/SECURITY_AUDIT.md). A new NVD entry can make
the scan fail again without any code change; that is a real signal.

#### Issue Triage
- **Schedule:** Every Monday
- **Actions:**
  - Review issues opened in the past week (see [ISSUE_TRIAGE.md](ISSUE_TRIAGE.md))
  - Label them with the existing labels
  - Respond to all issues opened in past week
  - Follow up on stale issues (90 days old)
  - Close resolved issues

---

### Monthly Tasks

#### First Monday of Month

##### Issue Backlog Review
- **Actions:**
  - Review open issues and their age
  - Identify patterns for template improvements
  - Update issue templates if needed

##### Documentation Review
- **Actions:**
  - Review documentation for accuracy against the repository
  - Check version numbers against `versions.mk` and `git describe --tags`
  - Check for broken links: `make check-links`

##### Release Review
- **Actions:**
  - List what changed since the last tag: `git log --oneline <last tag>..main`
  - Sort each change into major / minor / patch / not released, following
    [SPECIFICATION.md](../../SPECIFICATION.md) "10.2 バージョニングとリリースの方針"
  - If anything changes the published image, release it as one version
    (the largest category wins). CI, docs, scripts and kernel changes alone
    are not a reason to release

##### Security Audit
- **Actions:**
  - Review all security findings from past month
  - Verify all patches applied (`build/busybox-patches.log` and the musl patch step)
  - Match shipped components against CVEs: `make scan-image`
    (SBOM from the versions read out of the image + Grype)
  - Update `.github/SECURITY.md` / `docs/security/SECURITY_POLICY.md` if needed
  - Review access controls and permissions (repository, Docker Hub token)

---

### Quarterly Tasks

#### First Monday of Quarter (Jan/Apr/Jul/Oct)

##### Performance Benchmarking
- **Actions:**
  - Run the benchmark suite (`make benchmark`)
  - Compare with the previous values, recording host / arch / variant / version
  - Update README.md and `docs/benchmarks/` in the same change

##### Dependency Audit
- **Actions:**
  - Check upstream versions and EOL of the kernel, musl, BusyBox, OpenRC and Alpine
  - Plan upgrade path for major versions (`version-bump` skill)

##### Architecture Review
- **Actions:**
  - Review system architecture against SPECIFICATION.md
  - Identify technical debt
  - Update architecture documentation

---

## Manual Maintenance Tasks

### As Needed

#### Security Patches
- **Trigger:** CVE announcement affecting Kimigayo OS
- **Timeline:** the deadlines in
  [SECURITY_POLICY.md](../security/SECURITY_POLICY.md): acknowledge within
  24 hours, initial assessment within 72 hours, fix by severity —
  Critical within 7 days, High within 30 days, Medium within 90 days,
  Low in the next release
- **Process:**
  1. Assess impact and severity
  2. Create security advisory (private)
  3. Develop and test patch
  4. Release patch version
  5. Update security advisory (public)
  6. Announce to users

#### Bug Fixes
- **Trigger:** Bug reported (label `bug`)
- **Timeline:** no fixed SLA; security-relevant bugs follow the security
  deadlines above
- **Process:**
  1. Triage and reproduce
  2. Create fix (with a regression test where possible)
  3. Test fix
  4. Commit to `main`
  5. Release if needed

#### Release Preparation
- **Trigger:** the monthly Release Review, or an urgent fix (a Critical or
  CISA KEV CVE in the published image, or an image that does not start).
  When and which version: [SPECIFICATION.md](../../SPECIFICATION.md)
  "10.2 バージョニングとリリースの方針"
- **Process:** follow
  [.claude/skills/release/SKILL.md](../../.claude/skills/release/SKILL.md).
  In short: write CHANGELOG.md and RELEASE_NOTES.md by hand (`make changelog`
  only writes a draft to `build/CHANGELOG.generated.md`), run the quality
  checks, and get explicit approval before pushing a `v*.*.*` tag — the tag
  push makes `release.yml` replace the public images on Docker Hub, including
  `latest`. Running `release.yml` manually only builds, verifies and scans
  (it does not push to Docker Hub); publishing happens only on a tag push.

---

## Checklists

### Weekly Maintenance Checklist

```markdown
## Week of [DATE]

- [ ] Review automated security scan results (Security tab, open `security` issues)
- [ ] Review automated update PRs (base image update, Dependabot) and run CI on them
- [ ] Triage new issues from past week
- [ ] Follow up on stale issues
- [ ] Close resolved issues
- [ ] Review pull requests and Discussions
```

### Monthly Maintenance Checklist

```markdown
## Month of [MONTH YEAR]

- [ ] Issue backlog review
- [ ] Documentation review (`make check-links`)
- [ ] Security audit (`make scan-image`)
```

### Quarterly Maintenance Checklist

```markdown
## Quarter [Q# YEAR]

- [ ] Run benchmark suite and update the docs
- [ ] Dependency audit
- [ ] Architecture review
```

---

## Metrics Tracking

### Key Performance Indicators

| Metric | Target | Check Frequency |
|--------|--------|-----------------|
| Weekly published-image scan | Passing | Weekly |
| Security fix time | Within the SECURITY_POLICY.md deadlines (Critical 7 days / High 30 days / Medium 90 days) | As needed |
| Issue first response | < 1 week | Weekly |
| Open issue count | Tracked | Monthly |

---

## Escalation Procedures

### Security Emergency
1. **Immediate:** Create private security advisory
2. **Within 24 hours:** Acknowledge the reporter
3. **Within 72 hours:** Assess impact and severity
4. **By severity:** Release the fix and the public advisory within the
   SECURITY_POLICY.md deadline (Critical 7 days)

### Broken Release
1. **Immediate:** Open an issue labelled `bug` describing the affected tags
2. **As soon as possible:** Tell users to pin the previous version
   (for example `3.0.1-standard`) until a fix is released
3. **Then:** Release a fixed patch version

---

## Tools and Scripts

### Automated Maintenance Scripts

```bash
# Issues created in the past month
# (GNU date; on macOS use: date -v-1m +%Y-%m-%d)
gh issue list --json number,title,labels,createdAt,closedAt \
  --state all --search "created:>$(date -d '1 month ago' +%Y-%m-%d)" \
  > issues-report.json

# Check stale issues (macOS: date -v-90d +%Y-%m-%d)
gh issue list --search "updated:<$(date -d '90 days ago' +%Y-%m-%d)" --state open

# List security issues
gh issue list --label "security" --state open

# Check workflow runs
gh run list --limit 10

# View code scanning alerts
gh api repos/:owner/:repo/code-scanning/alerts
```

### Manual Maintenance Commands

```bash
# Update local repository
git pull origin main

# Outdated actions are reported by Dependabot (see above)

# View Docker Hub stats
# Use Docker Hub web interface

# Run local security scan
make trivy-fs-scan  # the repository
make scan-image     # CVE + secrets on kimigayo-os:$(VARIANT)-$(ARCH)
make security-scan  # scan-image + Trivy FS + ShellCheck

# Check build status
make status
```

---

## Contact and Escalation

### Maintainer
- There is no CODEOWNERS file; the single maintainer reviews everything
- **Backup:** GitHub Discussions or Issues

### Emergency Contact
- **Security:** Use GitHub Security Advisories (the only channel; there is no email address)
- **Critical Issues:** Create an issue with the `bug` label and say so in the title

### Community Support
- **Questions:** GitHub Discussions
- **Bug Reports:** GitHub Issues
- **Documentation:** GitHub Issues with `documentation` label

---

## References

- [Issue Triage Process](ISSUE_TRIAGE.md)
- [Security Policy](../security/SECURITY_POLICY.md)
- [Contributing Guide](../../CONTRIBUTING.md)
- [Release Process](../../.claude/skills/release/SKILL.md)
- [Release Notes](../../RELEASE_NOTES.md)

---

**Maintainer:** Kimigayo OS maintainer
**Last Review:** 2026-10-12

# Issue Triage Process

**Last Updated:** 2025-12-22
**Version:** 1.0.0

---

## Overview

This document defines the issue triage process for Kimigayo OS to ensure efficient handling of bug reports, feature requests, and security issues.

---

## Triage Schedule

### Daily Tasks
- **Review new issues** (unassigned, unlabeled)
- **Respond to security issues** (within 24 hours)
- **Update critical bug status**

### Weekly Tasks (Monday)
- **Review open issues** for stale items
- **Update milestone assignments**
- **Close resolved issues**
- **Review automated security scan results**

### Monthly Tasks (First Monday)
- **Review issue backlog** and prioritize
- **Update issue templates** based on common patterns
- **Analyze issue metrics** (time to response, time to resolution)

---

## Issue Categories

### 🐛 Bugs

**Definition:** Something is broken or not working as intended

**Priority Levels:**
- **P0 (Critical):** System crash, data loss, security vulnerability
- **P1 (High):** Major functionality broken, affects many users
- **P2 (Medium):** Minor functionality issue, workaround available
- **P3 (Low):** Cosmetic issue, minimal impact

**Labels:**
- `bug`
- `critical` (P0)
- `high-priority` (P1)
- `medium-priority` (P2)
- `low-priority` (P3)

**Triage Checklist:**
- [ ] Severity assessed
- [ ] Reproducible steps verified
- [ ] Affected versions identified
- [ ] Workaround documented (if available)
- [ ] Assigned to milestone

### 🚀 Feature Requests

**Definition:** New functionality or enhancement

**Priority Levels:**
- **P0 (Critical):** Blocking for next release
- **P1 (High):** Important for user experience
- **P2 (Medium):** Nice to have
- **P3 (Low):** Future consideration

**Labels:**
- `enhancement`
- `feature-request`
- `needs-discussion` (for complex features)

**Triage Checklist:**
- [ ] Use case validated
- [ ] Feasibility assessed
- [ ] Breaking changes identified
- [ ] Implementation complexity estimated
- [ ] Community interest gauged

### 📚 Documentation

**Definition:** Documentation improvements or corrections

**Labels:**
- `documentation`
- `good-first-issue` (simple doc fixes)

**Triage Checklist:**
- [ ] Documentation gap identified
- [ ] Affected docs listed
- [ ] Complexity assessed

### 🔒 Security

**Definition:** Security vulnerability or security-related issue

**Priority:** Always P0 (Critical)

**Labels:**
- `security`
- `vulnerability`

**Special Handling:**
- **Response time:** Within 24 hours
- **Private discussion:** Use GitHub Security Advisories for vulnerabilities
- **Disclosure:** Follow responsible disclosure process
- **Tracking:** Create private security advisory before public issue

**Triage Checklist:**
- [ ] Severity assessed (CVSS score)
- [ ] Affected versions identified
- [ ] Exploitation difficulty assessed
- [ ] Fix timeline established
- [ ] Security advisory created (if needed)

### ❓ Questions

**Definition:** User needs help or clarification

**Labels:**
- `question`
- `support`

**Triage Checklist:**
- [ ] Check if documentation exists
- [ ] Link to relevant docs
- [ ] Consider if FAQ entry needed
- [ ] Close after resolution

---

## Triage Workflow

```
New Issue Created
    ↓
┌───────────────────────────────────┐
│ 1. Initial Assessment (1 hour)    │
│    - Read issue description       │
│    - Check for duplicates         │
│    - Assess completeness          │
└───────────────────────────────────┘
    ↓
┌───────────────────────────────────┐
│ 2. Categorization (15 minutes)    │
│    - Assign type label            │
│    - Add relevant labels          │
│    - Set priority                 │
└───────────────────────────────────┘
    ↓
┌───────────────────────────────────┐
│ 3. Validation (varies)            │
│    - Reproduce bugs               │
│    - Validate use cases           │
│    - Assess security impact       │
└───────────────────────────────────┘
    ↓
┌───────────────────────────────────┐
│ 4. Assignment (30 minutes)        │
│    - Assign to milestone          │
│    - Assign to maintainer (if P0) │
│    - Add to project board         │
└───────────────────────────────────┘
    ↓
┌───────────────────────────────────┐
│ 5. Response (24 hours)            │
│    - Thank reporter               │
│    - Provide initial feedback     │
│    - Set expectations             │
└───────────────────────────────────┘
```

---

## Labeling Guide

### Priority Labels

| Label | Description | SLA Response | SLA Resolution |
|-------|-------------|--------------|----------------|
| `critical` | System broken, security issue | 1 hour | 24 hours |
| `high-priority` | Major functionality affected | 24 hours | 1 week |
| `medium-priority` | Minor issue, workaround exists | 3 days | 1 month |
| `low-priority` | Cosmetic or future consideration | 1 week | Next major version |

### Type Labels

- `bug` - Something is broken
- `enhancement` - Improve existing functionality
- `feature-request` - New functionality
- `documentation` - Documentation improvement
- `security` - Security-related issue
- `question` - User question or support
- `performance` - Performance-related issue

### Status Labels

- `needs-triage` - Awaiting initial triage
- `needs-info` - More information needed from reporter
- `needs-discussion` - Requires team discussion
- `in-progress` - Actively being worked on
- `blocked` - Blocked by external dependency
- `ready-for-review` - PR ready for review

### Component Labels

- `core` - Core OS functionality
- `package-manager` - isn package manager
- `init-system` - OpenRC/init system
- `networking` - Network-related
- `security-hardening` - Security features
- `build-system` - Build scripts/process
- `ci-cd` - CI/CD pipeline

### Special Labels

- `good-first-issue` - Good for new contributors
- `help-wanted` - Community help needed
- `wontfix` - Won't be fixed (explain why)
- `duplicate` - Duplicate of another issue
- `invalid` - Not a valid issue
- `automated` - Created by automation

---

## Response Templates

### Bug Report Response

```markdown
Thank you for reporting this issue!

I've triaged this as a **[priority]** bug affecting **[component]**.

**Next Steps:**
- [ ] Reproduce the issue
- [ ] Investigate root cause
- [ ] Develop fix
- [ ] Test fix
- [ ] Release patch

**Timeline:** Expected resolution by [date]

**Workaround:** [if available]

If you have additional information, please add it to this issue.
```

### Feature Request Response

```markdown
Thank you for the feature request!

This is an interesting idea. Let me break down the considerations:

**Use Case:** [summarize]
**Complexity:** [low/medium/high]
**Breaking Changes:** [yes/no]

I've added this to our **[milestone]** for further discussion.

**Community Feedback:**
If others are interested in this feature, please 👍 the original post to help us prioritize.
```

### Security Issue Response

```markdown
Thank you for reporting this security issue.

I've created a **private security advisory** to discuss this further.

**Immediate Actions:**
- [ ] Assess severity and impact
- [ ] Develop patch
- [ ] Test fix
- [ ] Coordinate disclosure

**Timeline:**
- Initial assessment: Within 24 hours
- Fix development: Within 1 week
- Public disclosure: After fix release

I'll keep you updated through the security advisory.
```

### Needs Info Response

```markdown
Thank you for opening this issue!

To help us investigate, could you please provide:

- [ ] Kimigayo OS version (`cat /etc/os-release`)
- [ ] Architecture (`uname -m`)
- [ ] Steps to reproduce
- [ ] Expected behavior
- [ ] Actual behavior
- [ ] Relevant logs or error messages

This will help us identify the root cause faster.
```

---

## Stale Issue Management

### Stale Issue Definition

An issue is considered stale if:
- No activity for **90 days** (low priority)
- No activity for **60 days** (medium priority)
- No activity for **30 days** (high priority, needs-info)

### Stale Issue Process

1. **Add `stale` label** and comment:
   ```
   This issue has been inactive for [X] days.
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
- Security issues (never auto-close)
- Feature requests with significant community interest (>10 👍)
- Issues in active milestones

---

## Automated Issue Management

### Automated Security Scans

**Source:** `.github/workflows/security-updates.yml`

**Triggers:**
- Daily at 02:00 UTC
- On-demand via workflow_dispatch

**Creates Issues:**
- Security updates available
- Dependency vulnerabilities found
- Component version updates needed

**Labels:** `security`, `automated`, `dependencies`

**Handling:**
1. Review automated issue
2. Assess impact and priority
3. Create tracking milestone if needed
4. Assign to maintainer
5. Update issue with action plan

### Automated Base Image Updates

**Source:** `.github/workflows/base-image-update.yml`

**Triggers:**
- Weekly on Monday at 03:00 UTC
- On-demand via workflow_dispatch

**Creates Pull Requests:**
- Component version updates (musl, BusyBox, etc.)
- Includes changelog and testing checklist

**Labels:** `dependencies`, `automated`, `base-image`

**Handling:**
1. Review automated PR
2. Run full test suite
3. Verify security scans pass
4. Merge if all checks pass
5. Update release notes

---

## Metrics and Monitoring

### Key Metrics

| Metric | Target | Current |
|--------|--------|---------|
| Time to first response | < 24 hours | - |
| Time to triage | < 3 days | - |
| Open issue count | < 50 | - |
| Stale issue rate | < 20% | - |
| Security issue resolution | < 7 days | - |

### Monthly Review

**First Monday of each month:**

1. **Generate report:**
   ```bash
   gh issue list --json number,title,labels,createdAt,closedAt \
     --state all --search "created:>$(date -d '1 month ago' +%Y-%m-%d)" \
     > issues-report.json
   ```

2. **Analyze:**
   - Total issues opened vs closed
   - Average time to response
   - Average time to resolution
   - Issue type distribution
   - Top contributors

3. **Improve:**
   - Update issue templates based on patterns
   - Adjust triage process if needed
   - Recognize top contributors

---

## Escalation Process

### When to Escalate

- Security vulnerability (CVSS > 7.0)
- Critical bug affecting production users
- Legal/compliance concerns
- Community conflict

### Escalation Path

1. **Level 1:** Maintainer team discussion (GitHub Discussions)
2. **Level 2:** Project lead decision (email)
3. **Level 3:** Security advisory for vulnerabilities

---

## Tools and Resources

### GitHub CLI Commands

```bash
# List new issues
gh issue list --label "needs-triage" --state open

# List security issues
gh issue list --label "security" --state open

# List stale issues
gh issue list --search "updated:<$(date -d '90 days ago' +%Y-%m-%d)" --state open

# Close stale issue
gh issue close <number> --comment "Closing due to inactivity"

# Create security advisory
gh api repos/:owner/:repo/security-advisories \
  -X POST -f summary="..." -f description="..."
```

### Issue Templates

See `.github/ISSUE_TEMPLATE/` for:
- Bug report template
- Feature request template
- Security vulnerability template
- Documentation improvement template

---

## References

- [GitHub Issue Triage Best Practices](https://docs.github.com/en/issues)
- [Alpine Linux Security Process](https://security.alpinelinux.org/)
- [Common Vulnerability Scoring System (CVSS)](https://www.first.org/cvss/)

---

**Maintainer:** Kimigayo OS Team
**Contact:** GitHub Issues or Discussions
**Last Review:** 2025-12-22

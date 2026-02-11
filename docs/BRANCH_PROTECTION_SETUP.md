# Branch Protection Setup Guide

This document explains how to configure GitHub branch protection rules to enforce the Three-Tier Promotion Strategy.

## 🎯 Overview

The Three-Tier Promotion Strategy ensures controlled, validated releases through three environments:

```
feat/*, fix/*, chore/*  →  develop  →  staging  →  main
     (Features)          (Alpha)     (Beta)    (Production)
```

## 🔒 Required Branch Protection Rules

Navigate to: **Repository Settings** → **Branches** → **Branch protection rules**

### 1. Protect `main` Branch

Click **Add rule** and configure:

**Branch name pattern:** `main`

**Protection Rules:**
- ✅ **Require a pull request before merging**
  - ✅ Require approvals: `1`
  - ✅ Dismiss stale pull request approvals when new commits are pushed
  - ✅ Require review from Code Owners (if you have CODEOWNERS file)
  - ✅ Require approval of the most recent reviewable push

- ✅ **Require status checks to pass before merging**
  - ✅ Require branches to be up to date before merging
  - **Required Status Checks:**
    - `Full Pipelane CI / lint`
    - `Full Pipelane CI / test`
    - `Full Pipelane CI / security`
    - `Full Pipelane CI / e2e`
    - `Full Pipelane CI / performance`
    - `Security Gate (PR Blocker) / dependency-review`
    - `Security Gate (PR Blocker) / secret-scan`
    - `Security Gate (PR Blocker) / codeql-analysis`
    - `Branch Protection Validator / validate-promotion-path`

- ✅ **Require conversation resolution before merging**

- ✅ **Require signed commits** (optional but recommended)

- ✅ **Require linear history** (enforces squash/rebase, no merge commits)

- ✅ **Include administrators** (admins must follow same rules)

- ✅ **Restrict who can push to matching branches**
  - Only: `github-actions[bot]` (for semantic-release)
  - No one else should have direct push access

### 2. Protect `staging` Branch

Click **Add rule** and configure:

**Branch name pattern:** `staging`

**Protection Rules:**
- ✅ **Require a pull request before merging**
  - ✅ Require approvals: `1`
  - ✅ Dismiss stale pull request approvals when new commits are pushed

- ✅ **Require status checks to pass before merging**
  - ✅ Require branches to be up to date before merging
  - **Required Status Checks:**
    - `Full Pipelane CI / lint`
    - `Full Pipelane CI / test`
    - `Full Pipelane CI / security`
    - `Full Pipelane CI / e2e`
    - `Full Pipelane CI / performance`
    - `Security Gate (PR Blocker) / dependency-review`
    - `Security Gate (PR Blocker) / secret-scan`
    - `Security Gate (PR Blocker) / codeql-analysis`
    - `Branch Protection Validator / validate-promotion-path`

- ✅ **Require conversation resolution before merging**

- ✅ **Require linear history**

- ✅ **Include administrators**

- ✅ **Restrict who can push to matching branches**
  - Only: `github-actions[bot]` (for semantic-release)

### 3. Protect `develop` Branch

Click **Add rule** and configure:

**Branch name pattern:** `develop`

**Protection Rules:**
- ✅ **Require a pull request before merging**
  - ✅ Require approvals: `1`
  - ✅ Dismiss stale pull request approvals when new commits are pushed

- ✅ **Require status checks to pass before merging**
  - ✅ Require branches to be up to date before merging
  - **Required Status Checks:**
    - `Baseline CI / commit-lint`
    - `Baseline CI / pr-title-lint`
    - `Baseline CI / lint`
    - `Baseline CI / test`
    - `Baseline CI / security`
    - `Security Gate (PR Blocker) / dependency-review`
    - `Security Gate (PR Blocker) / secret-scan`
    - `Security Gate (PR Blocker) / codeql-analysis`
    - `Branch Protection Validator / validate-promotion-path`

- ✅ **Require conversation resolution before merging**

- ✅ **Require linear history**

- ✅ **Include administrators**

- ✅ **Restrict who can push to matching branches**
  - Only: `github-actions[bot]` (for semantic-release)

## ⚙️ GitHub Actions Permissions

Navigate to: **Repository Settings** → **Actions** → **General**

### Workflow Permissions

- ✅ **Read and write permissions**
- ✅ **Allow GitHub Actions to create and approve pull requests**

This allows `semantic-release` to automatically create release PRs and tags.

## 🚫 What This Prevents

1. ❌ **Direct pushes to main/staging/develop** - Only PRs allowed
2. ❌ **develop → main** - Must go through staging first
3. ❌ **feat/* → staging or main** - Must go to develop first
4. ❌ **Merging without tests passing** - All status checks required
5. ❌ **Bypassing code review** - At least 1 approval required
6. ❌ **Merging without resolving comments** - Conversations must be resolved

## ✅ Allowed Workflows

### Feature Development
```bash
# 1. Create feature branch from develop
git checkout develop
git pull origin develop
git checkout -b feat/new-feature

# 2. Develop and commit
git add .
git commit -m "feat: add new feature"

# 3. Push and create PR to develop
git push origin feat/new-feature
gh pr create --base develop --title "feat: add new feature"

# 4. After review and CI passes, merge to develop (creates v1.0.0-alpha.1)
```

### Alpha → Beta Promotion
```bash
# 1. Create PR from develop to staging
gh pr create --base staging --head develop --title "chore: promote to beta"

# 2. After E2E/performance tests pass, merge to staging (creates v1.0.0-beta.1)
```

### Beta → Production Promotion
```bash
# 1. Create PR from staging to main
gh pr create --base main --head staging --title "chore: promote to production"

# 2. After final checks pass, merge to main (creates v1.0.0)
```

## 🔍 Verification

After setting up branch protection, verify:

1. Try direct push to `main`:
   ```bash
   git checkout main
   echo "test" > test.txt
   git add test.txt
   git commit -m "test"
   git push origin main
   # Should fail with: "protected branch hook declined"
   ```

2. Try invalid PR (feat/* → main):
   ```bash
   git checkout -b feat/invalid-pr
   gh pr create --base main --title "feat: invalid"
   # Branch Protection Validator should fail
   ```

3. Try valid PR (feat/* → develop):
   ```bash
   gh pr create --base develop --title "feat: valid"
   # Should pass after CI checks complete
   ```

## 📚 References

- [GitHub Protected Branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
- [Required Status Checks](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches#require-status-checks-before-merging)
- [Semantic Release Configuration](../pyproject.toml#L265)

## 🆘 Troubleshooting

### "Cannot merge - status checks required"
- Go to PR → Checks tab → Wait for all checks to complete
- Green checkmarks required before merge button activates

### "Semantic-release cannot push"
- Verify `github-actions[bot]` is in "Restrict who can push" list
- Check Actions permissions allow "create and approve pull requests"

### "PR title validation failed"
- PR title must follow format: `type: description`
- Valid types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`
- Example: `feat: add user authentication`

### "Wrong promotion path detected"
- PRs to `main` must come from `staging` only
- PRs to `staging` must come from `develop` only
- PRs to `develop` must come from `feat/`, `fix/`, or `chore/` branches only

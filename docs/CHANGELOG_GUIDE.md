# Changelog System Quick Start Guide

This guide explains how to use the automated changelog system for the Sunny TukTuk Management System.

## Overview

The changelog system automatically generates release notes from your git commits using the [Conventional Commits](https://www.conventionalcommits.org/) specification.

## Quick Commands

### View Available Commands
```bash
make help
```

### Check Current Status
```bash
make status
```

### Create a New Release
```bash
# Patch release (0.1.0 → 0.1.1)
make release-patch

# Minor release (0.1.0 → 0.2.0)  
make release-minor

# Major release (0.1.0 → 1.0.0)
make release-major

# Custom version
make release VERSION=0.1.1
```

## Writing Good Commits

### Commit Format
```
type(scope): description
```

### Examples
```bash
# New feature
git commit -m "feat(api): add new payment validation endpoint"

# Bug fix
git commit -m "fix(driver): resolve target calculation bug"

# Documentation
git commit -m "docs(readme): update installation instructions"

# Code refactoring
git commit -m "refactor(api): improve payment processing logic"

# Testing
git commit -m "test(api): add unit tests for payment validation"

# Maintenance
git commit -m "chore(deps): update frappe framework to 15.0.1"
```

### Allowed Types
- `feat` - New features
- `fix` - Bug fixes
- `docs` - Documentation changes
- `style` - Code style changes
- `refactor` - Code refactoring
- `test` - Test additions/changes
- `chore` - Maintenance tasks
- `perf` - Performance improvements
- `ci` - CI/CD changes
- `build` - Build system changes
- `revert` - Revert previous commits

### Scopes
Use scopes to categorize changes:
- `api` - API endpoints and business logic
- `driver` - Driver management features
- `vehicle` - Vehicle management features
- `payment` - Payment processing
- `ui` - User interface changes
- `db` - Database changes
- `config` - Configuration changes
- `test` - Test-related changes

## Validation

### Automatic Validation
The pre-commit hook automatically validates your commit messages:
```bash
# Setup git hooks (run once)
make setup-hooks
```

### Manual Validation
```bash
# Check last 10 commits
make validate-commits

# Check specific number of commits
python scripts/validate_commits.py --check-last 20

# Strict mode (exit on error)
python scripts/validate_commits.py --strict
```

## Changelog Generation

### Generate Changelog
```bash
# Generate for specific version
make changelog VERSION=0.1.1

# Preview without writing to file
make changelog-preview VERSION=0.1.1
```

### What Gets Included
- All conventional commits since the last tag
- Categorized by type (Added, Fixed, etc.)
- Scoped descriptions for better organization
- Automatic date stamping

### What Gets Excluded
- Merge commits
- Version bump commits
- Non-conventional commits (with warning)

## Version Management

### Bump Version
```bash
# Bump to specific version
make version-bump VERSION=0.1.1

# Auto-bump
make version-patch    # 0.1.0 → 0.1.1
make version-minor    # 0.1.0 → 0.2.0
make version-major    # 0.1.0 → 1.0.0
```

### Files Updated
- `pyproject.toml`
- `setup.py`
- `CHANGELOG.md`

## Release Process

### 1. Development
```bash
# Make your changes
git add .
git commit -m "feat(api): add new endpoint"
git commit -m "fix(driver): resolve bug"
```

### 2. Create Release
```bash
# Choose release type
make release-patch    # For bug fixes
make release-minor    # For new features
make release-major    # For breaking changes
```

### 3. Push to Remote
```bash
git push && git push --tags
```

## Troubleshooting

### Invalid Commit Message
If you get an error about invalid commit format:
```bash
# Amend the last commit
git commit --amend -m "feat(api): add new payment endpoint"

# Or reset and recommit
git reset --soft HEAD~1
git commit -m "feat(api): add new payment endpoint"
```

### No Commits Found
If changelog generation shows "No commits found":
```bash
# Check if you have commits since last tag
git log --oneline $(git describe --tags --abbrev=0)..HEAD

# Check if commits follow conventional format
make validate-commits
```

### Version Bump Issues
If version bumping fails:
```bash
# Check current version
grep 'version = ' pyproject.toml

# Manual version update
sed -i 's/version = ".*"/version = "0.1.1"/' pyproject.toml
sed -i "s/version='.*'/version='0.1.1'/" setup.py
```

## Best Practices

### 1. Write Clear Commit Messages
```bash
# Good
git commit -m "feat(api): add Mpesa payment validation endpoint"

# Bad
git commit -m "add payment stuff"
```

### 2. Use Appropriate Scopes
```bash
# Good - specific scope
git commit -m "fix(driver): resolve target calculation bug"

# Bad - too generic
git commit -m "fix: fix bug"
```

### 3. Keep Commits Focused
```bash
# Good - single change
git commit -m "feat(api): add payment validation"

# Bad - multiple changes
git commit -m "feat: add payment validation and fix driver bug and update docs"
```

### 4. Test Before Release
```bash
# Validate commits
make validate-commits

# Preview changelog
make changelog-preview VERSION=0.1.1

# Check status
make status
```

## Integration with CI/CD

### GitHub Actions Example
```yaml
name: Release
on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Generate Changelog
        run: |
          VERSION=${GITHUB_REF#refs/tags/v}
          make changelog VERSION=$VERSION
      - name: Create Release
        uses: actions/create-release@v1
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          tag_name: ${{ github.ref }}
          release_name: Release ${{ github.ref }}
          body_path: CHANGELOG.md
```

## Support

For issues with the changelog system:
1. Check this guide first
2. Run `make help` for available commands
3. Check the [Conventional Commits specification](https://www.conventionalcommits.org/)
4. Review `docs/VERSIONING.md` for detailed versioning strategy

---

This system makes it easy to maintain professional, consistent release notes automatically! 
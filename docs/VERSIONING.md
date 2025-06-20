# Versioning Strategy

This document outlines the versioning strategy for the Sunny TukTuk Management System.

## Semantic Versioning

We follow [Semantic Versioning](https://semver.org/) (SemVer) with the format `MAJOR.MINOR.PATCH`:

- **MAJOR** version for incompatible API changes
- **MINOR** version for backwards-compatible functionality additions  
- **PATCH** version for backwards-compatible bug fixes

### Version Number Examples

- `0.1.0` - Initial beta release
- `0.1.1` - Bug fix release
- `0.2.0` - New features added
- `1.0.0` - First stable release
- `1.0.1` - Critical bug fix
- `1.1.0` - New features in stable release

## Release Types

### Pre-release Versions

For development and testing phases:

- **Alpha**: `0.1.0-alpha.1` - Early development, breaking changes expected
- **Beta**: `0.1.0-beta.1` - Feature complete, testing phase
- **RC**: `0.1.0-rc.1` - Release candidate, final testing

### Stable Releases

- **Patch**: `0.1.1` - Bug fixes only
- **Minor**: `0.2.0` - New features, backwards compatible
- **Major**: `1.0.0` - Breaking changes

## Release Schedule

### Current Phase: Beta (0.x.x)

- **Patch releases**: As needed for critical bug fixes
- **Minor releases**: Monthly for new features
- **Major releases**: When breaking changes are necessary

### Stable Phase: Production (1.x.x)

- **Patch releases**: Weekly for critical fixes
- **Minor releases**: Quarterly for new features
- **Major releases**: Annually or when breaking changes are required

## Version Bumping Rules

### When to Bump PATCH (0.1.0 → 0.1.1)

- Bug fixes that don't add new functionality
- Documentation updates
- Code style changes
- Performance improvements
- Security patches

### When to Bump MINOR (0.1.0 → 0.2.0)

- New features added in a backwards-compatible manner
- New API endpoints
- New DocTypes or fields
- New configuration options
- Deprecation notices (but not removals)

### When to Bump MAJOR (0.1.0 → 1.0.0)

- Breaking changes to APIs
- Removal of deprecated features
- Changes to database schema that require migration
- Changes to configuration file formats
- Changes to authentication or security models

## Release Process

### 1. Development Phase

```bash
# Make changes and commit with conventional commits
git add .
git commit -m "feat(api): add new payment validation endpoint"
git commit -m "fix(driver): resolve target calculation bug"
```

### 2. Pre-release Testing

```bash
# Create alpha/beta/rc versions
make version-bump VERSION=0.1.0-alpha.1
make changelog VERSION=0.1.0-alpha.1
git tag -a v0.1.0-alpha.1 -m "Alpha release 0.1.0-alpha.1"
```

### 3. Release Creation

```bash
# For patch release
make release-patch

# For minor release  
make release-minor

# For major release
make release-major

# Or specify custom version
make release VERSION=0.1.1
```

### 4. Post-release

```bash
# Push to remote
git push && git push --tags

# Create GitHub release with changelog
# Update documentation
# Notify stakeholders
```

## Conventional Commits

All commits must follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

### Commit Types

- `feat`: A new feature
- `fix`: A bug fix
- `docs`: Documentation only changes
- `style`: Changes that do not affect the meaning of the code
- `refactor`: A code change that neither fixes a bug nor adds a feature
- `test`: Adding missing tests or correcting existing tests
- `chore`: Other changes that do not modify src or test files
- `perf`: A code change that improves performance
- `ci`: Changes to CI configuration files and scripts
- `build`: Changes that affect the build system or external dependencies
- `revert`: Reverts a previous commit

### Commit Format

```
type(scope): description

[optional body]

[optional footer(s)]
```

### Examples

```
feat(api): add Mpesa payment validation endpoint
fix(driver): resolve target calculation bug in daily reports
docs(readme): update installation instructions for ERPNext 15
chore(deps): update frappe framework to 15.0.1
test(api): add unit tests for payment processing
```

## Automated Tools

### Changelog Generation

The changelog is automatically generated from conventional commits:

```bash
# Generate changelog for new version
make changelog VERSION=0.1.1

# Preview changelog without writing to file
make changelog-preview VERSION=0.1.1
```

### Commit Validation

Commits are automatically validated to ensure they follow conventional format:

```bash
# Validate last 10 commits
make validate-commits

# Validate with strict mode (exit on error)
python scripts/validate_commits.py --strict
```

### Version Management

Version numbers are automatically updated across all files:

```bash
# Bump to specific version
make version-bump VERSION=0.1.1

# Auto-bump patch/minor/major
make version-patch
make version-minor  
make version-major
```

## Version Files

The following files contain version information and are automatically updated:

- `pyproject.toml` - Main version reference
- `setup.py` - Package version
- `CHANGELOG.md` - Release history
- `docs/VERSIONING.md` - This file

## Migration Strategy

### Database Migrations

- **Patch releases**: No database changes
- **Minor releases**: Additive changes only (new fields, new DocTypes)
- **Major releases**: May include breaking schema changes

### API Changes

- **Patch releases**: Bug fixes only
- **Minor releases**: New endpoints, optional parameters
- **Major releases**: Breaking changes, removed endpoints

### Configuration Changes

- **Patch releases**: No config changes
- **Minor releases**: New optional settings
- **Major releases**: Breaking config format changes

## Support Policy

### Version Support Timeline

- **Current version**: Full support
- **Previous minor version**: Security fixes only
- **Older versions**: No support

### Upgrade Path

- **Patch releases**: Direct upgrade
- **Minor releases**: Direct upgrade
- **Major releases**: May require migration steps

## Release Notes

Each release includes:

1. **Version number and date**
2. **Summary of changes**
3. **Breaking changes** (if any)
4. **New features**
5. **Bug fixes**
6. **Upgrade instructions**
7. **Known issues**

## Emergency Releases

For critical security or stability issues:

1. Create hotfix branch from latest stable
2. Apply minimal fix
3. Bump patch version
4. Create emergency release
5. Deploy immediately
6. Follow up with proper release process

## Version History

See [CHANGELOG.md](../CHANGELOG.md) for complete version history.

---

This versioning strategy ensures consistent, predictable releases and helps users understand the impact of updates. 
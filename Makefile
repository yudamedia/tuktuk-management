# Makefile for Sunny TukTuk Management System
# Provides easy commands for changelog management and releases

.PHONY: help changelog version-bump release install test clean

# Default target
help:
	@echo "Sunny TukTuk Management System - Development Commands"
	@echo "=================================================="
	@echo ""
	@echo "Changelog Management:"
	@echo "  changelog          - Generate changelog from git commits"
	@echo "  changelog-preview  - Preview changelog without writing to file"
	@echo ""
	@echo "Version Management:"
	@echo "  version-bump       - Bump version (use VERSION=0.1.1)"
	@echo "  version-patch      - Bump patch version (0.1.0 -> 0.1.1)"
	@echo "  version-minor      - Bump minor version (0.1.0 -> 0.2.0)"
	@echo "  version-major      - Bump major version (0.1.0 -> 1.0.0)"
	@echo ""
	@echo "Release Process:"
	@echo "  release           - Create a new release (use VERSION=0.1.1)"
	@echo "  release-patch     - Create patch release"
	@echo "  release-minor     - Create minor release"
	@echo "  release-major     - Create major release"
	@echo ""
	@echo "Development:"
	@echo "  install           - Install development dependencies"
	@echo "  test              - Run tests"
	@echo "  clean             - Clean build artifacts"
	@echo ""
	@echo "Examples:"
	@echo "  make version-bump VERSION=0.1.1"
	@echo "  make release VERSION=0.1.1"
	@echo "  make release-patch"

# Get current version from pyproject.toml
CURRENT_VERSION := $(shell grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')

# Changelog generation
changelog:
	@echo "Generating changelog..."
	@if [ -z "$(VERSION)" ]; then \
		echo "Error: VERSION is required. Use: make changelog VERSION=0.1.1"; \
		exit 1; \
	fi
	@python3 scripts/generate_changelog.py --version $(VERSION)

changelog-preview:
	@echo "Previewing changelog changes..."
	@if [ -z "$(VERSION)" ]; then \
		echo "Error: VERSION is required. Use: make changelog-preview VERSION=0.1.1"; \
		exit 1; \
	fi
	@python3 scripts/generate_changelog.py --version $(VERSION) --preview

# Version bumping
version-bump:
	@echo "Bumping version to $(VERSION)..."
	@if [ -z "$(VERSION)" ]; then \
		echo "Error: VERSION is required. Use: make version-bump VERSION=0.1.1"; \
		exit 1; \
	fi
	@sed -i 's/version = ".*"/version = "$(VERSION)"/' pyproject.toml
	@sed -i "s/version='.*'/version='$(VERSION)'/" setup.py
	@sed -i 's/current_version = ".*"/current_version = "$(VERSION)"/' pyproject.toml
	@echo "✅ Version bumped to $(VERSION)"

version-patch:
	@$(eval NEW_VERSION := $(shell echo $(CURRENT_VERSION) | awk -F. '{print $$1"."$$2"."$$3+1}'))
	@$(MAKE) version-bump VERSION=$(NEW_VERSION)

version-minor:
	@$(eval NEW_VERSION := $(shell echo $(CURRENT_VERSION) | awk -F. '{print $$1"."$$2+1".0"}'))
	@$(MAKE) version-bump VERSION=$(NEW_VERSION)

version-major:
	@$(eval NEW_VERSION := $(shell echo $(CURRENT_VERSION) | awk -F. '{print $$1+1".0.0"}'))
	@$(MAKE) version-bump VERSION=$(NEW_VERSION)

# Release process
release:
	@echo "Creating release $(VERSION)..."
	@if [ -z "$(VERSION)" ]; then \
		echo "Error: VERSION is required. Use: make release VERSION=0.1.1"; \
		exit 1; \
	fi
	@echo "1. Bumping version..."
	@$(MAKE) version-bump VERSION=$(VERSION)
	@echo "2. Generating changelog..."
	@$(MAKE) changelog VERSION=$(VERSION)
	@echo "3. Creating git tag..."
	@git add .
	@git commit -m "chore: release version $(VERSION)"
	@git tag -a v$(VERSION) -m "Release version $(VERSION)"
	@echo "✅ Release $(VERSION) created successfully!"
	@echo "📝 To push to remote: git push && git push --tags"

release-patch:
	@$(eval NEW_VERSION := $(shell echo $(CURRENT_VERSION) | awk -F. '{print $$1"."$$2"."$$3+1}'))
	@$(MAKE) release VERSION=$(NEW_VERSION)

release-minor:
	@$(eval NEW_VERSION := $(shell echo $(CURRENT_VERSION) | awk -F. '{print $$1"."$$2+1".0"}'))
	@$(MAKE) release VERSION=$(NEW_VERSION)

release-major:
	@$(eval NEW_VERSION := $(shell echo $(CURRENT_VERSION) | awk -F. '{print $$1+1".0.0"}'))
	@$(MAKE) release VERSION=$(NEW_VERSION)

# Development commands
install:
	@echo "Installing development dependencies..."
	@pip install -r requirements.txt
	@echo "✅ Dependencies installed"

test:
	@echo "Running tests..."
	@python3 -m pytest tests/ -v
	@echo "✅ Tests completed"

clean:
	@echo "Cleaning build artifacts..."
	@find . -type f -name "*.pyc" -delete
	@find . -type d -name "__pycache__" -delete
	@find . -type d -name "*.egg-info" -exec rm -rf {} +
	@echo "✅ Clean completed"

# Git hooks setup
setup-hooks:
	@echo "Setting up git hooks..."
	@mkdir -p .git/hooks
	@cp scripts/pre-commit .git/hooks/ || echo "No pre-commit hook found"
	@chmod +x .git/hooks/pre-commit || true
	@echo "✅ Git hooks setup completed"

# Show current status
status:
	@echo "Current version: $(CURRENT_VERSION)"
	@echo "Git status:"
	@git status --short
	@echo ""
	@echo "Recent commits:"
	@git log --oneline -5

# Validate conventional commits
validate-commits:
	@echo "Validating conventional commits..."
	@python3 scripts/validate_commits.py || echo "No commit validator found" 
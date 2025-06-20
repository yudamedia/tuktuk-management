#!/usr/bin/env python3
"""
Automated Changelog Generator for Sunny TukTuk Management System

This script generates changelog entries based on conventional commits
and updates the CHANGELOG.md file automatically.

Usage:
    python scripts/generate_changelog.py [--version VERSION] [--release-date DATE]
"""

import argparse
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

class ChangelogGenerator:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.changelog_file = project_root / "CHANGELOG.md"
        
    def get_git_tags(self) -> List[str]:
        """Get all git tags sorted by version"""
        try:
            result = subprocess.run(
                ["git", "tag", "--sort=-version:refname"],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            return result.stdout.strip().split('\n') if result.stdout.strip() else []
        except subprocess.CalledProcessError:
            return []
    
    def get_commits_since_tag(self, tag: str = None) -> List[Dict]:
        """Get commits since a specific tag or all commits if no tag provided"""
        try:
            if tag:
                cmd = ["git", "log", f"{tag}..HEAD", "--pretty=format:%H|%s|%b|%an|%ad", "--date=short"]
            else:
                cmd = ["git", "log", "--pretty=format:%H|%s|%b|%an|%ad", "--date=short"]
            
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)
            
            commits = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split('|', 4)
                    if len(parts) >= 5:
                        commits.append({
                            'hash': parts[0],
                            'subject': parts[1],
                            'body': parts[2],
                            'author': parts[3],
                            'date': parts[4]
                        })
            return commits
        except subprocess.CalledProcessError:
            return []
    
    def parse_conventional_commit(self, commit: Dict) -> Tuple[str, str, str]:
        """Parse conventional commit format"""
        subject = commit['subject']
        
        # Conventional commit pattern: type(scope): description
        pattern = r'^(\w+)(?:\(([\w\-]+)\))?:\s*(.+)$'
        match = re.match(pattern, subject)
        
        if match:
            commit_type = match.group(1)
            scope = match.group(2) or 'general'
            description = match.group(3)
            return commit_type, scope, description
        
        # Fallback for non-conventional commits
        return 'other', 'general', subject
    
    def categorize_commits(self, commits: List[Dict]) -> Dict[str, List[str]]:
        """Categorize commits by type"""
        categories = {
            'feat': [],
            'fix': [],
            'docs': [],
            'style': [],
            'refactor': [],
            'test': [],
            'chore': [],
            'perf': [],
            'ci': [],
            'build': [],
            'revert': [],
            'other': []
        }
        
        type_mapping = {
            'feat': 'Added',
            'fix': 'Fixed',
            'docs': 'Documentation',
            'style': 'Style',
            'refactor': 'Refactored',
            'test': 'Testing',
            'chore': 'Chores',
            'perf': 'Performance',
            'ci': 'CI/CD',
            'build': 'Build',
            'revert': 'Reverted',
            'other': 'Other'
        }
        
        for commit in commits:
            commit_type, scope, description = self.parse_conventional_commit(commit)
            
            # Skip merge commits and version bumps
            if any(skip in commit['subject'].lower() for skip in ['merge', 'version', 'bump']):
                continue
            
            # Format the entry
            entry = f"- **{scope}**: {description}"
            if commit_type in categories:
                categories[commit_type].append(entry)
            else:
                categories['other'].append(entry)
        
        # Convert to display format
        result = {}
        for commit_type, entries in categories.items():
            if entries:
                result[type_mapping.get(commit_type, commit_type.title())] = entries
        
        return result
    
    def generate_changelog_entry(self, version: str, release_date: str, categorized_commits: Dict[str, List[str]]) -> str:
        """Generate a changelog entry for a specific version"""
        entry = f"## [{version}] - {release_date}\n\n"
        
        for category, entries in categorized_commits.items():
            entry += f"### {category}\n"
            for item in entries:
                entry += f"{item}\n"
            entry += "\n"
        
        return entry
    
    def update_changelog(self, version: str, release_date: str = None):
        """Update the CHANGELOG.md file with new version entry"""
        if not release_date:
            release_date = datetime.now().strftime("%Y-%m-%d")
        
        # Get commits since last tag
        tags = self.get_git_tags()
        last_tag = tags[0] if tags else None
        
        commits = self.get_commits_since_tag(last_tag)
        if not commits:
            print("No new commits found since last tag")
            return
        
        categorized_commits = self.categorize_commits(commits)
        if not categorized_commits:
            print("No conventional commits found")
            return
        
        # Generate new entry
        new_entry = self.generate_changelog_entry(version, release_date, categorized_commits)
        
        # Read existing changelog
        if self.changelog_file.exists():
            with open(self.changelog_file, 'r') as f:
                content = f.read()
        else:
            content = "# Changelog\n\nAll notable changes to this project will be documented in this file.\n\n"
        
        # Insert new entry after the header
        lines = content.split('\n')
        insert_index = 0
        
        # Find where to insert (after initial header, before [Unreleased])
        for i, line in enumerate(lines):
            if line.startswith('## [Unreleased]'):
                insert_index = i
                break
            elif line.startswith('## [') and i > 0:
                insert_index = i
                break
        
        # Insert the new entry
        lines.insert(insert_index, '')
        lines.insert(insert_index, new_entry.rstrip())
        
        # Write back to file
        with open(self.changelog_file, 'w') as f:
            f.write('\n'.join(lines))
        
        print(f"✅ Changelog updated with version {version}")
        print(f"📝 Added {len(commits)} commits across {len(categorized_commits)} categories")

def main():
    parser = argparse.ArgumentParser(description='Generate changelog for TukTuk Management System')
    parser.add_argument('--version', required=True, help='Version number (e.g., 0.1.0)')
    parser.add_argument('--release-date', help='Release date (YYYY-MM-DD format)')
    parser.add_argument('--project-root', default='.', help='Project root directory')
    
    args = parser.parse_args()
    
    project_root = Path(args.project_root)
    if not project_root.exists():
        print(f"❌ Project root directory does not exist: {project_root}")
        sys.exit(1)
    
    generator = ChangelogGenerator(project_root)
    generator.update_changelog(args.version, args.release_date)

if __name__ == '__main__':
    main() 
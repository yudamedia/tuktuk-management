#!/usr/bin/env python3
"""
Commit Validator for Conventional Commits

This script validates that commits follow the conventional commit format
to ensure proper changelog generation.

Usage:
    python scripts/validate_commits.py [--check-last N]
"""

import argparse
import re
import subprocess
import sys
from typing import List, Tuple

class CommitValidator:
    def __init__(self):
        self.conventional_pattern = re.compile(
            r'^(feat|fix|docs|style|refactor|test|chore|perf|ci|build|revert)(\([\w\-]+\))?:\s+.+$'
        )
        
        # Allowed commit types
        self.allowed_types = {
            'feat': 'A new feature',
            'fix': 'A bug fix',
            'docs': 'Documentation only changes',
            'style': 'Changes that do not affect the meaning of the code',
            'refactor': 'A code change that neither fixes a bug nor adds a feature',
            'test': 'Adding missing tests or correcting existing tests',
            'chore': 'Other changes that do not modify src or test files',
            'perf': 'A code change that improves performance',
            'ci': 'Changes to CI configuration files and scripts',
            'build': 'Changes that affect the build system or external dependencies',
            'revert': 'Reverts a previous commit'
        }
    
    def get_commits(self, count: int = 10) -> List[Tuple[str, str]]:
        """Get the last N commits with their messages"""
        try:
            result = subprocess.run(
                ['git', 'log', f'-{count}', '--pretty=format:%H|%s'],
                capture_output=True,
                text=True
            )
            
            commits = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split('|', 1)
                    if len(parts) == 2:
                        commits.append((parts[0], parts[1]))
            return commits
        except subprocess.CalledProcessError:
            return []
    
    def validate_commit(self, commit_hash: str, message: str) -> Tuple[bool, str]:
        """Validate a single commit message"""
        # Skip merge commits
        if message.startswith('Merge'):
            return True, "Merge commit (skipped)"
        
        # Skip version bump commits
        if 'version' in message.lower() and 'bump' in message.lower():
            return True, "Version bump (skipped)"
        
        # Check conventional commit format
        if self.conventional_pattern.match(message):
            return True, "Valid conventional commit"
        else:
            return False, "Invalid format - should be: type(scope): description"
    
    def validate_commits(self, count: int = 10) -> List[Tuple[str, str, bool, str]]:
        """Validate the last N commits"""
        commits = self.get_commits(count)
        results = []
        
        for commit_hash, message in commits:
            is_valid, reason = self.validate_commit(commit_hash, message)
            results.append((commit_hash[:8], message, is_valid, reason))
        
        return results
    
    def print_results(self, results: List[Tuple[str, str, bool, str]]):
        """Print validation results"""
        print("Commit Validation Results")
        print("=" * 50)
        
        valid_count = 0
        invalid_count = 0
        
        for commit_hash, message, is_valid, reason in results:
            status = "✅" if is_valid else "❌"
            print(f"{status} {commit_hash}: {message}")
            if not is_valid:
                print(f"   └─ {reason}")
            print()
            
            if is_valid:
                valid_count += 1
            else:
                invalid_count += 1
        
        print("Summary:")
        print(f"✅ Valid commits: {valid_count}")
        print(f"❌ Invalid commits: {invalid_count}")
        print(f"📊 Total checked: {len(results)}")
        
        if invalid_count > 0:
            print("\n💡 Tips for conventional commits:")
            print("   Format: type(scope): description")
            print("   Types:", ", ".join(self.allowed_types.keys()))
            print("   Example: feat(api): add new payment endpoint")
            print("   Example: fix(driver): resolve target calculation bug")
        
        return invalid_count == 0

def main():
    parser = argparse.ArgumentParser(description='Validate conventional commits')
    parser.add_argument('--check-last', type=int, default=10, 
                       help='Number of recent commits to check (default: 10)')
    parser.add_argument('--strict', action='store_true',
                       help='Exit with error code if any commits are invalid')
    
    args = parser.parse_args()
    
    validator = CommitValidator()
    results = validator.validate_commits(args.check_last)
    all_valid = validator.print_results(results)
    
    if args.strict and not all_valid:
        sys.exit(1)

if __name__ == '__main__':
    main() 
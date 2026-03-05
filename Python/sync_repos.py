#!/usr/bin/env python3
"""
Universal sync script for TudoNum repositories.
Handles Dev -> Staging and Staging -> Production syncs with validation.

Improvements:
- Includes untracked (new) files in sync
- Cleans up empty directories after deletion
- Checks if target repo is dirty before overwriting
- Auto-detects package manager (bun/npm/yarn)
- Better error handling and safety checks

Usage:
    python3 sync_repos.py

The script will:
1. Ask which sync to perform (Dev->Staging or Staging->Production)
2. Check for uncommitted changes in target repo (safety check)
3. Pull latest changes from both repos
4. Identify differences (modified, new, deleted files) including untracked files
5. Copy changed files
6. Run build, lint, and type-check using detected package manager
7. Provide a summary
"""

from __future__ import annotations

import fnmatch
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Literal

# Repository paths (relative to script location)
SCRIPT_DIR = Path(__file__).parent.absolute()
DEV_REPO = SCRIPT_DIR / "TudoNum-WebApp-Dev"
STAGING_REPO = SCRIPT_DIR / "TudoNum-WebApp-Stagging"
PROD_REPO = SCRIPT_DIR / "TudoNumWebApp-Production"

# Branch names
DEV_BRANCH = "dev"
STAGING_BRANCH = "staging"
PROD_BRANCH = "main"

# Sync type
SyncType = Literal["dev-to-staging", "staging-to-production"]


class Colors:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_header(text: str) -> None:
    """Print a formatted header."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(60)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")


def print_success(text: str) -> None:
    """Print success message."""
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")


def print_error(text: str) -> None:
    """Print error message."""
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")


def print_warning(text: str) -> None:
    """Print warning message."""
    print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")


def print_info(text: str) -> None:
    """Print info message."""
    print(f"{Colors.OKCYAN}ℹ {text}{Colors.ENDC}")


def run_command(
    cmd: list[str],
    cwd: Path | None = None,
    check: bool = True,
    capture_output: bool = True
) -> tuple[int, str, str]:
    """
    Run a shell command and return (returncode, stdout, stderr).
    
    Args:
        cmd: Command to run as list of strings
        cwd: Working directory (None = current directory)
        check: If True, raise exception on non-zero return code
        capture_output: If True, capture stdout/stderr
    
    Returns:
        Tuple of (returncode, stdout, stderr)
    """
    try:
        result = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            capture_output=capture_output,
            text=True,
            check=False
        )
        if check and result.returncode != 0:
            raise RuntimeError(
                f"Command failed: {' '.join(cmd)}\n"
                f"Return code: {result.returncode}\n"
                f"Stderr: {result.stderr}"
            )
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        if check:
            raise
        return 1, "", str(e)


def run_git(repo: Path, args: list[str], check: bool = True) -> str:
    """Run git command in repo and return stdout."""
    returncode, stdout, stderr = run_command(
        ["git", "-C", str(repo), *args],
        check=check
    )
    if check and returncode != 0:
        raise RuntimeError(
            f"git command failed in {repo}: git {' '.join(args)}\n{stderr}".strip()
        )
    return stdout.strip()


def detect_package_manager(repo: Path) -> str:
    """Detect package manager based on lock files."""
    if (repo / "bun.lockb").exists() or (repo / "bun.lock").exists():
        return "bun"
    if (repo / "yarn.lock").exists():
        return "yarn"
    if (repo / "package-lock.json").exists():
        return "npm"
    # Default to bun if package.json exists (most likely for this project)
    if (repo / "package.json").exists():
        return "bun"
    return "npm"


def ensure_repo_exists(repo: Path, name: str) -> None:
    """Check if repository exists."""
    if not repo.exists():
        raise RuntimeError(f"{name} repository not found at {repo}")
    if not (repo / ".git").exists():
        raise RuntimeError(f"{repo} is not a git repository")


def is_repo_dirty(repo: Path) -> bool:
    """Check if repository has uncommitted changes."""
    # --porcelain prints nothing if clean
    output = run_git(repo, ["status", "--porcelain"], check=False)
    return bool(output.strip())


def pull_latest_changes(repo: Path, branch: str, name: str) -> None:
    """Pull latest changes from the specified branch."""
    print_info(f"Preparing {name} ({branch} branch)...")
    
    try:
        # Check current branch
        current_branch = run_git(repo, ["rev-parse", "--abbrev-ref", "HEAD"], check=False)
        
        # If we are on the wrong branch, try to switch
        if current_branch != branch:
            if is_repo_dirty(repo):
                print_warning(f"{name} is on '{current_branch}' and has uncommitted changes.")
                print_warning(f"Cannot automatically switch to '{branch}'. Skipping pull.")
                return
            
            print_info(f"Switching {name} to {branch}...")
            returncode, stdout, stderr = run_command(
                ["git", "-C", str(repo), "checkout", branch],
                check=False
            )
            if returncode != 0:
                # Try to create branch tracking remote
                returncode, stdout, stderr = run_command(
                    ["git", "-C", str(repo), "checkout", "-b", branch, f"origin/{branch}"],
                    check=False
                )
                if returncode != 0:
                    print_warning(f"Could not checkout {branch} branch: {stderr.strip()}")
                    return
        
        # Fetch and Pull
        print_info(f"Pulling from origin/{branch}...")
        returncode, stdout, stderr = run_command(
            ["git", "-C", str(repo), "pull", "origin", branch],
            check=False
        )
        
        if returncode != 0:
            if "Already up to date" in stderr or "Already up to date" in stdout:
                print_success(f"{name} is already up to date")
            else:
                print_warning(f"Git pull failed for {name}: {stderr.strip()}")
                print_info("Continuing with local state...")
        else:
            print_success(f"{name} updated successfully")
            
    except Exception as e:
        print_warning(f"Git operation failed for {name}: {e}")
        print_info("Continuing with local state...")


def read_syncignore(repo: Path) -> list[str]:
    """
    Read patterns from .syncignore (gitignore-like, simple glob matching).
    - Supports comments (#...) and blank lines
    - Treats trailing '/' as "directory prefix"
    - Includes default patterns for safety
    """
    # Default patterns that should always be ignored
    patterns: list[str] = [
        ".git",
        ".github",
        ".gitattributes",
        ".gitignore",
        "node_modules",
        ".DS_Store"
    ]
    
    path = repo / ".syncignore"
    if path.exists():
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            s = line.strip()
            if s and not s.startswith("#"):
                patterns.append(s)
    
    return patterns


def should_ignore(rel_posix: str, patterns: list[str]) -> bool:
    """
    Minimal gitignore-like behavior using glob matching.
    Note: does not implement full gitignore semantics (negations like !pattern are ignored).
    """
    for pat in patterns:
        if pat.startswith("!"):
            # Keep it simple: ignore negation rules for now
            continue
        
        if pat.endswith("/"):
            prefix = pat
            if rel_posix.startswith(prefix) or f"/{prefix}" in rel_posix:
                return True
            continue
        
        if fnmatch.fnmatch(rel_posix, pat) or fnmatch.fnmatch(Path(rel_posix).name, pat):
            return True
        
        # If pattern looks like a directory name without '/', ignore if any path segment matches.
        if "/" not in pat and pat in Path(rel_posix).parts:
            return True
    
    return False


def list_repo_files(repo: Path) -> list[str]:
    """
    Get list of all relevant files (tracked + untracked), respecting gitignore.
    Uses 'git ls-files' with options to find untracked but not ignored files.
    -c: cached (tracked files)
    -o: others (untracked files)
    --exclude-standard: respect .gitignore
    -z: null terminated
    """
    out = run_git(repo, ["ls-files", "-c", "-o", "--exclude-standard", "-z"], check=False)
    parts = out.split("\0") if out else []
    return [p for p in parts if p]


def files_differ(a: Path, b: Path) -> bool:
    """Check if two files are different."""
    if not a.exists() or not b.exists():
        return True
    if a.is_dir() or b.is_dir():
        return True
    try:
        return a.read_bytes() != b.read_bytes()
    except Exception:
        return True


def remove_empty_dirs(root: Path, rel_path: str) -> None:
    """Recursively remove empty parent directories of a deleted file."""
    try:
        parent = (root / rel_path).parent
        # Stop if we reach the repo root
        while parent != root and parent.exists():
            try:
                # Check if directory is empty
                if not any(parent.iterdir()):
                    parent.rmdir()
                    parent = parent.parent
                else:
                    break
            except (OSError, PermissionError):
                # Can't remove or check - stop trying
                break
    except Exception:
        # Silently fail - not critical
        pass


def sync_files(
    source_repo: Path,
    target_repo: Path,
    source_name: str,
    target_name: str
) -> tuple[list[str], list[str], list[str]]:
    """
    Sync files from source to target repository.
    Includes both tracked and untracked files (respecting gitignore).
    
    Returns:
        Tuple of (added_files, updated_files, deleted_files)
    """
    patterns = read_syncignore(source_repo)
    
    source_files = list_repo_files(source_repo)
    target_files = list_repo_files(target_repo)
    
    source_set = {f for f in source_files if not should_ignore(f, patterns)}
    target_set = {f for f in target_files if not should_ignore(f, patterns)}
    
    added: list[str] = []
    updated: list[str] = []
    deleted: list[str] = []
    
    # Add/update files
    for rel in sorted(source_set):
        src = source_repo / rel
        dst = target_repo / rel
        
        # Skip if source is somehow a directory (shouldn't happen with ls-files)
        if not src.exists() or src.is_dir():
            continue
        
        existed_before = dst.exists()
        
        try:
            if files_differ(src, dst):
                # Create parent directory if needed
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                
                if not existed_before:
                    added.append(rel)
                    print(f"  + {rel}")
                else:
                    updated.append(rel)
                    print(f"  ~ {rel}")
        except Exception as e:
            print_error(f"Failed to copy {rel}: {e}")
    
    # Delete files that exist in target but not in source
    for rel in sorted(target_set - source_set):
        target = target_repo / rel
        if target.exists():
            try:
                if target.is_dir():
                    shutil.rmtree(target)
                else:
                    target.unlink()
                
                # Cleanup empty parent directories
                remove_empty_dirs(target_repo, rel)
                
                deleted.append(rel)
                print(f"  - {rel}")
            except Exception as e:
                print_error(f"Failed to delete {rel}: {e}")
    
    return added, updated, deleted


def run_validation_check(repo: Path, name: str, check_name: str, cmd: list[str]) -> bool:
    """Run a validation check and return True if successful."""
    print_info(f"Running {check_name} for {name}...")
    
    returncode, stdout, stderr = run_command(cmd, cwd=repo, check=False)
    
    if returncode != 0:
        print_error(f"{check_name} failed for {name}")
        # Only print first few lines of error to avoid spamming terminal
        err_msg = (stderr or stdout).strip()
        if err_msg:
            lines = err_msg.splitlines()
            print(f"{Colors.FAIL}{chr(10).join(lines[:10])}{Colors.ENDC}")
            if len(lines) > 10:
                print(f"{Colors.FAIL}... (see logs for full output){Colors.ENDC}")
        return False
    
    print_success(f"{check_name} passed for {name}")
    return True


def run_source_validation(repo: Path, name: str) -> bool:
    """Runs build, lint, and type-check on source repo before syncing. Fails fast if any check fails."""
    pm = detect_package_manager(repo)
    print_info(f"Detected package manager for {name}: {Colors.BOLD}{pm}{Colors.ENDC}")
    
    # Check if package manager is available
    returncode, _, _ = run_command(["which", pm], check=False)
    if returncode != 0:
        print_error(f"{pm} is not installed or not in PATH")
        return False
    
    # Install dependencies first
    print_info(f"Installing dependencies in {name}...")
    returncode, _, _ = run_command([pm, "install"], cwd=repo, check=False)
    if returncode != 0:
        print_warning(f"Dependency install failed. Validation might fail.")
    
    checks = [
        ("build", [pm, "run", "build"]),
        ("lint", [pm, "run", "lint"]),
        ("type-check", [pm, "run", "type-check"])
    ]
    
    # Run all checks - fail fast if any check fails
    for check_name, cmd in checks:
        if not run_validation_check(repo, name, check_name, cmd):
            print_error(f"Source validation failed at {check_name}. Aborting sync.")
            return False
    
    return True


def run_validation(repo: Path, name: str) -> bool:
    """Runs build, lint, and type-check using the detected package manager."""
    pm = detect_package_manager(repo)
    print_info(f"Detected package manager for {name}: {Colors.BOLD}{pm}{Colors.ENDC}")
    
    # Check if package manager is available
    returncode, _, _ = run_command(["which", pm], check=False)
    if returncode != 0:
        print_error(f"{pm} is not installed or not in PATH")
        return False
    
    # Install dependencies first
    print_info(f"Installing dependencies in {name}...")
    returncode, _, _ = run_command([pm, "install"], cwd=repo, check=False)
    if returncode != 0:
        print_warning(f"Dependency install failed. Validation might fail.")
    
    checks = [
        ("build", [pm, "run", "build"]),
        ("lint", [pm, "run", "lint"]),
        ("type-check", [pm, "run", "type-check"])
    ]
    
    all_passed = True
    continue_checks = True
    
    for i, (check_name, cmd) in enumerate(checks):
        if not continue_checks:
            break
            
        if not run_validation_check(repo, name, check_name, cmd):
            all_passed = False
            
            # For build failure, ask if user wants to continue
            if check_name == "build":
                response = input(f"\n{check_name.capitalize()} failed. Continue with remaining checks? (yes/no): ").strip().lower()
                continue_checks = response in ["yes", "y"]
                if not continue_checks:
                    print_warning("Skipping remaining checks due to build failure.")
            # For lint failure, ask if user wants to continue with type-check
            elif check_name == "lint" and i < len(checks) - 1:
                response = input(f"\n{check_name.capitalize()} failed. Continue with type-check? (yes/no): ").strip().lower()
                continue_checks = response in ["yes", "y"]
                if not continue_checks:
                    print_warning("Skipping type-check due to lint failure.")
    
    return all_passed


def fetch_and_merge_target(repo: Path, branch: str, name: str) -> bool:
    """Fetch latest changes from remote and merge into target repository."""
    print_info(f"Fetching latest changes for {name} from origin/{branch}...")
    
    try:
        # Ensure we're on the correct branch
        current_branch = run_git(repo, ["rev-parse", "--abbrev-ref", "HEAD"], check=False)
        if current_branch != branch:
            if is_repo_dirty(repo):
                print_warning(f"{name} is on '{current_branch}' and has uncommitted changes.")
                print_warning(f"Cannot switch to '{branch}'. Skipping fetch.")
                return False
            
            print_info(f"Switching {name} to {branch}...")
            returncode, stdout, stderr = run_command(
                ["git", "-C", str(repo), "checkout", branch],
                check=False
            )
            if returncode != 0:
                print_warning(f"Could not checkout {branch} branch: {stderr.strip()}")
                return False
        
        # Fetch from remote
        print_info(f"Fetching from origin/{branch}...")
        returncode, stdout, stderr = run_command(
            ["git", "-C", str(repo), "fetch", "origin", branch],
            check=False
        )
        if returncode != 0:
            print_warning(f"Git fetch failed for {name}: {stderr.strip()}")
            return False
        
        # Check if local is behind remote
        local_commit = run_git(repo, ["rev-parse", "HEAD"], check=False)
        if not local_commit:
            print_warning(f"Could not determine local commit for {name}")
            return False
        
        # Check if remote branch exists
        returncode, _, _ = run_command(
            ["git", "-C", str(repo), "rev-parse", "--verify", f"origin/{branch}"],
            check=False
        )
        if returncode != 0:
            print_warning(f"Remote branch origin/{branch} does not exist for {name}")
            return False
        
        remote_commit = run_git(repo, ["rev-parse", f"origin/{branch}"], check=False)
        if not remote_commit:
            print_warning(f"Could not determine remote commit for {name}")
            return False
        
        if local_commit == remote_commit:
            print_success(f"{name} is already up to date with origin/{branch}")
            return True
        
        # Check if there are uncommitted changes that would conflict
        if is_repo_dirty(repo):
            print_warning(f"{name} has uncommitted changes. Cannot merge remote changes.")
            return False
        
        # Merge remote changes
        print_info(f"Merging origin/{branch} into {name}...")
        returncode, stdout, stderr = run_command(
            ["git", "-C", str(repo), "merge", f"origin/{branch}"],
            check=False
        )
        
        if returncode != 0:
            # Check if there are merge conflicts
            if "CONFLICT" in stdout or "CONFLICT" in stderr or "conflict" in stdout.lower() or "conflict" in stderr.lower():
                print_error(f"Merge conflicts detected in {name}!")
                print_error("Please resolve conflicts manually before syncing.")
                return False
            else:
                print_warning(f"Git merge failed for {name}: {stderr.strip()}")
                return False
        
        print_success(f"{name} successfully updated with latest changes from origin/{branch}")
        return True
        
    except Exception as e:
        print_error(f"Error during fetch/merge for {name}: {e}")
        return False


def commit_changes(repo: Path, name: str) -> bool:
    """Stage and commit changes in target repository."""
    try:
        # Check if there are changes to commit
        if not is_repo_dirty(repo):
            print_info(f"No changes to commit in {name}")
            return True
        
        # Prompt for commit message
        print(f"\n{Colors.BOLD}Enter commit message for {name}:{Colors.ENDC}")
        commit_message = input("> ").strip()
        
        if not commit_message:
            print_warning("Commit message is empty. Aborting commit.")
            return False
        
        # Stage all changes
        print_info(f"Staging changes in {name}...")
        returncode, stdout, stderr = run_command(
            ["git", "-C", str(repo), "add", "."],
            check=False
        )
        if returncode != 0:
            print_error(f"Failed to stage changes: {stderr.strip()}")
            return False
        
        # Commit changes
        print_info(f"Committing changes in {name}...")
        returncode, stdout, stderr = run_command(
            ["git", "-C", str(repo), "commit", "-m", commit_message],
            check=False
        )
        if returncode != 0:
            print_error(f"Failed to commit changes: {stderr.strip()}")
            return False
        
        print_success(f"Successfully committed changes in {name}")
        return True
        
    except Exception as e:
        print_error(f"Error during commit for {name}: {e}")
        return False


def get_user_choice() -> SyncType | None:
    """Get user's choice for sync direction."""
    print_header("TudoNum Repository Sync Tool")
    print("Select sync direction:")
    print(f"  1. Dev → Staging")
    print(f"  2. Staging → Production")
    print(f"  3. Exit")
    
    while True:
        choice = input("\nEnter your choice (1-3): ").strip()
        
        if choice == "1":
            return "dev-to-staging"
        elif choice == "2":
            return "staging-to-production"
        elif choice == "3":
            print_info("Exiting...")
            return None
        else:
            print_error("Invalid choice. Please enter 1, 2, or 3.")


def confirm_sync(sync_type: SyncType) -> bool:
    """Ask user to confirm the sync operation."""
    if sync_type == "dev-to-staging":
        print_header("Sync: Dev → Staging")
        print("This will:")
        print("  - Pull latest changes from Dev (dev branch) and Staging (staging branch)")
        print("  - Validate Dev repository (build, lint, type-check)")
        print("  - Fetch and merge latest remote changes into Staging")
        print("  - Copy changed files from Dev to Staging")
        print("  - Run build, lint, and type-check on Staging")
        print("  - Optionally commit changes in Staging (if validation passes)")
    else:
        print_header("Sync: Staging → Production")
        print("This will:")
        print("  - Pull latest changes from Staging (staging branch) and Production (main branch)")
        print("  - Validate Staging repository (build, lint, type-check)")
        print("  - Fetch and merge latest remote changes into Production")
        print("  - Copy changed files from Staging to Production")
        print("  - Run build, lint, and type-check on Production")
    
    response = input("\nDo you want to proceed? (yes/no): ").strip().lower()
    return response in ["yes", "y"]


def main() -> int:
    """Main function."""
    try:
        # Get user choice
        sync_type = get_user_choice()
        if sync_type is None:
            return 0
        
        # Confirm sync
        if not confirm_sync(sync_type):
            print_info("Sync cancelled by user.")
            return 0
        
        # Determine source and target repos
        if sync_type == "dev-to-staging":
            source_repo = DEV_REPO
            target_repo = STAGING_REPO
            source_branch = DEV_BRANCH
            target_branch = STAGING_BRANCH
            source_name = "Dev"
            target_name = "Staging"
        else:  # staging-to-production
            source_repo = STAGING_REPO
            target_repo = PROD_REPO
            source_branch = STAGING_BRANCH
            target_branch = PROD_BRANCH
            source_name = "Staging"
            target_name = "Production"
        
        # Verify repositories exist
        print_info("Verifying repositories...")
        ensure_repo_exists(source_repo, source_name)
        ensure_repo_exists(target_repo, target_name)
        print_success("Repositories verified")
        
        # Safety check: Warn if target repo is dirty
        if is_repo_dirty(target_repo):
            print_warning(f"⚠ TARGET REPOSITORY ({target_name}) HAS UNCOMMITTED CHANGES!")
            print_warning("Syncing will overwrite or delete these local changes.")
            response = input(f"Are you sure you want to proceed? This will destroy local changes in {target_name} (yes/no): ").strip().lower()
            if response not in ["yes", "y"]:
                print_error("Sync aborted by user.")
                return 1
        
        # Pull latest changes
        print_header("Step 1: Pulling Latest Changes")
        pull_latest_changes(source_repo, source_branch, source_name)
        pull_latest_changes(target_repo, target_branch, target_name)
        
        # Validate source repository
        print_header("Step 2: Validating Source Repository")
        if not run_source_validation(source_repo, source_name):
            print_error(f"Source validation failed for {source_name}. Aborting sync.")
            return 1
        
        # Fresh fetch and merge target repository
        print_header("Step 3: Fetching and Merging Latest Changes in Target Repository")
        if not fetch_and_merge_target(target_repo, target_branch, target_name):
            print_error(f"Failed to update {target_name} with latest remote changes. Aborting sync.")
            return 1
        
        # Sync files
        print_header("Step 4: Identifying and Copying Changes")
        print_info(f"Comparing {source_name} and {target_name}...")
        
        added, updated, deleted = sync_files(
            source_repo,
            target_repo,
            source_name,
            target_name
        )
        
        total_changes = len(added) + len(updated) + len(deleted)
        
        if total_changes == 0:
            print_success("No changes detected. Repositories are already in sync!")
            return 0
        
        print_success(f"File sync complete: {len(added)} added, {len(updated)} updated, {len(deleted)} deleted")
        
        # Run validation checks
        print_header("Step 5: Running Validation Checks")
        
        checks_passed = run_validation(target_repo, target_name)
        
        # Commit changes (only for Dev→Staging syncs)
        committed = False
        if checks_passed and sync_type == "dev-to-staging":
            print_header("Step 6: Commit Changes")
            response = input("Do you want me to commit these changes? (yes/no): ").strip().lower()
            if response in ["yes", "y"]:
                committed = commit_changes(target_repo, target_name)
                if not committed:
                    print_warning("Commit failed. Changes are staged but not committed.")
            else:
                print_info("Skipping commit. Changes are ready to be committed manually.")
        
        # Summary
        print_header("Sync Summary")
        
        if checks_passed:
            print_success(f"✓ All checks passed! {target_name} is ready.")
        else:
            print_error(f"✗ Some checks failed. Please review the errors above.")
            print_warning("The files have been copied, but validation failed.")
            print_info("You may need to fix issues before committing.")
        
        print(f"\n{Colors.BOLD}Files Changed:{Colors.ENDC}")
        print(f"  Added: {len(added)}")
        print(f"  Updated: {len(updated)}")
        print(f"  Deleted: {len(deleted)}")
        print(f"  Total: {total_changes}")
        
        if added:
            print(f"\n{Colors.BOLD}Added files:{Colors.ENDC}")
            for f in added[:10]:  # Show first 10
                print(f"  + {f}")
            if len(added) > 10:
                print(f"  ... and {len(added) - 10} more")
        
        if updated:
            print(f"\n{Colors.BOLD}Updated files:{Colors.ENDC}")
            for f in updated[:10]:  # Show first 10
                print(f"  ~ {f}")
            if len(updated) > 10:
                print(f"  ... and {len(updated) - 10} more")
        
        if deleted:
            print(f"\n{Colors.BOLD}Deleted files:{Colors.ENDC}")
            for f in deleted[:10]:  # Show first 10
                print(f"  - {f}")
            if len(deleted) > 10:
                print(f"  ... and {len(deleted) - 10} more")
        
        print(f"\n{Colors.BOLD}Next Steps:{Colors.ENDC}")
        if committed:
            print(f"  1. Review the committed changes in {target_name} repository")
            print(f"  2. Push to remote repository: git push origin {target_branch}")
        else:
            print(f"  1. Review the changes in {target_name} repository")
            print(f"  2. Commit the changes using GitHub Desktop or git CLI")
            print(f"  3. Push to remote repository")
        
        if checks_passed:
            return 0
        else:
            return 1
        
    except KeyboardInterrupt:
        print_error("\n\nSync interrupted by user.")
        return 130
    except Exception as e:
        print_error(f"\n\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())


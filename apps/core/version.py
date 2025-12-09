"""
Version information for the application.
This file is automatically updated during deployment.
"""
import os
from pathlib import Path

# Get version from VERSION file
BASE_DIR = Path(__file__).resolve().parent.parent.parent
VERSION_FILE = BASE_DIR / 'VERSION'

def get_version():
    """
    Read version from VERSION file.
    Returns version string or 'unknown' if file doesn't exist.
    """
    try:
        if VERSION_FILE.exists():
            with open(VERSION_FILE, 'r') as f:
                version = f.read().strip()
                return version if version else 'unknown'
        return 'unknown'
    except Exception:
        return 'unknown'

def get_git_info():
    """
    Get git commit hash and branch info.
    Returns dict with commit_hash, branch, and commit_date.
    """
    import subprocess
    try:
        # Get commit hash
        commit_hash = subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'],
            cwd=BASE_DIR,
            stderr=subprocess.DEVNULL
        ).decode('utf-8').strip()[:7]
        
        # Get branch
        branch = subprocess.check_output(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            cwd=BASE_DIR,
            stderr=subprocess.DEVNULL
        ).decode('utf-8').strip()
        
        # Get commit date
        commit_date = subprocess.check_output(
            ['git', 'log', '-1', '--format=%ci'],
            cwd=BASE_DIR,
            stderr=subprocess.DEVNULL
        ).decode('utf-8').strip()
        
        return {
            'commit_hash': commit_hash,
            'branch': branch,
            'commit_date': commit_date,
        }
    except Exception:
        return {
            'commit_hash': 'unknown',
            'branch': 'unknown',
            'commit_date': 'unknown',
        }

# Current version
__version__ = get_version()


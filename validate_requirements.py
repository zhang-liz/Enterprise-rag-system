#!/usr/bin/env python3
"""
Validate requirements.txt for common issues.
This can be run without Docker to check for problems.
"""

import sys
from pathlib import Path


def validate_requirements():
    """Validate requirements.txt file."""

    print("🔍 Validating requirements.txt...")
    print("=" * 50)

    req_file = Path("requirements.txt")
    if not req_file.exists():
        print("❌ requirements.txt not found!")
        return False

    issues = []
    warnings = []
    packages = []

    with open(req_file) as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()

            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue

            # Check for problematic packages
            if 'openai-whisper' in line:
                issues.append(f"Line {line_num}: openai-whisper package found - should be removed!")
                issues.append("  Reason: Python 3.13 compatibility issues")
                issues.append("  Solution: Use OpenAI's Whisper API (already included in openai package)")

            if 'opencv-python==' in line and 'headless' not in line:
                warnings.append(f"Line {line_num}: opencv-python found")
                warnings.append("  Consider: opencv-python-headless for Docker compatibility")

            # Extract package names
            if '==' in line:
                pkg_name = line.split('==')[0].strip()
                pkg_version = line.split('==')[1].strip()
                packages.append((pkg_name, pkg_version))
            elif line and not line.startswith('-'):
                warnings.append(f"Line {line_num}: No version specified for {line}")

    # Report findings
    print(f"\n📦 Found {len(packages)} packages with versions")

    if issues:
        print(f"\n❌ {len(issues)} CRITICAL ISSUES FOUND:")
        for issue in issues:
            print(f"  {issue}")
        print("\n🔧 Fix these issues before building Docker images!")
        return False

    if warnings:
        print(f"\n⚠️  {len(warnings)} warnings:")
        for warning in warnings:
            print(f"  {warning}")

    # Check for required packages
    print("\n✅ Checking for required packages...")
    required = {
        'fastapi': False,
        'openai': False,
        'neo4j': False,
        'qdrant-client': False,
        'pillow': False,
        'pytesseract': False,
    }

    for pkg, _ in packages:
        pkg_lower = pkg.lower()
        for req in required:
            if req in pkg_lower:
                required[req] = True

    all_found = True
    for pkg, found in required.items():
        if found:
            print(f"  ✅ {pkg}")
        else:
            print(f"  ❌ {pkg} - MISSING!")
            all_found = False

    if not all_found:
        print("\n❌ Some required packages are missing!")
        return False

    # Check for Docker-friendly packages
    print("\n🐳 Docker compatibility checks...")
    has_headless_opencv = any('opencv-python-headless' in pkg for pkg, _ in packages)
    has_no_whisper = not any('openai-whisper' in pkg for pkg, _ in packages)

    if has_headless_opencv:
        print("  ✅ Using opencv-python-headless (Docker-friendly)")
    else:
        print("  ⚠️  Not using opencv-python-headless")

    if has_no_whisper:
        print("  ✅ Not using local openai-whisper (good - using API)")
    else:
        print("  ❌ Using openai-whisper package (problematic)")
        return False

    print("\n" + "=" * 50)
    print("✅ All validation checks passed!")
    print("\nRequirements.txt is ready for Docker build.")
    return True


if __name__ == "__main__":
    success = validate_requirements()
    sys.exit(0 if success else 1)

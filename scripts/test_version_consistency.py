#!/usr/bin/env python3
"""
Version consistency tests for Sonar.

This script validates that all version references in the project are consistent
and follow the established patterns.
"""

import os
import re
import sys
import tempfile
from pathlib import Path
from typing import List, Tuple, Optional

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent.absolute()


def test_meson_version() -> Tuple[bool, str]:
    """Test that meson.build contains a valid version."""
    meson_file = PROJECT_ROOT / "meson.build"
    
    if not meson_file.exists():
        return False, "meson.build not found"
    
    try:
        content = meson_file.read_text()
        
        # Look for version: 'x.y.z' pattern
        version_match = re.search(r"version:\s*'([^']+)'", content)
        if not version_match:
            return False, "Version not found in meson.build"
        
        version = version_match.group(1)
        
        # Validate semantic versioning format
        if not re.match(r'^\d+\.\d+\.\d+$', version):
            return False, f"Invalid version format: {version}"
        
        return True, f"Valid version found: {version}"
    
    except Exception as e:
        return False, f"Error reading meson.build: {e}"


def test_python_version() -> Tuple[bool, str]:
    """Test that Python package version is accessible."""
    try:
        # Try to import from src directory
        sys.path.insert(0, str(PROJECT_ROOT / "src"))
        from _version import __version__
        
        # Test that we can access it
        version = __version__
        
        # Validate semantic versioning format
        if not re.match(r'^\d+\.\d+\.\d+$', version):
            return False, f"Invalid Python version format: {version}"
        
        return True, f"Valid Python version: {version}"
    
    except ImportError as e:
        return False, f"Cannot import sonar module: {e}"
    except Exception as e:
        return False, f"Error checking Python version: {e}"


def test_version_files_consistency() -> Tuple[bool, str]:
    """Test that all version files are consistent."""
    # Read meson.build version
    meson_file = PROJECT_ROOT / "meson.build"
    if not meson_file.exists():
        return False, "meson.build not found"
    
    try:
        content = meson_file.read_text()
        version_match = re.search(r"version:\s*'([^']+)'", content)
        if not version_match:
            return False, "Version not found in meson.build"
        
        meson_version = version_match.group(1)
        
        # Check version files
        version_files = [
            ("src/_version.py", r'__version__ = "([^"]+)"'),
        ]
        
        inconsistencies = []
        
        for file_path, pattern in version_files:
            full_path = PROJECT_ROOT / file_path
            if not full_path.exists():
                inconsistencies.append(f"{file_path}: file not found")
                continue
            
            try:
                file_content = full_path.read_text()
                match = re.search(pattern, file_content)
                if not match:
                    inconsistencies.append(f"{file_path}: version pattern not found")
                    continue
                
                file_version = match.group(1)
                if file_version != meson_version:
                    inconsistencies.append(f"{file_path}: version {file_version} != meson version {meson_version}")
            
            except Exception as e:
                inconsistencies.append(f"{file_path}: error reading file - {e}")
        
        if inconsistencies:
            return False, "Version inconsistencies found:\n" + "\n".join(f"  - {issue}" for issue in inconsistencies)
        
        return True, f"All version files consistent with meson.build version: {meson_version}"
    
    except Exception as e:
        return False, f"Error checking version consistency: {e}"


def test_no_hardcoded_versions() -> Tuple[bool, str]:
    """Test that no hardcoded versions exist in Python files."""
    # Get meson.build version
    meson_file = PROJECT_ROOT / "meson.build"
    if not meson_file.exists():
        return False, "meson.build not found"
    
    try:
        content = meson_file.read_text()
        version_match = re.search(r"version:\s*'([^']+)'", content)
        if not version_match:
            return False, "Version not found in meson.build"
        
        current_version = version_match.group(1)
        
        # Files to check for hardcoded versions
        python_files = list((PROJECT_ROOT / "src").glob("**/*.py"))
        
        # Exclude version files from this check
        excluded_files = {"_version.py", "__init__.py"}
        
        hardcoded_versions = []
        
        for py_file in python_files:
            if py_file.name in excluded_files:
                continue
            
            try:
                file_content = py_file.read_text()
                
                # Look for hardcoded version patterns
                version_patterns = [
                    rf'"{re.escape(current_version)}"',
                    rf"'{re.escape(current_version)}'",
                    r'"[0-9]+\.[0-9]+\.[0-9]+"',
                    r"'[0-9]+\.[0-9]+\.[0-9]+'"
                ]
                
                for pattern in version_patterns:
                    matches = re.findall(pattern, file_content)
                    if matches:
                        # Check if it's in a version import context
                        lines = file_content.split('\n')
                        for i, line in enumerate(lines):
                            if re.search(pattern, line):
                                # Skip if it's an import statement or version assignment
                                if re.search(r'(import|from|__version__|version\s*=)', line):
                                    continue
                                hardcoded_versions.append(f"{py_file.relative_to(PROJECT_ROOT)}:{i+1}")
            
            except Exception as e:
                hardcoded_versions.append(f"{py_file.relative_to(PROJECT_ROOT)}: error reading file - {e}")
        
        if hardcoded_versions:
            return False, "Hardcoded versions found:\n" + "\n".join(f"  - {issue}" for issue in hardcoded_versions)
        
        return True, "No hardcoded versions found in Python files"
    
    except Exception as e:
        return False, f"Error checking for hardcoded versions: {e}"


def test_version_template_files() -> Tuple[bool, str]:
    """Test that template files use @VERSION@ placeholder."""
    template_files = [
        "src/_version.py.in",
        "data/io.github.tobagin.sonar.appdata.xml.in"
    ]
    
    issues = []
    
    for template_file in template_files:
        full_path = PROJECT_ROOT / template_file
        if not full_path.exists():
            continue  # Template files are optional
        
        try:
            content = full_path.read_text()
            
            # Check if it uses @VERSION@ placeholder for current release
            if "@VERSION@" not in content:
                issues.append(f"{template_file}: missing @VERSION@ placeholder")
            
            # For appdata files, only check that the first release uses @VERSION@
            if template_file.endswith('.appdata.xml.in'):
                # Check that the first release entry uses @VERSION@
                first_release_match = re.search(r'<release version="([^"]+)"', content)
                if first_release_match:
                    first_version = first_release_match.group(1)
                    if first_version != "@VERSION@":
                        issues.append(f"{template_file}: first release should use @VERSION@, found {first_version}")
                # Historical releases with hardcoded versions are acceptable
            else:
                # For other template files, check if it has hardcoded version
                if re.search(r'[0-9]+\.[0-9]+\.[0-9]+', content):
                    issues.append(f"{template_file}: contains hardcoded version")
        
        except Exception as e:
            issues.append(f"{template_file}: error reading file - {e}")
    
    if issues:
        return False, "Template file issues:\n" + "\n".join(f"  - {issue}" for issue in issues)
    
    return True, "All template files use proper version placeholders"


def test_server_version_endpoints() -> Tuple[bool, str]:
    """Test that server version endpoints use centralized version."""
    server_file = PROJECT_ROOT / "src" / "server.py"
    
    if not server_file.exists():
        return False, "server.py not found"
    
    try:
        content = server_file.read_text()
        
        # Check for version import
        if not re.search(r'from.*__version__.*import', content) and not re.search(r'import.*__version__', content):
            return False, "server.py doesn't import __version__"
        
        # Check for hardcoded versions in API responses
        hardcoded_patterns = [
            r'"version":\s*"[0-9]+\.[0-9]+\.[0-9]+"',
            r"'version':\s*'[0-9]+\.[0-9]+\.[0-9]+'",
            r'version\s*=\s*"[0-9]+\.[0-9]+\.[0-9]+"'
        ]
        
        for pattern in hardcoded_patterns:
            if re.search(pattern, content):
                return False, f"server.py contains hardcoded version: {pattern}"
        
        return True, "server.py uses centralized version"
    
    except Exception as e:
        return False, f"Error checking server version: {e}"


def main():
    """Run all version consistency tests."""
    print("🔍 Running version consistency tests for Sonar...")
    print("=" * 60)
    
    tests = [
        ("Meson build version", test_meson_version),
        ("Python package version", test_python_version),
        ("Version files consistency", test_version_files_consistency),
        ("No hardcoded versions", test_no_hardcoded_versions),
        ("Version template files", test_version_template_files),
        ("Server version endpoints", test_server_version_endpoints),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            success, message = test_func()
            if success:
                print(f"✅ {test_name}: {message}")
                passed += 1
            else:
                print(f"❌ {test_name}: {message}")
                failed += 1
        except Exception as e:
            print(f"💥 {test_name}: Test error - {e}")
            failed += 1
    
    print("=" * 60)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed > 0:
        print("\n🚨 Version consistency issues found!")
        print("Please fix the issues above before proceeding.")
        sys.exit(1)
    else:
        print("\n✨ All version consistency tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
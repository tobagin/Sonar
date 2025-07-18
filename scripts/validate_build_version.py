#!/usr/bin/env python3
"""
Build version validation script for Sonar.

This script validates version consistency and format during the build process.
"""

import os
import re
import sys
import subprocess
from pathlib import Path
from typing import List, Tuple, Optional


# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent.absolute()


def validate_meson_version() -> Tuple[bool, str]:
    """Validate the version in meson.build."""
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
            return False, f"Invalid version format: {version} (must be X.Y.Z)"
        
        # Check version components are reasonable
        parts = version.split('.')
        for part in parts:
            if int(part) > 999:
                return False, f"Version component too large: {part} (max 999)"
        
        return True, f"Valid meson version: {version}"
    
    except Exception as e:
        return False, f"Error validating meson version: {e}"


def validate_git_tag_consistency() -> Tuple[bool, str]:
    """Validate that git tag matches version (if tag exists)."""
    try:
        # Get version from meson.build
        meson_file = PROJECT_ROOT / "meson.build"
        if not meson_file.exists():
            return False, "meson.build not found"
        
        content = meson_file.read_text()
        version_match = re.search(r"version:\s*'([^']+)'", content)
        if not version_match:
            return False, "Version not found in meson.build"
        
        version = version_match.group(1)
        
        # Check if we're on a git tag
        try:
            result = subprocess.run(
                ['git', 'describe', '--exact-match', '--tags', 'HEAD'],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                check=True
            )
            current_tag = result.stdout.strip()
            
            # Check if tag matches version
            expected_tag = f"v{version}"
            if current_tag != expected_tag:
                return False, f"Git tag {current_tag} doesn't match version {version} (expected {expected_tag})"
            
            return True, f"Git tag {current_tag} matches version {version}"
        
        except subprocess.CalledProcessError:
            # Not on a tag, which is fine for development builds
            return True, f"Not on a git tag (development build with version {version})"
    
    except Exception as e:
        return False, f"Error checking git tag consistency: {e}"


def validate_template_files() -> Tuple[bool, str]:
    """Validate that template files use @VERSION@ placeholder."""
    template_files = [
        "src/_version.py.in",
        "data/io.github.tobagin.sonar.appdata.xml.in"
    ]
    
    issues = []
    found_templates = []
    
    for template_file in template_files:
        full_path = PROJECT_ROOT / template_file
        if not full_path.exists():
            continue  # Template files are optional
        
        found_templates.append(template_file)
        
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
    
    if found_templates:
        return True, f"Template files valid: {', '.join(found_templates)}"
    else:
        return True, "No template files found (using direct version references)"


def validate_no_hardcoded_versions() -> Tuple[bool, str]:
    """Validate that no hardcoded versions exist in source files."""
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
        excluded_files = {"_version.py"}
        
        hardcoded_versions = []
        
        for py_file in python_files:
            if py_file.name in excluded_files:
                continue
            
            try:
                file_content = py_file.read_text()
                
                # Look for hardcoded version strings
                version_patterns = [
                    r'"[0-9]+\.[0-9]+\.[0-9]+"',
                    r"'[0-9]+\.[0-9]+\.[0-9]+'"
                ]
                
                for pattern in version_patterns:
                    matches = re.finditer(pattern, file_content)
                    for match in matches:
                        # Get the line number
                        line_num = file_content[:match.start()].count('\n') + 1
                        
                        # Get the full line for context
                        lines = file_content.split('\n')
                        line_content = lines[line_num - 1].strip()
                        
                        # Skip if it's clearly a version import or assignment
                        if re.search(r'(import|from|__version__|version\s*=)', line_content):
                            continue
                        
                        hardcoded_versions.append(f"{py_file.relative_to(PROJECT_ROOT)}:{line_num}")
            
            except Exception as e:
                hardcoded_versions.append(f"{py_file.relative_to(PROJECT_ROOT)}: error reading file - {e}")
        
        if hardcoded_versions:
            return False, "Hardcoded versions found:\n" + "\n".join(f"  - {issue}" for issue in hardcoded_versions)
        
        return True, "No hardcoded versions found in source files"
    
    except Exception as e:
        return False, f"Error checking for hardcoded versions: {e}"


def validate_build_consistency() -> Tuple[bool, str]:
    """Validate build structure consistency."""
    required_files = [
        "meson.build",
        "src/__init__.py",
        "src/main.py",
        "src/server.py"
    ]
    
    missing_files = []
    
    for file_path in required_files:
        full_path = PROJECT_ROOT / file_path
        if not full_path.exists():
            missing_files.append(file_path)
    
    if missing_files:
        return False, f"Missing required files: {', '.join(missing_files)}"
    
    return True, "Build structure is consistent"


def validate_version_imports() -> Tuple[bool, str]:
    """Validate that modules import version correctly."""
    # Files that should import version
    files_to_check = [
        ("src/main.py", "main application"),
        ("src/server.py", "server module"),
    ]
    
    issues = []
    
    for file_path, description in files_to_check:
        full_path = PROJECT_ROOT / file_path
        if not full_path.exists():
            issues.append(f"{file_path}: file not found")
            continue
        
        try:
            content = full_path.read_text()
            
            # Check for version import patterns
            version_import_patterns = [
                r'from.*__version__.*import',
                r'import.*__version__',
                r'from.*sonar.*import.*__version__',
                r'import.*sonar.*__version__'
            ]
            
            has_version_import = any(re.search(pattern, content) for pattern in version_import_patterns)
            
            if not has_version_import:
                issues.append(f"{file_path}: {description} doesn't import version")
        
        except Exception as e:
            issues.append(f"{file_path}: error reading file - {e}")
    
    if issues:
        return False, "Version import issues:\n" + "\n".join(f"  - {issue}" for issue in issues)
    
    return True, "All modules import version correctly"


def main():
    """Run all build version validation tests."""
    print("🔧 Running build version validation for Sonar...")
    print("=" * 60)
    
    validations = [
        ("Meson version format", validate_meson_version),
        ("Git tag consistency", validate_git_tag_consistency),
        ("Template files", validate_template_files),
        ("No hardcoded versions", validate_no_hardcoded_versions),
        ("Build consistency", validate_build_consistency),
        ("Version imports", validate_version_imports),
    ]
    
    passed = 0
    failed = 0
    
    for validation_name, validation_func in validations:
        try:
            success, message = validation_func()
            if success:
                print(f"✅ {validation_name}: {message}")
                passed += 1
            else:
                print(f"❌ {validation_name}: {message}")
                failed += 1
        except Exception as e:
            print(f"💥 {validation_name}: Validation error - {e}")
            failed += 1
    
    print("=" * 60)
    print(f"📊 Validation Results: {passed} passed, {failed} failed")
    
    if failed > 0:
        print("\n🚨 Build version validation failed!")
        print("Please fix the issues above before building.")
        sys.exit(1)
    else:
        print("\n✨ All build version validations passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
# Version Management for Sonar

## Overview

Sonar uses a centralized version management system where `meson.build` serves as the **single source of truth** for version information. All other components derive their version from this central location to ensure consistency across the entire project.

## Core Principles

### 1. Single Source of Truth
- **Primary Source**: `meson.build` contains the authoritative version
- **Propagation**: All other files derive their version from meson.build
- **Consistency**: Automated tools ensure all components use the same version

### 2. Semantic Versioning
- **Format**: `MAJOR.MINOR.PATCH` (e.g., "1.0.5")
- **Validation**: Automated validation ensures proper semver format
- **Components**: Each part limited to 999 for reasonable bounds

### 3. Automated Validation
- **Build-time Checks**: Version consistency validated during build
- **Development Tools**: Scripts to check version consistency
- **CI/CD Integration**: Automated validation in continuous integration

## Version Flow Architecture

```
meson.build (version: '1.0.5')
    ↓
src/_version.py (__version__ = "1.0.5")
    ↓
src/__init__.py (from ._version import __version__)
    ↓
src/main.py (from sonar import __version__)
    ↓
src/server.py (from sonar import __version__)
    ↓
Other modules and components
```

## File Structure

### Primary Files

1. **`meson.build`** - The authoritative version source
   ```meson
   project('sonar', 'c',
     version: '1.0.5',
     meson_version: '>= 0.62.0',
     default_options: [ 'warning_level=2', 'werror=false', ],
   )
   ```

2. **`src/_version.py`** - Generated version file
   ```python
   __version__ = "1.0.5"
   ```

3. **`src/__init__.py`** - Package version export
   ```python
   from ._version import __version__
   ```

### Template Files (Optional)

- **`src/_version.py.in`** - Template for generated version file
  ```python
  __version__ = "@VERSION@"
  ```

- **`data/io.github.tobagin.sonar.appdata.xml.in`** - Metadata template
  ```xml
  <release version="@VERSION@" date="@DATE@">
  ```

## Version Management Tools

### 1. Version Consistency Testing
```bash
python scripts/test_version_consistency.py
```

**Tests performed:**
- Meson build version validation
- Python package version accessibility
- Version files consistency
- No hardcoded versions in source
- Template files use proper placeholders
- Server endpoints use centralized version

### 2. Build Version Validation
```bash
python scripts/validate_build_version.py
```

**Validations performed:**
- Meson version format validation
- Git tag consistency (if applicable)
- Template files validation
- No hardcoded versions in source
- Build structure consistency
- Version import validation

### 3. Version Management CLI
```bash
python version.py [command]
```

**Available commands:**
- `info` - Display version information
- `report` - Generate comprehensive version report
- `update` - Update all version references
- `bump [major|minor|patch]` - Bump version components
- `export version.json` - Export version info as JSON

## Development Workflow

### For Regular Development

1. **Check Version Consistency**
   ```bash
   python scripts/test_version_consistency.py
   ```

2. **Update Version References** (if needed)
   ```bash
   python version.py update
   ```

3. **Validate Build**
   ```bash
   python scripts/validate_build_version.py
   ```

### For Version Updates

1. **Update meson.build** (manual edit)
   ```meson
   version: '1.0.6',  # Update this line
   ```

2. **Propagate Changes**
   ```bash
   python version.py update
   ```

3. **Validate Consistency**
   ```bash
   python scripts/test_version_consistency.py
   ```

4. **Create Git Tag** (for releases)
   ```bash
   git tag -a v1.0.6 -m "Release v1.0.6"
   ```

### For Version Bumping

1. **Bump Version**
   ```bash
   python version.py bump patch --update
   ```

2. **Validate Changes**
   ```bash
   python scripts/test_version_consistency.py
   ```

## Environment Variables

### Development Variables

- **`SONAR_VERSION`** - Override version for development/testing
- **`SONAR_BUILD_ENV`** - Set build environment (dev, test, prod)

### Usage Example
```bash
export SONAR_VERSION="1.0.5-dev"
python -m sonar --version
```

## Best Practices

### For Developers

1. **Never Hardcode Versions**
   - ❌ `version = "1.0.5"`
   - ✅ `from sonar import __version__`

2. **Always Import from Package**
   ```python
   from sonar import __version__
   print(f"Sonar version: {__version__}")
   ```

3. **Test Version Display**
   - Test in development environment
   - Test in installed package
   - Test in different build configurations

4. **Use Version Tools**
   - Run consistency tests before commits
   - Use validation scripts in CI/CD
   - Validate version updates

### For Version Updates

1. **Update Process**
   - Edit `meson.build` with new version
   - Run `python version.py update`
   - Test application functionality
   - Update documentation if needed
   - Create git tag for releases

2. **Validation Steps**
   - Run consistency tests
   - Build and test application
   - Verify version display in UI
   - Check API version endpoints

## Troubleshooting

### Common Issues

1. **Version Not Updating**
   - Check `meson.build` syntax
   - Run `python version.py update`
   - Verify file permissions

2. **Version Mismatches**
   - Run consistency tests
   - Check for hardcoded versions
   - Validate import statements

3. **Build Failures**
   - Check meson.build syntax
   - Validate version format
   - Ensure all files are accessible

### Debug Commands

```bash
# Check current version
python version.py info

# Generate detailed report
python version.py report

# Check what would be updated
python version.py update --dry-run

# Validate all consistency
python scripts/test_version_consistency.py
```

## Integration with Build System

### Meson Integration

The version from `meson.build` is automatically available in the build system:

```meson
conf = configuration_data()
conf.set('VERSION', meson.project_version())
```

### Python Package Integration

The version is automatically available in the Python package:

```python
import sonar
print(sonar.__version__)  # Prints current version
```

### Git Integration

Version information can include git metadata:

```python
from version import VersionManager
vm = VersionManager()
info = vm.get_version_info()
print(f"Version: {info['version']}")
print(f"Git Commit: {info['git_commit']}")
print(f"Build Date: {info['build_date']}")
```

## Future Enhancements

### Planned Improvements

1. **Automatic Version Bumping**
   - Git tag-based version bumping
   - Changelog integration
   - Release note generation

2. **CI/CD Integration**
   - Automated version validation
   - Release pipeline integration
   - Automated tagging

3. **Enhanced Validation**
   - More comprehensive consistency checks
   - Performance benchmarking
   - Cross-platform validation

4. **Developer Tools**
   - IDE integration
   - Git hooks for validation
   - Pre-commit checks

## Conclusion

The centralized version management system ensures that all components of Sonar use consistent version information. By using `meson.build` as the single source of truth and providing automated validation tools, we maintain version consistency across the entire project while making version updates simple and reliable.

For questions or issues with version management, please refer to the troubleshooting section or run the validation scripts to identify and resolve problems.
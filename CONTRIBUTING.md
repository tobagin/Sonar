# Contributing to Echo

Thank you for your interest in contributing to Echo! This guide will help you get started with contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Environment](#development-environment)
- [Contributing Guidelines](#contributing-guidelines)
- [Submitting Changes](#submitting-changes)
- [Reporting Issues](#reporting-issues)
- [Style Guidelines](#style-guidelines)

## Code of Conduct

This project follows the [GNOME Code of Conduct](https://conduct.gnome.org/). By participating in this project, you agree to abide by its terms.

## Getting Started

### Prerequisites

Before contributing, make sure you have:

- Python 3.12+
- GTK4 development libraries
- Libadwaita 1.4+
- Meson build system
- Blueprint compiler
- Flatpak (for testing)
- Git

### Setting Up the Development Environment

1. **Fork and Clone the Repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/echo.git
   cd echo
   ```

2. **Install Development Dependencies**
   ```bash
   # On Fedora/RHEL
   sudo dnf install python3-devel gtk4-devel libadwaita-devel meson blueprint-compiler flatpak flatpak-builder

   # On Ubuntu/Debian
   sudo apt install python3-dev libgtk-4-dev libadwaita-1-dev meson blueprint-compiler flatpak flatpak-builder
   ```

3. **Build for Development**
   ```bash
   ./build.sh --dev --install
   ```

4. **Run the Application**
   ```bash
   flatpak run io.github.tobagin.echo
   ```

## Contributing Guidelines

### Areas for Contribution

We welcome contributions in the following areas:

- **Bug Fixes**: Help fix reported issues
- **Feature Development**: Implement new features from our roadmap
- **UI/UX Improvements**: Enhance the user interface and experience
- **Documentation**: Improve or translate documentation
- **Testing**: Write tests and improve test coverage
- **Accessibility**: Make the app more accessible
- **Internationalization**: Add translations for your language

### Development Workflow

1. **Check Existing Issues**: Look for existing issues or feature requests
2. **Create an Issue**: If none exists, create one describing your proposed changes
3. **Fork the Repository**: Create your own fork to work on
4. **Create a Feature Branch**: Use a descriptive branch name
   ```bash
   git checkout -b feature/your-feature-name
   ```
5. **Make Changes**: Follow our coding standards (see below)
6. **Test Your Changes**: Ensure everything works properly
7. **Commit Your Changes**: Use clear, descriptive commit messages
8. **Submit a Pull Request**: Include a detailed description

### Coding Standards

#### Python Code

- Follow **PEP 8** style guidelines
- Use **type hints** for all function parameters and return values
- Write **docstrings** for all functions using Google style:
  ```python
  def example_function(param1: str, param2: int) -> bool:
      """
      Brief description of what the function does.

      Args:
          param1 (str): Description of param1.
          param2 (int): Description of param2.

      Returns:
          bool: Description of return value.
      """
  ```
- Use descriptive variable names
- Keep functions under 50 lines when possible
- Prefer composition over inheritance

#### UI Code (Blueprint)

- Use consistent indentation (2 spaces)
- Add meaningful comments for complex UI logic
- Follow GNOME Human Interface Guidelines
- Use semantic widget names
- Ensure accessibility attributes are set

#### File Organization

- Keep files under 500 lines of code
- Group related functionality into modules
- Use relative imports within packages
- Organize imports: standard library, third-party, local

### Testing

- Write unit tests for new functionality using pytest
- Test files should mirror the main app structure in `/tests`
- Include at least:
  - 1 test for expected behavior
  - 1 edge case test
  - 1 failure case test
- Run tests before submitting:
  ```bash
  pytest tests/
  ```

### UI Guidelines

- Follow GNOME Human Interface Guidelines
- Use Libadwaita widgets when possible
- Ensure the app works well with both light and dark themes
- Test with different window sizes
- Consider keyboard navigation and accessibility

## Submitting Changes

### Pull Request Process

1. **Update Documentation**: Ensure README.md reflects any changes
2. **Run Quality Checks**:
   ```bash
   # Format code
   black src/ tests/

   # Check linting
   ruff check src/ tests/

   # Run type checking
   mypy src/

   # Run tests
   pytest tests/
   ```

3. **Write Clear Commit Messages**:
   ```
   feat: add history export functionality

   - Added JSON, CSV, and TXT export formats
   - Implemented file chooser dialog
   - Added export button to history view

   Closes #123
   ```

4. **Create Pull Request**: Include:
   - Clear description of changes
   - Link to related issues
   - Screenshots for UI changes
   - Testing instructions

### Commit Message Format

Use conventional commits format:
- `feat:` for new features
- `fix:` for bug fixes
- `docs:` for documentation changes
- `style:` for formatting changes
- `refactor:` for code refactoring
- `test:` for adding tests
- `chore:` for maintenance tasks

## Reporting Issues

### Bug Reports

Use the bug report template and include:
- Echo version
- Operating system and version
- GTK4/Libadwaita versions
- Steps to reproduce
- Expected vs actual behavior
- Screenshots if applicable
- Log output if relevant

### Feature Requests

Use the feature request template and include:
- Clear description of the feature
- Use case/motivation
- Proposed implementation (if any)
- Screenshots/mockups (if UI-related)

### Performance Issues

Include:
- System specifications
- Performance profiling data
- Specific operations that are slow
- Expected vs actual performance

## Style Guidelines

### Code Style

- Use descriptive variable and function names
- Avoid abbreviations unless widely understood
- Add comments for complex logic
- Use consistent naming conventions:
  - `snake_case` for variables and functions
  - `PascalCase` for classes
  - `UPPER_CASE` for constants

### Documentation Style

- Use clear, concise language
- Include code examples where helpful
- Keep line length under 100 characters
- Use proper Markdown formatting

### UI Text

- Use sentence case for labels and buttons
- Keep text concise but descriptive
- Follow GNOME terminology guidelines
- Consider internationalization

## Release Process

### Version Numbering

We follow [Semantic Versioning](https://semver.org/):
- `MAJOR.MINOR.PATCH`
- Major: Breaking changes
- Minor: New features (backward compatible)
- Patch: Bug fixes (backward compatible)

### Release Checklist

- [ ] Update version in `meson.build`
- [ ] Update CHANGELOG.md
- [ ] Test on multiple distributions
- [ ] Update screenshots if needed
- [ ] Create release tag
- [ ] Submit to Flathub

## Getting Help

- **GitHub Discussions**: General questions and community discussion
- **GitHub Issues**: Bug reports and feature requests
- **Matrix/IRC**: Real-time chat (if available)

## Recognition

Contributors will be recognized in:
- Release notes
- About dialog credits
- GitHub contributor list

Thank you for contributing to Echo! 🎉
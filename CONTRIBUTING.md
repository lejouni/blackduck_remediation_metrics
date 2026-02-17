# Contributing to Black Duck Remediation Metrics

Thank you for your interest in contributing to Black Duck Remediation Metrics! This document provides guidelines and instructions for contributing.

## Development Setup

1. Fork and clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\Activate.ps1
   ```
3. Install development dependencies:
   ```bash
   pip install -e .[dev,playwright]
   ```
4. Install pre-commit hooks (if available):
   ```bash
   pre-commit install
   ```

## Code Style

- Follow PEP 8 style guidelines
- Use meaningful variable and function names
- Add docstrings to all functions and classes
- Keep functions focused and concise
- Maximum line length: 120 characters

### Formatting

We use `black` for code formatting:

```bash
black src/
```

### Linting

Run `flake8` to check for issues:

```bash
flake8 src/
```

## Testing

### Running Tests

Run all tests:

```bash
pytest
```

Run with coverage:

```bash
pytest --cov=blackduck_remediation_metrics --cov-report=html
```

### Writing Tests

- Place tests in the `tests/` directory
- Name test files with `test_` prefix
- Name test functions with `test_` prefix
- Use descriptive test names that explain what is being tested
- Include both positive and negative test cases
- Mock external API calls

Example:

```python
def test_feature_name_should_do_something():
    """Test that feature does something specific."""
    # Arrange
    input_data = "test"
    
    # Act
    result = function_under_test(input_data)
    
    # Assert
    assert result == expected_output
```

## Submitting Changes

### Pull Request Process

1. Create a new branch for your feature or bugfix:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes and commit them with clear messages:
   ```bash
   git commit -m "Add feature: description of feature"
   ```

3. Push to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

4. Create a Pull Request on GitHub

### Commit Message Guidelines

- Use the present tense ("Add feature" not "Added feature")
- Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit the first line to 72 characters or less
- Reference issues and pull requests after the first line

Examples:
- `Fix bug in vulnerability counting`
- `Add support for filtering by project group`
- `Update documentation for new API endpoint`

### Pull Request Guidelines

- Provide a clear description of the changes
- Reference any related issues
- Include screenshots for UI changes
- Ensure all tests pass
- Update documentation as needed
- Add tests for new features

## Code Review Process

- All submissions require review before merging
- Reviewers may suggest changes or improvements
- Be open to feedback and discussion
- Address review comments promptly

## Reporting Bugs

### Before Submitting a Bug Report

- Check the issue tracker to avoid duplicates
- Verify the bug with the latest version
- Collect relevant information (version, OS, error messages)

### Submitting a Bug Report

Include:
- Clear, descriptive title
- Steps to reproduce the issue
- Expected behavior
- Actual behavior
- Screenshots (if applicable)
- Environment details (OS, Python version, package version)
- Error messages or logs

## Requesting Features

### Before Submitting a Feature Request

- Check if the feature already exists
- Search existing feature requests
- Consider if it fits the project scope

### Submitting a Feature Request

Include:
- Clear, descriptive title
- Detailed description of the feature
- Use cases and benefits
- Example usage (if applicable)
- Alternative solutions considered

## Documentation

- Update README.md for user-facing changes
- Update docstrings for code changes
- Add examples for new features
- Keep documentation clear and concise
- Use proper Markdown formatting

## Release Process

(For maintainers)

1. Update version in `pyproject.toml` and `__init__.py`
2. Update CHANGELOG.md with release notes
3. Create a git tag: `git tag -a v0.1.x -m "Release version 0.1.x"`
4. Push tag: `git push origin v0.1.x`
5. Build package: `python -m build`
6. Upload to PyPI: `python -m twine upload dist/*`

## Questions or Need Help?

- Open an issue for questions
- Check existing documentation
- Review closed issues for similar questions

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

Thank you for contributing! 🎉

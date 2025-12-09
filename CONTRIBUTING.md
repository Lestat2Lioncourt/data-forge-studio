# Contributing to DataForge Studio

Thank you for your interest in contributing to DataForge Studio! This document provides guidelines and instructions for contributing.

## Code of Conduct

- Be respectful and constructive
- Welcome newcomers and help them get started
- Focus on what is best for the community
- Show empathy towards other community members

## How to Contribute

### Reporting Bugs

Before creating a bug report, please check the existing issues to avoid duplicates.

When reporting a bug, include:
- **Description**: Clear description of the issue
- **Steps to reproduce**: Detailed steps to recreate the bug
- **Expected behavior**: What you expected to happen
- **Actual behavior**: What actually happened
- **Environment**: OS, Python version, database type
- **Screenshots**: If applicable
- **Error messages**: Full error traceback

### Suggesting Features

Feature suggestions are welcome! Please:
- Check if the feature has already been suggested
- Provide a clear use case
- Explain why this feature would be useful
- Consider how it fits with existing features

### Pull Requests

#### Before You Start

1. **Fork** the repository
2. **Clone** your fork locally
3. **Create a branch** for your changes
   ```bash
   git checkout -b feature/your-feature-name
   ```

#### Development Setup

```bash
# Install dependencies
uv sync

# Install development dependencies
uv sync --dev

# Run tests to ensure everything works
uv run pytest
```

#### Making Changes

1. **Write clean code**
   - Follow existing code style
   - Use meaningful variable and function names
   - Add docstrings to functions and classes
   - Keep functions focused and concise

2. **Add tests**
   - Write tests for new features
   - Ensure existing tests still pass
   - Aim for good test coverage

3. **Update documentation**
   - Update README.md if needed
   - Add/update docs in `docs/` folder
   - Update CHANGELOG.md

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: add amazing feature"
   ```

   Use conventional commit messages:
   - `feat:` for new features
   - `fix:` for bug fixes
   - `docs:` for documentation changes
   - `refactor:` for code refactoring
   - `test:` for adding tests
   - `chore:` for maintenance tasks

#### Submitting Pull Request

1. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Create Pull Request**
   - Go to the original repository
   - Click "New Pull Request"
   - Select your branch
   - Fill in the PR template with:
     - Description of changes
     - Related issues (if any)
     - Testing performed
     - Screenshots (if UI changes)

3. **Wait for review**
   - Address any feedback
   - Keep the PR updated with main branch
   - Be patient and responsive

## Development Guidelines

### Code Style

- Follow PEP 8 style guide
- Use type hints where appropriate
- Maximum line length: 100 characters
- Use 4 spaces for indentation (no tabs)

### Testing

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src --cov-report=html

# Run specific test file
uv run pytest tests/test_sql_features.py

# Watch mode (if available)
uv run pytest --watch
```

### Project Structure

- `src/` - Source code
  - `core/` - Business logic
  - `ui/` - User interface components
  - `database/` - Database layer
  - `utils/` - Utility functions
  - `config/` - Configuration management
- `tests/` - Test files (mirror src structure)
- `docs/` - Documentation
- `scripts/` - Utility scripts
- `assets/` - Images, icons, resources

### Adding Dependencies

If you need to add a new dependency:

```bash
uv add package-name
```

Update `pyproject.toml` with version constraints if needed.

## Testing Database Features

When testing database features:
- Use SQLite for tests (no external setup needed)
- Mock external database connections
- Clean up test data after tests
- Don't commit test databases to git

## Documentation

- Add docstrings to all public functions and classes
- Use Google-style docstrings
- Update relevant markdown files in `docs/`
- Include code examples where helpful

Example docstring:
```python
def format_sql(query: str, style: str = "expanded") -> str:
    """
    Format SQL query with specified style.

    Args:
        query: SQL query string to format
        style: Formatting style (expanded, compact, comma_first, aligned)

    Returns:
        Formatted SQL query string

    Raises:
        ValueError: If style is not recognized

    Example:
        >>> format_sql("SELECT * FROM users", style="expanded")
        'SELECT *\\nFROM   users'
    """
    pass
```

## Release Process

(For maintainers)

1. Update version in `src/constants.py` and `pyproject.toml`
2. Update `CHANGELOG.md` with changes
3. Create git tag: `git tag -a v0.x.0 -m "Release v0.x.0"`
4. Push tag: `git push origin v0.x.0`
5. Create GitHub release from tag

## Questions?

If you have questions about contributing:
- Open a [Discussion](https://github.com/Lestat2Lioncourt/data-forge-studio/discussions)
- Ask in an issue
- Check existing documentation

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

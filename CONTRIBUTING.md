# Contributing to OpenAgent

Thank you for your interest in contributing to OpenAgent! This document provides guidelines for contributing.

## Code of Conduct

Please be respectful and constructive. We welcome contributions from everyone.

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported
2. Use the bug report template
3. Provide detailed information including:
   - Python version
   - OpenAgent version
   - Steps to reproduce
   - Expected vs actual behavior

### Suggesting Features

1. Check the issue tracker for existing suggestions
2. Provide a clear description of the feature
3. Explain why this feature would be useful

### Pull Requests

1. **Fork** the repository
2. **Create** a feature branch:
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **Make** your changes
4. **Test** your changes
5. **Commit** with clear messages:
   ```bash
   git commit -m 'Add amazing feature'
   ```
6. **Push** to your fork:
   ```bash
   git push origin feature/amazing-feature
   ```
7. **Submit** a Pull Request

## Development Setup

```bash
# Clone the repository
git clone https://github.com/none-ai/AgentCrew.git
cd AgentCrew

# Install in development mode
pip install -e .

# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest
```

## Coding Standards

- Follow PEP 8
- Use meaningful variable names
- Add docstrings to new functions
- Write tests for new features

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

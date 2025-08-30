# Contributing to Kit Gmail

Thank you for your interest in contributing to Kit Gmail! This document provides guidelines and information for contributors.

## 🎯 Ways to Contribute

### 🐛 Bug Reports
- Use the [GitHub Issues](https://github.com/rickyarm/kit_gmail/issues) page
- Include detailed steps to reproduce
- Provide system information (OS, Python version)
- Include relevant log output

### 💡 Feature Requests
- Check existing issues to avoid duplicates
- Clearly describe the proposed feature
- Explain the use case and benefits
- Consider implementation complexity

### 🔧 Code Contributions
- Bug fixes
- New features
- Performance improvements
- Documentation improvements
- Test coverage improvements

### 📚 Documentation
- README improvements
- Code documentation
- Tutorial creation
- API documentation

## 🚀 Getting Started

### Prerequisites
- Python 3.9 or higher
- Git
- Virtual environment tool (venv, conda, etc.)

### Development Setup

1. **Fork the repository**
```bash
git clone https://github.com/YOUR_USERNAME/kit_gmail.git
cd kit_gmail
```

2. **Set up development environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate
pip install -r requirements-dev.txt
pip install -e .
```

3. **Install pre-commit hooks**
```bash
pre-commit install
```

4. **Run initial tests**
```bash
pytest
```

## 🏗️ Development Workflow

### Branch Strategy
- `main` branch: Stable releases
- `develop` branch: Integration branch for features
- `feature/*` branches: Individual features
- `bugfix/*` branches: Bug fixes
- `hotfix/*` branches: Critical fixes for production

### Making Changes

1. **Create a feature branch**
```bash
git checkout -b feature/your-feature-name
```

2. **Make your changes**
- Follow the coding standards (see below)
- Add tests for new functionality
- Update documentation as needed

3. **Test your changes**
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=kit_gmail

# Run specific test categories
pytest tests/unit/
pytest tests/integration/

# Run linting
flake8 src/
mypy src/
```

4. **Commit your changes**
```bash
git add .
git commit -m "feat: add new email classification feature"
```

5. **Push and create PR**
```bash
git push origin feature/your-feature-name
```

## 📝 Coding Standards

### Code Formatting
We use automated code formatting tools:

```bash
# Format code
black .

# Sort imports
isort .

# Check formatting
black --check .
isort --check-only .
```

### Code Style Guidelines

#### Python Style
- Follow PEP 8
- Use type hints for all function parameters and return values
- Write docstrings for all public modules, functions, classes, and methods
- Use meaningful variable and function names
- Keep functions focused and small (ideally < 50 lines)

#### Docstring Format
Use Google-style docstrings:

```python
def process_email(message: Dict) -> ProcessedEmail:
    """Process a Gmail API message into a structured format.
    
    Args:
        message: Raw message from Gmail API
        
    Returns:
        ProcessedEmail object with classified data
        
    Raises:
        ProcessingError: If message format is invalid
    """
    pass
```

#### Error Handling
- Use specific exception types
- Include helpful error messages
- Log errors appropriately
- Don't swallow exceptions silently

```python
try:
    result = risky_operation()
except SpecificError as e:
    logger.error(f"Operation failed: {e}")
    raise ProcessingError(f"Failed to process data: {e}") from e
```

### Testing Guidelines

#### Test Organization
- Unit tests: `tests/unit/`
- Integration tests: `tests/integration/`
- Fixtures: `tests/conftest.py`

#### Test Naming
```python
def test_process_email_with_valid_input():
    """Test email processing with valid Gmail message."""
    pass

def test_process_email_raises_error_on_invalid_input():
    """Test that invalid input raises appropriate error."""
    pass
```

#### Test Coverage
- Aim for >90% test coverage
- Test both happy path and error cases
- Use mocks for external dependencies
- Write integration tests for complex workflows

#### Example Test
```python
def test_classify_email_as_receipt(self, sample_gmail_message):
    """Test email classification as receipt."""
    processor = EmailProcessor()
    
    # Modify message to look like a receipt
    sample_gmail_message["payload"]["headers"].append({
        "name": "Subject", 
        "value": "Your order #12345 confirmation"
    })
    
    result = processor.process_email(sample_gmail_message)
    
    assert result.is_receipt
    assert result.confidence_score > 0.6
```

## 🧪 Testing

### Running Tests
```bash
# All tests
pytest

# Specific test file
pytest tests/unit/test_email_processor.py

# Specific test function
pytest tests/unit/test_email_processor.py::TestEmailProcessor::test_process_email_basic

# With coverage
pytest --cov=kit_gmail --cov-report=html

# Parallel execution
pytest -n auto
```

### Test Categories
- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test component interactions
- **End-to-End Tests**: Test complete workflows

### Mocking Guidelines
- Mock external services (Gmail API, AI APIs)
- Mock file system operations
- Mock network requests
- Use `pytest-mock` for convenient mocking

## 📋 Pull Request Process

### Before Submitting
- [ ] Tests pass locally
- [ ] Code is formatted (black, isort)
- [ ] Linting passes (flake8, mypy)
- [ ] Documentation is updated
- [ ] CHANGELOG.md is updated (for significant changes)

### PR Title Format
Use conventional commit format:
- `feat: add new email summarization feature`
- `fix: resolve authentication token refresh issue`
- `docs: update installation instructions`
- `test: add tests for contact manager`
- `refactor: simplify email classification logic`

### PR Description Template
```markdown
## Description
Brief description of changes made.

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests added for new functionality
```

### Review Process
1. Automated checks must pass (CI/CD)
2. Code review by maintainer(s)
3. Address feedback and make changes
4. Approval and merge

## 🔧 Development Tools

### Recommended IDE Setup
- **VS Code** with extensions:
  - Python
  - Pylance
  - Black Formatter
  - isort
  - GitLens

### Debugging
- Use `pytest --pdb` for test debugging
- Set up IDE debugging configuration
- Use logging for production debugging

### Performance Profiling
```bash
# Profile specific functions
python -m cProfile -s cumulative script.py

# Memory profiling
pip install memory-profiler
python -m memory_profiler script.py
```

## 📚 Architecture Guidelines

### Adding New Features

#### Core Components
- **Email Processing**: Add to `core/email_processor.py`
- **Gmail Operations**: Add to `core/gmail_manager.py`
- **AI Integration**: Add to `services/ai_service.py`
- **Contact Management**: Add to `services/contact_manager.py`

#### CLI Commands
1. Create command module in `cli/commands/`
2. Add to main CLI app in `cli/main.py`
3. Follow existing command patterns

#### Configuration
- Add settings to `utils/config.py`
- Update `.env.example`
- Document in README.md

### Database Changes
- Use SQLite migrations for schema changes
- Maintain backward compatibility
- Update database initialization code

### Security Considerations
- Never log sensitive data
- Use secure storage for credentials
- Validate all user inputs
- Follow principle of least privilege

## 📋 Issue Labels

We use the following labels to categorize issues:

- `bug`: Something isn't working
- `enhancement`: New feature or request
- `documentation`: Improvements or additions to docs
- `good first issue`: Good for newcomers
- `help wanted`: Extra attention is needed
- `question`: Further information is requested
- `wontfix`: This will not be worked on
- `duplicate`: This issue or PR already exists

## 🎯 Coding Best Practices

### Error Handling
```python
# Good
try:
    result = api_call()
except APIError as e:
    logger.error(f"API call failed: {e}")
    raise EmailProcessingError("Failed to fetch emails") from e

# Bad
try:
    result = api_call()
except:
    pass
```

### Logging
```python
# Good
logger.info(f"Processing {len(emails)} emails")
logger.debug(f"Email content: {email.subject}")
logger.error(f"Failed to process email {email.id}: {error}")

# Bad
print("Processing emails")
```

### Configuration
```python
# Good
from kit_gmail.utils.config import settings

max_emails = settings.max_email_batch_size

# Bad
max_emails = 100  # Hard-coded value
```

### Type Hints
```python
# Good
def process_emails(emails: List[Dict]) -> List[ProcessedEmail]:
    """Process a list of Gmail messages."""
    return [process_email(email) for email in emails]

# Bad
def process_emails(emails):
    return [process_email(email) for email in emails]
```

## 🚀 Release Process

### Version Numbering
We follow [Semantic Versioning](https://semver.org/):
- `MAJOR.MINOR.PATCH`
- Major: Breaking changes
- Minor: New features (backward compatible)
- Patch: Bug fixes

### Release Checklist
- [ ] Update version in `pyproject.toml`
- [ ] Update CHANGELOG.md
- [ ] Run full test suite
- [ ] Update documentation
- [ ] Create release tag
- [ ] Build and publish to PyPI

## ❓ Questions?

- **General Questions**: [GitHub Discussions](https://github.com/rickyarm/kit_gmail/discussions)
- **Bug Reports**: [GitHub Issues](https://github.com/rickyarm/kit_gmail/issues)
- **Security Issues**: Email rickyarm@users.noreply.github.com

Thank you for contributing to Kit Gmail! 🎉
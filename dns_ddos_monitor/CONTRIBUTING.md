# Contributing to DNS DDoS Monitor

Thank you for your interest in contributing to DNS DDoS Monitor! This document provides guidelines for contributing to the project.

## 🤝 How to Contribute

### Reporting Issues
- Use the GitHub issue tracker to report bugs
- Include detailed information about your environment
- Provide steps to reproduce the issue
- Include relevant log files or error messages

### Suggesting Features
- Open an issue with the "enhancement" label
- Describe the feature and its use case
- Explain how it would benefit users
- Consider implementation complexity

### Code Contributions

#### Getting Started
1. Fork the repository
2. Clone your fork locally
3. Create a new branch for your feature/fix
4. Make your changes
5. Test your changes thoroughly
6. Submit a pull request

#### Development Setup
```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/dns-ddos-monitor.git
cd dns-ddos-monitor

# Install dependencies
pip3 install -r requirements.txt

# Install development dependencies
pip3 install pytest black flake8

# Run tests
python3 test_system.py
```

#### Code Standards

##### Python Style
- Follow PEP 8 style guide
- Use meaningful variable and function names
- Add docstrings to all functions and classes
- Keep functions focused and concise

##### Code Formatting
```bash
# Format code with black
black dns_ddos_monitor/

# Check code style
flake8 dns_ddos_monitor/

# Run tests
pytest tests/
```

##### Documentation
- Update README.md for new features
- Add inline comments for complex logic
- Include examples in docstrings
- Update configuration documentation

#### Commit Guidelines
- Use clear, descriptive commit messages
- Start with a verb (Add, Fix, Update, Remove)
- Keep the first line under 50 characters
- Include details in the body if needed

Example:
```
Add DGA detection for new malware family

- Implement pattern matching for XYZ malware
- Update classifier with new features
- Add unit tests for new detection logic
```

#### Pull Request Process
1. Ensure your code follows the style guidelines
2. Add or update tests for your changes
3. Update documentation as needed
4. Ensure all tests pass
5. Create a clear PR description explaining:
   - What changes were made
   - Why they were made
   - How to test them

## 🧪 Testing

### Running Tests
```bash
# Run system tests
python3 test_system.py

# Run specific component tests
python3 -m pytest tests/test_log_reader.py

# Run with coverage
python3 -m pytest --cov=core tests/
```

### Adding Tests
- Write tests for new features
- Include edge cases and error conditions
- Use descriptive test names
- Follow the existing test structure

### Test Structure
```python
def test_feature_name():
    """Test description"""
    # Arrange
    setup_test_data()
    
    # Act
    result = function_under_test()
    
    # Assert
    assert result == expected_value
```

## 📋 Development Guidelines

### Adding New Detection Methods
1. Extend the `ThresholdDetector` class
2. Add configuration options to `monitor_config.json`
3. Include comprehensive logging
4. Add unit tests
5. Update documentation

### Modifying Core Components
- Maintain backward compatibility when possible
- Update configuration schema if needed
- Test with existing configurations
- Document breaking changes

### Performance Considerations
- Profile code for performance bottlenecks
- Avoid blocking operations in main loop
- Use efficient data structures
- Consider memory usage for large deployments

## 🐛 Bug Reports

### Before Reporting
- Check existing issues for duplicates
- Try the latest version
- Test with minimal configuration
- Gather relevant system information

### Bug Report Template
```
**Environment:**
- OS: [e.g., Ubuntu 20.04]
- Python version: [e.g., 3.8.5]
- DNS DDoS Monitor version: [e.g., 1.0.0]

**Description:**
Clear description of the bug

**Steps to Reproduce:**
1. Step one
2. Step two
3. Step three

**Expected Behavior:**
What should happen

**Actual Behavior:**
What actually happens

**Logs:**
Relevant log files or error messages

**Additional Context:**
Any other relevant information
```

## 🚀 Feature Requests

### Feature Request Template
```
**Feature Description:**
Clear description of the proposed feature

**Use Case:**
Why is this feature needed?

**Proposed Implementation:**
How should this feature work?

**Alternatives Considered:**
Other approaches you've considered

**Additional Context:**
Screenshots, mockups, or examples
```

## 📖 Documentation

### Types of Documentation
- Code comments and docstrings
- README and setup guides
- API documentation
- Configuration reference
- Troubleshooting guides

### Documentation Standards
- Use clear, concise language
- Include examples where helpful
- Keep documentation up to date
- Test all examples and commands

## 🏷️ Release Process

### Version Numbering
We use [Semantic Versioning](https://semver.org/):
- MAJOR.MINOR.PATCH
- MAJOR: Breaking changes
- MINOR: New features (backward compatible)
- PATCH: Bug fixes (backward compatible)

### Release Checklist
- [ ] Update version numbers
- [ ] Update CHANGELOG.md
- [ ] Run full test suite
- [ ] Update documentation
- [ ] Create release notes
- [ ] Tag release in Git

## 🤔 Questions?

If you have questions about contributing:
- Check the existing documentation
- Search through issues
- Open a new issue with the "question" label
- Join our community discussions

## 📜 Code of Conduct

### Our Standards
- Be respectful and inclusive
- Focus on constructive feedback
- Help create a welcoming environment
- Respect different viewpoints and experiences

### Unacceptable Behavior
- Harassment or discrimination
- Trolling or insulting comments
- Personal attacks
- Publishing private information

### Enforcement
Project maintainers are responsible for clarifying standards and may take action including warning, temporary ban, or permanent ban for inappropriate behavior.

---

Thank you for contributing to DNS DDoS Monitor! Your efforts help make DNS security better for everyone. 🛡️
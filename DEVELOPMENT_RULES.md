# Development Rules and Guidelines - Quick Reference

## 📌 IMPORTANT: Review Before ANY Action

This file serves as a quick reference checkpoint. Always review relevant sections before:
- Creating branches
- Making commits
- Modifying code
- Running tests
- Pushing to remote

---

## 🔄 Git Workflow Rules (MANDATORY)

### Branching Strategy
✅ **DO:**
- Create feature branches from `dev`: `git checkout -b feature/feature-name`
- Use descriptive branch names: `feature/pytest-infrastructure`, `feature/add-cli-tests`
- After completion, rename to: `feature/done/feature-name`
- Merge to `dev` for testing, then to `main` for production

❌ **DON'T:**
- Never commit directly to `main`
- Never commit directly to `dev` (use feature branches)
- Never use vague branch names: `fix`, `update`, `test`

### Commit Guidelines
✅ **DO:**
- Write descriptive commit messages (50 char summary, detailed body)
- Make atomic commits (one logical change per commit)
- Follow conventional commits: `feat:`, `fix:`, `test:`, `docs:`, `refactor:`
- Include relevant issue numbers: `Fixes #123`

❌ **DON'T:**
- Never commit secrets, credentials, or API keys
- Never commit generated files (coverage reports, __pycache__)
- Never use vague messages: "fix bug", "update", "wip"

### Example Good Commit:
```
Add comprehensive pytest infrastructure with 120+ test cases

- Created test directory structure (unit/, integration/, fixtures/, performance/)
- Implemented 120+ test cases covering core modules
- Configured pytest.ini with coverage settings
- Added conftest.py with extensive fixture library
- Updated dev_requirements.txt with testing dependencies

Targets 80%+ coverage. Current: 47.34%
```

---

## 🧪 Testing Rules (MANDATORY)

### Before Committing
✅ **MUST DO:**
1. Run relevant tests: `pytest tests/unit/test_<module>.py`
2. Check coverage doesn't decrease: `pytest --cov=. --cov-report=term`
3. Fix all test failures before committing
4. Ensure new code has accompanying tests

### Test Coverage Requirements
- **Minimum**: 80% overall coverage
- **New code**: Must have tests before commit
- **Bug fixes**: Must include regression test

### Test Structure
```
tests/
├── unit/           # Test individual functions
├── integration/    # Test workflows
├── performance/    # Benchmarks
└── fixtures/       # Sample data
```

---

## 💻 Code Quality Rules

### Python Standards (PEP 8)
✅ **DO:**
- Use type hints: `def function(arg: str) -> int:`
- Write docstrings (Google/NumPy style)
- Keep functions short (<10 lines preferred)
- One function, one responsibility
- Use meaningful variable names

❌ **DON'T:**
- No hardcoded values (use constants)
- No commented-out code
- No unused imports
- No `print()` for debugging (use logging)

### Lean Coding Principles
1. "The best code is no code at all"
2. "Simplicity is the ultimate sophistication"
3. "Write code for humans, not machines"

---

## 🐍 Dependency Management

### Before Installing
✅ **DO:**
- Check compatibility: Python 3.11+
- Use virtual environment
- Document in requirements.txt
- Pin versions for production

⚠️ **KNOWN ISSUES:**
- Pandas 3.0: Use `freq='h'` (lowercase) not `'H'`
- VirtualiZarr: Import from `obspec_utils.registry` not `virtualizarr.registry`

### Installation Command:
```bash
source ../ngs-flight-planning-venv/bin/activate
pip install -r requirements.txt
pip install -r dev_requirements.txt  # For testing
```

---

## 📝 Documentation Rules

### What to Document
✅ **MUST:**
- All public functions (docstrings)
- Complex algorithms (inline comments)
- Breaking changes (CHANGELOG.md)
- New features (README.md)
- API changes (API docs)

### Docstring Template:
```python
def function(param: type) -> return_type:
    """Brief description.
    
    Longer description if needed.
    
    Parameters
    ----------
    param : type
        Description of param.
    
    Returns
    -------
    return_type
        Description of return value.
    """
```

---

## 🔒 Security Rules (CRITICAL)

❌ **NEVER:**
- Commit secrets, API keys, passwords
- Commit `.env` files or credentials
- Use hardcoded credentials
- Expose sensitive data in logs

✅ **ALWAYS:**
- Use environment variables
- Add sensitive files to `.gitignore`
- Validate all user inputs
- Handle errors gracefully

---

## 🚀 Pull Request Process

### Before Creating PR
1. ✅ All tests passing
2. ✅ Coverage at or above 80%
3. ✅ Code formatted (black, isort)
4. ✅ Linting passes (flake8, pylint)
5. ✅ Documentation updated
6. ✅ CHANGELOG.md updated

### PR Requirements
- Descriptive title and description
- Link to related issues
- At least one code review required
- All CI/CD checks must pass
- Squash commits before merge

---

## 📊 Current Project Status

### Test Coverage: 47.34% ⚠️
**Target**: 80%

**Excellent Coverage (>90%)**:
- ✅ utils.py (100%)
- ✅ inputs.py (97%)

**Critical Gaps (<50%)**:
- 🔴 predict.py (0%)
- 🔴 qc.py (0%)
- 🔴 outputs.py (7%)
- 🔴 mesh_handling.py (22%)

### Known Issues to Fix:
1. **Pandas 3.0 compatibility**: 13 tests failing (easy fix)
2. **VirtualiZarr deprecation**: 1 warning (easy fix)
3. **Coverage gaps**: Need tests for CLI modules

---

## ⚡ Quick Action Checklist

### Before ANY Code Change:
- [ ] Read relevant section above
- [ ] Understand the change needed
- [ ] Create feature branch from `dev`
- [ ] Write tests first (TDD approach)
- [ ] Make minimal changes needed
- [ ] Run tests locally
- [ ] Check coverage
- [ ] Update documentation
- [ ] Commit with descriptive message
- [ ] Push feature branch
- [ ] Create PR when ready

### Before ANY Commit:
- [ ] Tests passing: `pytest tests/`
- [ ] No secrets in code
- [ ] Linting clean
- [ ] Docs updated
- [ ] Descriptive commit message

### Before ANY Push:
- [ ] All commits follow guidelines
- [ ] Feature complete and tested
- [ ] Ready for code review
- [ ] No WIP commits

---

## 🆘 When in Doubt

1. **Read the guide**: `docs/guides/development-best-practices.md`
2. **Check examples**: Look at existing tests
3. **Ask for review**: Better to ask than to break
4. **Small changes**: Easier to review and test
5. **Test everything**: If it can break, test it

---

## 📞 Getting Help

- **Documentation issues**: Open GitHub issue with `documentation` label
- **Test failures**: Check `DEPENDENCY_AND_TESTING_ANALYSIS_REPORT.md`
- **Git workflow**: Review `docs/guides/development-best-practices.md`
- **General questions**: nos.modeling@noaa.gov

---

## 🎯 Remember

> "Quality over quantity"  
> "Test before commit"  
> "Document as you go"  
> "Review the rules before acting"

**This file should be your first stop before any development work!**

---

**Last Updated**: 2026-05-06  
**Version**: 1.0  
**Review Status**: Mandatory before all actions

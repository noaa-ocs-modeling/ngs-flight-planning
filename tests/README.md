# NGS Flight Planning - Pytest Infrastructure

## Overview
Comprehensive pytest infrastructure for NGS Flight Planning Software with 80%+ test coverage goal.

## Directory Structure
```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures and pytest configuration
├── unit/                    # Unit tests for individual modules
│   ├── test_utils.py        # Tests for utils.py
│   ├── test_inputs.py       # Tests for inputs.py
│   ├── test_processing.py   # Tests for processing.py
│   ├── test_mesh_handling.py # Tests for mesh_handling.py
│   └── test_outputs.py      # Tests for outputs.py
├── integration/             # Integration tests for workflows
│   ├── test_predict_workflow.py
│   └── test_qc_workflow.py
├── fixtures/                # Sample test data files
│   ├── sample_lines.wpt
│   ├── sample_images_field.csv
│   └── sample_images_final.csv
└── performance/             # Performance benchmarks
    └── test_performance.py
```

## Running Tests

### Install Testing Dependencies
```bash
pip install -r dev_requirements.txt
```

### Run All Tests
```bash
pytest
```

### Run with Coverage Report
```bash
pytest --cov=. --cov-report=html
```

### Run Specific Test Categories
```bash
# Unit tests only
pytest -m unit

# Integration tests only
pytest -m integration

# Exclude slow tests
pytest -m "not slow"

# Performance benchmarks
pytest -m performance
```

### Run Specific Test Files
```bash
pytest tests/unit/test_utils.py
pytest tests/unit/test_inputs.py
pytest tests/integration/test_predict_workflow.py
```

### Run with Parallel Execution
```bash
pytest -n auto
```

## Test Markers
- `@pytest.mark.unit` - Unit tests for individual functions
- `@pytest.mark.integration` - Integration tests for workflows
- `@pytest.mark.slow` - Tests that take significant time
- `@pytest.mark.performance` - Performance benchmarks

## Coverage Goals
- **Target**: 80%+ overall coverage
- **Priority modules**: utils.py, inputs.py, processing.py (aim for 90%+)
- **Complex modules**: mesh_handling.py, outputs.py (aim for 70%+)

## Test Data
Sample test data is provided in `tests/fixtures/`:
- `sample_lines.wpt` - Sample flight lines in waypoint format
- `sample_images_field.csv` - Sample field QC images
- `sample_images_final.csv` - Sample final QC images

## Fixtures
Common fixtures are defined in `tests/conftest.py`:
- `sample_lines_gdf` - GeoDataFrame with flight lines
- `sample_images_field_csv` - Path to field images CSV
- `sample_images_final_csv` - Path to final images CSV
- `sample_xarray_dataset` - Mock xarray Dataset
- `mock_stofs_data` - Mock STOFS forecast data
- `temp_output_dir` - Temporary directory for test outputs

## Continuous Integration
The test suite is designed to integrate with CI/CD pipelines:
- Fast unit tests run on every commit
- Integration tests run on pull requests
- Performance benchmarks run nightly/weekly

## Coverage Report
After running tests with coverage:
```bash
pytest --cov=. --cov-report=html
```

Open `htmlcov/index.html` to view the detailed coverage report.

## Known Limitations
1. Some integration tests require S3 access and are skipped by default
2. Full workflow tests require external data sources
3. Performance benchmarks may vary based on system resources

## Future Enhancements
- [ ] Add property-based testing with Hypothesis
- [ ] Expand integration tests with full workflow coverage
- [ ] Add mutation testing for test quality assessment
- [ ] Implement visual regression tests for output formats
- [ ] Add load testing for large datasets

## Contributing
When adding new code:
1. Write unit tests for new functions
2. Update integration tests if workflows change
3. Add fixtures for new data formats
4. Ensure coverage stays above 80%
5. Run full test suite before committing

## Getting Help
- Check pytest documentation: https://docs.pytest.org
- Review test examples in `tests/unit/`
- Refer to `conftest.py` for available fixtures

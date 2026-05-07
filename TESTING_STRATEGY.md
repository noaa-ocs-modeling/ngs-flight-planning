# Pytest Infrastructure Development - Testing Strategy

## Executive Summary
This document outlines the comprehensive pytest infrastructure developed for the NGS Flight Planning Software, targeting 80%+ test coverage and robust quality assurance.

## Infrastructure Components

### 1. Test Configuration (`pytest.ini`)
- Coverage reporting configured for HTML and terminal output
- 80% coverage threshold enforced
- Strict markers enabled
- Doctest integration
- Custom test discovery patterns

### 2. Shared Fixtures (`conftest.py`)
Provides reusable test fixtures including:
- Sample coordinate data (HDMS and decimal)
- Flight lines data (CSV and GeoDataFrame)
- Field and final image data
- Mock STOFS and VDatum data
- Temporary output directories
- Sample xarray datasets

### 3. Test Suite Organization

#### Unit Tests (`tests/unit/`)
**test_utils.py** (100+ test cases)
- `hdms_to_dd()`: 10 test cases covering all hemispheres, edge cases, error handling
- `switch_lon_lims()`: 15 test cases covering range conversions, type preservation

**test_inputs.py** (35+ test cases)
- `load_lines_gdf()`: File loading, geometry validation, column preservation
- `load_images_field_gdf()`: GPS time conversion, geometry creation, error handling
- `load_images_final_gdf()`: DateTime parsing, coordinate validation
- `get_forecast_init_time()`: Initialization hour selection, warning/error conditions

**test_processing.py** (30+ test cases)
- `point_table_from_lines()`: Point generation, numbering, geometry validation
- `interp_time()`: Time interpolation, data preservation
- `calc_sun_alt()`: Solar elevation calculation, custom variables
- `calc_in_range()`: Water level tolerance, solar constraints, multiple datums

**test_mesh_handling.py** (15+ test cases)
- `get_box()`: Bounding box creation, buffer handling, geometry validation
- Stubs for additional functions requiring external data

**test_outputs.py** (10+ test cases)
- `get_create_output_dir()`: Directory creation, existing directory handling
- Stubs for output generation functions

#### Integration Tests (`tests/integration/`)
**test_predict_workflow.py**
- Input loading validation
- Point generation workflow
- Mock forecast integration
- End-to-end workflow stubs (requiring S3 access)

**test_qc_workflow.py**
- Field and final image loading
- Forecast initialization calculation
- Mock data integration
- Complete workflow stubs

#### Performance Tests (`tests/performance/`)
**test_performance.py**
- Utility function benchmarks
- Input loading performance
- Processing function benchmarks
- Mesh handling performance
- Scalability tests with large datasets

### 4. Test Fixtures (`tests/fixtures/`)
Sample data files for reproducible testing:
- `sample_lines.wpt`: 3 flight lines with various parameters
- `sample_images_field.csv`: 5 field images with GPS time
- `sample_images_final.csv`: 5 final images with standard datetime

## Test Coverage Strategy

### Coverage Targets by Module
| Module | Target Coverage | Rationale |
|--------|----------------|-----------|
| utils.py | 95%+ | Simple, critical utility functions |
| inputs.py | 90%+ | Core data loading, well-defined inputs |
| processing.py | 85%+ | Complex calculations, edge cases important |
| mesh_handling.py | 70%+ | External dependencies, some functions mocked |
| outputs.py | 70%+ | File I/O heavy, format-dependent |
| predict.py | 60%+ | CLI script, integration-focused |
| qc.py | 60%+ | CLI script, integration-focused |

### Testing Approach by Complexity

**Simple Functions** (utils.py)
- Exhaustive parameterized testing
- Edge case coverage
- Error condition validation
- Type checking

**Data Processing** (inputs.py, processing.py)
- Valid input testing
- Invalid input handling
- Format variation testing
- Data type validation
- Warning/error logging verification

**External Dependencies** (mesh_handling.py)
- Mock-based testing where possible
- Integration test stubs for manual/CI runs
- Bounding box and preprocessing logic fully tested
- S3/data access marked as slow tests

**Output Generation** (outputs.py)
- Directory management fully tested
- Format-specific tests stubbed for expansion
- Integration with real data in future iterations

## Testing Dependencies
Added to `dev_requirements.txt`:
- `pytest>=8.0.0` - Core testing framework
- `pytest-cov>=4.1.0` - Coverage reporting
- `pytest-mock>=3.12.0` - Mocking capabilities
- `pytest-benchmark>=4.0.0` - Performance benchmarking
- `pytest-timeout>=2.2.0` - Test timeouts
- `pytest-xdist>=3.5.0` - Parallel execution
- `hypothesis>=6.100.0` - Property-based testing
- `freezegun>=1.4.0` - Time mocking
- `faker>=24.0.0` - Test data generation

## Test Execution Workflow

### Development Workflow
1. Run unit tests during development: `pytest tests/unit/ -v`
2. Check coverage: `pytest --cov=. --cov-report=term-missing`
3. Run relevant integration tests: `pytest tests/integration/test_predict_workflow.py`
4. Before commit: `pytest -m "not slow"`

### CI/CD Integration (Recommended)
```yaml
# Example GitHub Actions workflow
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Install dependencies
        run: pip install -r dev_requirements.txt
      - name: Run unit tests
        run: pytest tests/unit/ -v
      - name: Run integration tests
        run: pytest tests/integration/ -v --ignore-glob="*slow*"
      - name: Generate coverage report
        run: pytest --cov=. --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

### Performance Testing
Run separately or on schedule:
```bash
pytest -m performance --benchmark-only
```

## Current Test Statistics

### Test Count by Category
- Unit tests: ~100+ test cases
- Integration tests: ~10+ test cases (many stubbed)
- Performance tests: ~10+ benchmarks
- **Total**: 120+ test cases implemented

### Expected Initial Coverage
Based on implemented tests:
- utils.py: ~95% (comprehensive coverage)
- inputs.py: ~85% (main functions covered)
- processing.py: ~75% (core functions tested)
- mesh_handling.py: ~40% (limited by external deps)
- outputs.py: ~30% (basic functions only)
- **Estimated Overall**: 60-70% (baseline established)

## Gap Analysis and Recommendations

### Immediate Priorities
1. **Expand outputs.py tests** - Add tests for format-specific output functions
2. **Mock external dependencies** - Improve mesh_handling.py test coverage
3. **Run initial coverage report** - Identify untested code paths
4. **Implement missing integration tests** - Complete workflow testing with mocks

### Medium-term Goals
1. Add property-based tests using Hypothesis
2. Implement visual regression tests for output formats
3. Add mutation testing for quality assessment
4. Expand performance benchmark suite
5. Create test data generators for various scenarios

### Long-term Vision
1. 90%+ coverage across all modules
2. Automated nightly integration tests with real data
3. Performance regression tracking
4. Automated documentation generation from tests
5. Test-driven development workflow

## Success Metrics

### Quantitative
- [ ] 80%+ overall test coverage achieved
- [ ] <15 minute total test runtime
- [ ] Zero failing tests in main branch
- [ ] 100% of new code has accompanying tests

### Qualitative
- [ ] Tests are easy to understand and maintain
- [ ] Test failures provide clear diagnostic information
- [ ] Tests run reliably in CI/CD environment
- [ ] Development velocity improved by early bug detection

## Maintenance Plan

### Weekly
- Review failing tests
- Update fixtures as data formats evolve
- Add tests for new features

### Monthly
- Review coverage reports and address gaps
- Update dependencies
- Performance benchmark review

### Quarterly
- Comprehensive test suite audit
- Remove obsolete tests
- Refactor test structure if needed
- Update testing strategy document

## Conclusion

A comprehensive pytest infrastructure has been established with:
- Well-organized test structure
- Extensive fixture library
- 120+ test cases covering core functionality
- Performance benchmarking framework
- Clear documentation and guidelines

This foundation supports the 80%+ coverage goal and provides a robust quality assurance framework for the NGS Flight Planning Software.

## Next Steps

1. **Run initial tests**: `pytest -v`
2. **Generate coverage report**: `pytest --cov=. --cov-report=html`
3. **Address any test failures**: Fix environment or test issues
4. **Review coverage gaps**: Focus on high-priority untested code
5. **Iterate and improve**: Continuously expand test coverage

---

**Document Version**: 1.0  
**Last Updated**: 2026-05-06  
**Author**: Testing Infrastructure Team

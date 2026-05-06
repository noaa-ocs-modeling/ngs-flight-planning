"""Unit tests for utils.py module."""

import pytest
import numpy as np
from utils import hdms_to_dd, switch_lon_lims


@pytest.mark.unit
class TestHdmsToDd:
    """Test cases for hdms_to_dd function."""
    
    def test_western_hemisphere(self):
        """Test conversion of Western hemisphere coordinates."""
        result = hdms_to_dd('W80 30 15')
        expected = -80.50416667
        assert abs(result - expected) < 1e-6
    
    def test_eastern_hemisphere(self):
        """Test conversion of Eastern hemisphere coordinates."""
        result = hdms_to_dd('E10 15 30')
        expected = 10.25833333
        assert abs(result - expected) < 1e-6
    
    def test_northern_hemisphere(self):
        """Test conversion of Northern hemisphere coordinates."""
        result = hdms_to_dd('N25 45 30')
        expected = 25.75833333
        assert abs(result - expected) < 1e-6
    
    def test_southern_hemisphere(self):
        """Test conversion of Southern hemisphere coordinates."""
        result = hdms_to_dd('S15 30 45')
        expected = -15.5125
        assert abs(result - expected) < 1e-6
    
    def test_zero_minutes_seconds(self):
        """Test conversion with zero minutes and seconds."""
        result = hdms_to_dd('N45 0 0')
        expected = 45.0
        assert abs(result - expected) < 1e-6
    
    def test_max_minutes_seconds(self):
        """Test conversion with maximum minutes and seconds."""
        result = hdms_to_dd('N45 59 59')
        expected = 45.99972222
        assert abs(result - expected) < 1e-6
    
    def test_invalid_hemisphere(self):
        """Test that invalid hemisphere raises ValueError."""
        with pytest.raises(ValueError, match='Location string must be formatted'):
            hdms_to_dd('X45 30 15')
    
    def test_extra_whitespace(self):
        """Test handling of extra whitespace."""
        result = hdms_to_dd('  W80 30 15  ')
        expected = -80.50416667
        assert abs(result - expected) < 1e-6
    
    def test_single_digit_components(self):
        """Test conversion with single digit components."""
        result = hdms_to_dd('N5 5 5')
        expected = 5.08472222
        assert abs(result - expected) < 1e-6
    
    @pytest.mark.parametrize('hdms_str,expected', [
        ('W80 30 15', -80.50416667),
        ('E10 15 30', 10.25833333),
        ('N25 45 30', 25.75833333),
        ('S15 30 45', -15.5125),
        ('W0 0 0', 0.0),
        ('E180 0 0', 180.0),
    ])
    def test_multiple_coordinates(self, hdms_str, expected):
        """Test multiple coordinate conversions."""
        result = hdms_to_dd(hdms_str)
        assert abs(result - expected) < 1e-6


@pytest.mark.unit
class TestSwitchLonLims:
    """Test cases for switch_lon_lims function."""
    
    def test_default_min_lon(self):
        """Test conversion with default min_lon (0.0)."""
        lon_array = np.array([-180, -90, 0, 90, 180])
        result = switch_lon_lims(lon_array)
        expected = np.array([180, 270, 0, 90, 180])
        np.testing.assert_array_almost_equal(result, expected)
    
    def test_negative_180_min_lon(self):
        """Test conversion with min_lon = -180.0."""
        lon_array = np.array([0, 90, 180, 270, 360])
        result = switch_lon_lims(lon_array, min_lon=-180.0)
        expected = np.array([0, 90, -180, -90, 0])
        np.testing.assert_array_almost_equal(result, expected)
    
    def test_single_value(self):
        """Test conversion of a single longitude value."""
        result = switch_lon_lims(-170)
        expected = 190
        assert abs(result - expected) < 1e-6
    
    def test_numpy_array_input(self):
        """Test conversion with numpy array input."""
        lon_array = np.array([-180, -90, 0, 90, 180])
        result = switch_lon_lims(lon_array)
        expected = np.array([180, 270, 0, 90, 180])
        np.testing.assert_array_almost_equal(result, expected)
    
    def test_list_input(self):
        """Test conversion with list input (converts to array)."""
        lon_list = [-180, -90, 0, 90, 180]
        lon_array = np.array(lon_list)
        result = switch_lon_lims(lon_array)
        expected = np.array([180, 270, 0, 90, 180])
        np.testing.assert_array_almost_equal(result, expected)
    
    def test_float_input(self):
        """Test conversion with float input."""
        result = switch_lon_lims(-170.5)
        expected = 189.5
        assert abs(result - expected) < 1e-6
    
    def test_values_already_in_range(self):
        """Test values already in target range."""
        lon_array = np.array([0, 90, 180, 270, 360])
        result = switch_lon_lims(lon_array, min_lon=0.0)
        expected = np.array([0, 90, 180, 270, 0])
        np.testing.assert_array_almost_equal(result, expected)
    
    def test_negative_values_to_0_360(self):
        """Test conversion of negative values to [0, 360) range."""
        lon_array = np.array([-90, -45, -10])
        result = switch_lon_lims(lon_array, min_lon=0.0)
        expected = np.array([270, 315, 350])
        np.testing.assert_array_almost_equal(result, expected)
    
    def test_large_positive_values(self):
        """Test conversion of values > 360."""
        lon_array = np.array([370, 450, 720])
        result = switch_lon_lims(lon_array, min_lon=0.0)
        expected = np.array([10, 90, 0])
        np.testing.assert_array_almost_equal(result, expected)
    
    def test_large_negative_values(self):
        """Test conversion of values < -360."""
        lon_array = np.array([-370, -450, -720])
        result = switch_lon_lims(lon_array, min_lon=-180.0)
        expected = np.array([-10, -90, 0])
        np.testing.assert_array_almost_equal(result, expected)
    
    @pytest.mark.parametrize('lon,min_lon,expected', [
        (-180, 0.0, 180),
        (180, -180.0, -180),
        (0, 0.0, 0),
        (-90, 0.0, 270),
        (270, -180.0, -90),
        (360, 0.0, 0),
        (360, -180.0, 0),
    ])
    def test_parameterized_conversions(self, lon, min_lon, expected):
        """Test various longitude conversions with different min_lon values."""
        result = switch_lon_lims(lon, min_lon=min_lon)
        assert abs(result - expected) < 1e-6
    
    def test_preserves_type(self):
        """Test that numpy array operations work correctly."""
        # Test with numpy array
        lon_array = np.array([-180, 0, 180])
        result_array = switch_lon_lims(lon_array)
        assert isinstance(result_array, np.ndarray)
        
        # Test with float
        lon_float = -180.0
        result_float = switch_lon_lims(lon_float)
        assert isinstance(result_float, (int, float, np.number))
    
    def test_empty_array(self):
        """Test conversion of empty array."""
        lon_array = np.array([])
        result = switch_lon_lims(lon_array)
        assert len(result) == 0
    
    def test_decimal_precision(self):
        """Test that decimal precision is maintained."""
        lon = -80.12345678
        result = switch_lon_lims(lon, min_lon=0.0)
        expected = 279.87654322
        assert abs(result - expected) < 1e-6

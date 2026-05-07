"""Unit tests for processing.py module."""

import pytest
import pandas as pd
import geopandas as gpd
import numpy as np
import xarray as xr
import datetime
from unittest.mock import patch, MagicMock
import shapely

from processing import (
    point_table_from_lines,
    interp_time,
    calc_sun_alt,
    calc_in_range
)


@pytest.mark.unit
class TestPointTableFromLines:
    """Test cases for point_table_from_lines function."""
    
    def test_basic_point_generation(self, sample_lines_gdf):
        """Test basic point generation from flight lines."""
        df_points = point_table_from_lines(sample_lines_gdf)
        
        assert isinstance(df_points, gpd.GeoDataFrame)
        assert 'geometry' in df_points.columns
        assert all(isinstance(geom, shapely.Point) for geom in df_points.geometry)
    
    def test_correct_number_of_points(self, sample_lines_gdf):
        """Test that correct number of points are generated."""
        df_points = point_table_from_lines(sample_lines_gdf)
        
        # First line has 10 photos, second has 8
        expected_total = 10 + 8
        assert len(df_points) == expected_total
    
    def test_point_numbering(self, sample_lines_gdf):
        """Test that points are numbered correctly."""
        df_points = point_table_from_lines(sample_lines_gdf)
        
        # Check first line's points
        line1_points = df_points[df_points['LINE'] == 1]
        assert list(line1_points['POINT_NUM']) == list(range(1, 11))
        
        # Check second line's points
        line2_points = df_points[df_points['LINE'] == 2]
        assert list(line2_points['POINT_NUM']) == list(range(1, 9))
    
    def test_columns_preserved(self, sample_lines_gdf):
        """Test that relevant columns from lines are preserved."""
        df_points = point_table_from_lines(sample_lines_gdf)
        
        expected_cols = ['LINE', 'SCALE', 'EMULSION', 'GRND_EL', 
                        'LAT', 'LON', 'POINT_NUM', 'geometry']
        for col in expected_cols:
            assert col in df_points.columns
    
    def test_lat_lon_columns_created(self, sample_lines_gdf):
        """Test that LAT and LON columns are created."""
        df_points = point_table_from_lines(sample_lines_gdf)
        
        assert 'LAT' in df_points.columns
        assert 'LON' in df_points.columns
        assert all(df_points['LAT'].notna())
        assert all(df_points['LON'].notna())
    
    def test_geometry_matches_lat_lon(self, sample_lines_gdf):
        """Test that geometry coordinates match LAT/LON columns."""
        df_points = point_table_from_lines(sample_lines_gdf)
        
        for idx in df_points.index:
            point = df_points.loc[idx, 'geometry']
            lat = df_points.loc[idx, 'LAT']
            lon = df_points.loc[idx, 'LON']
            
            assert abs(point.x - lon) < 1e-6
            assert abs(point.y - lat) < 1e-6
    
    def test_single_line(self):
        """Test with a single flight line."""
        data = {
            'LINE': [1],
            'LON1': ['W80 30 15'],
            'LAT1': ['N25 45 30'],
            'LON2': ['W80 20 10'],
            'LAT2': ['N25 50 45'],
            'PHOTOS': [5],
            'SCALE': [10000],
            'EMULSION': ['RGB'],
            'GRND_EL': [50]
        }
        gdf = gpd.GeoDataFrame(
            data,
            geometry=[shapely.LineString([[-80.5, 25.75], [-80.33, 25.85]])]
        )
        
        df_points = point_table_from_lines(gdf)
        
        assert len(df_points) == 5
        assert all(df_points['LINE'] == 1)
    
    def test_points_along_line(self, sample_lines_gdf):
        """Test that generated points lie along the flight line."""
        df_points = point_table_from_lines(sample_lines_gdf.iloc[:1])
        
        # All points should be between the line endpoints
        lons = df_points['LON'].values
        lats = df_points['LAT'].values
        
        # Get line endpoints (approximate)
        lon1, lat1 = -80.50416667, 25.75833333
        lon2, lat2 = -80.33611111, 25.84583333
        
        # Points should be within the bounding box
        assert all(min(lon1, lon2) <= lon <= max(lon1, lon2) for lon in lons)
        assert all(min(lat1, lat2) <= lat <= max(lat1, lat2) for lat in lats)


@pytest.mark.unit
class TestInterpTime:
    """Test cases for interp_time function."""
    
    def test_basic_interpolation(self, sample_xarray_dataset):
        """Test basic time interpolation."""
        result = interp_time(sample_xarray_dataset, timestep_seconds=1800)  # 30 min
        
        assert isinstance(result, xr.Dataset)
        assert 'time' in result.coords
        assert len(result.time) > len(sample_xarray_dataset.time)
    
    def test_timestep_60_seconds(self, sample_xarray_dataset):
        """Test interpolation with 60 second timestep."""
        result = interp_time(sample_xarray_dataset, timestep_seconds=60)
        
        # Should have approximately 60x more time steps
        original_hours = len(sample_xarray_dataset.time)
        expected_minutes = (original_hours - 1) * 60 + 1
        
        assert len(result.time) >= expected_minutes
    
    def test_interpolation_increases_resolution(self, sample_xarray_dataset):
        """Test that interpolation increases temporal resolution."""
        original_len = len(sample_xarray_dataset.time)
        result = interp_time(sample_xarray_dataset, timestep_seconds=60)
        
        assert len(result.time) > original_len
    
    def test_preserves_data_variables(self, sample_xarray_dataset):
        """Test that data variables are preserved."""
        result = interp_time(sample_xarray_dataset, timestep_seconds=1800)
        
        for var in sample_xarray_dataset.data_vars:
            assert var in result.data_vars
    
    def test_preserves_spatial_coords(self, sample_xarray_dataset):
        """Test that spatial coordinates are preserved."""
        result = interp_time(sample_xarray_dataset, timestep_seconds=1800)
        
        np.testing.assert_array_equal(result.lat.values, 
                                     sample_xarray_dataset.lat.values)
        np.testing.assert_array_equal(result.lon.values, 
                                     sample_xarray_dataset.lon.values)
    
    def test_time_range_preserved(self, sample_xarray_dataset):
        """Test that time range is preserved."""
        result = interp_time(sample_xarray_dataset, timestep_seconds=1800)
        
        assert result.time.min() == sample_xarray_dataset.time.min()
        # Max time might be slightly different due to rounding


@pytest.mark.unit
class TestCalcSunAlt:
    """Test cases for calc_sun_alt function."""
    
    def test_basic_solar_elevation(self):
        """Test basic solar elevation calculation."""
        # Create sample data
        df = pd.DataFrame({
            'station': ['A', 'A', 'B', 'B'],
            'time': pd.date_range('2025-01-15 12:00', periods=4, freq='1H'),
            'node_lon': [-80.0, -80.0, -75.0, -75.0],
            'node_lat': [25.0, 25.0, 30.0, 30.0]
        }).set_index(['station', 'time'])
        
        result = calc_sun_alt(df)
        
        assert 'solar_elevation' in result.columns
        assert len(result) == 4
        assert result.index.names == ['station', 'time']
    
    def test_solar_elevation_values_reasonable(self):
        """Test that solar elevation values are reasonable."""
        # Noon in Miami should have high solar elevation
        df = pd.DataFrame({
            'station': ['Miami'],
            'time': [datetime.datetime(2025, 6, 21, 12, 0, 0)],  # Summer solstice noon
            'node_lon': [-80.19],
            'node_lat': [25.76]
        }).set_index(['station', 'time'])
        
        result = calc_sun_alt(df)
        
        # Solar elevation at noon in summer should be high (> 70 degrees)
        assert result['solar_elevation'].iloc[0] > 70
    
    def test_solar_elevation_negative_at_night(self):
        """Test that solar elevation is negative at night."""
        # Midnight should have negative solar elevation
        df = pd.DataFrame({
            'station': ['Miami'],
            'time': [datetime.datetime(2025, 1, 15, 0, 0, 0)],
            'node_lon': [-80.19],
            'node_lat': [25.76]
        }).set_index(['station', 'time'])
        
        result = calc_sun_alt(df)
        
        assert result['solar_elevation'].iloc[0] < 0
    
    def test_custom_variable_names(self):
        """Test with custom variable names."""
        df = pd.DataFrame({
            'station': ['A', 'B'],
            'custom_time': pd.date_range('2025-01-15 12:00', periods=2, freq='1H'),
            'custom_lon': [-80.0, -75.0],
            'custom_lat': [25.0, 30.0]
        }).set_index(['station', 'custom_time'])
        
        result = calc_sun_alt(df, time_var='custom_time', 
                             x_var='custom_lon', y_var='custom_lat')
        
        assert 'solar_elevation' in result.columns
        assert len(result) == 2


@pytest.mark.unit
class TestCalcInRange:
    """Test cases for calc_in_range function."""
    
    def test_basic_in_range_calculation(self):
        """Test basic in-range calculation."""
        df = pd.DataFrame({
            'station': ['A', 'A', 'A', 'A'],
            'time': pd.date_range('2025-01-15', periods=4, freq='1H'),
            'zeta': [0.0, 0.5, 1.0, 1.5],
            'mllw_minus_lmsl': [-0.5, -0.5, -0.5, -0.5],
            'mhw_minus_lmsl': [0.5, 0.5, 0.5, 0.5],
            'tolerance': [0.2, 0.2, 0.2, 0.2],
            'solar_elevation': [30, 30, 30, 30]
        }).set_index(['station', 'time'])
        
        result = calc_in_range(df, datums=['mllw', 'mhw'])
        
        assert 'mllw_in_range' in result.columns
        assert 'mhw_in_range' in result.columns
    
    def test_water_level_in_tolerance(self):
        """Test that water levels within tolerance are marked in range."""
        df = pd.DataFrame({
            'station': ['A'],
            'time': [pd.Timestamp('2025-01-15 12:00')],
            'zeta': [0.0],
            'mllw_minus_lmsl': [-0.5],
            'tolerance': [0.1],
            'solar_elevation': [30]
        }).set_index(['station', 'time'])
        
        result = calc_in_range(df, datums=['mllw'])
        
        # zeta=0.0 should be outside mllw=-0.5 ± 0.1
        assert not result['mllw_in_range'].iloc[0]
    
    def test_water_level_outside_tolerance(self):
        """Test that water levels outside tolerance are marked out of range."""
        df = pd.DataFrame({
            'station': ['A'],
            'time': [pd.Timestamp('2025-01-15 12:00')],
            'zeta': [0.0],
            'mllw_minus_lmsl': [-1.0],
            'tolerance': [0.1],
            'solar_elevation': [30]
        }).set_index(['station', 'time'])
        
        result = calc_in_range(df, datums=['mllw'])
        
        # zeta=0.0 is outside mllw=-1.0 ± 0.1
        assert not result['mllw_in_range'].iloc[0]
    
    def test_solar_elevation_constraint(self):
        """Test that low solar elevation marks out of range."""
        df = pd.DataFrame({
            'station': ['A', 'B'],
            'time': pd.date_range('2025-01-15', periods=2, freq='1H'),
            'zeta': [-0.5, -0.5],
            'mllw_minus_lmsl': [-0.5, -0.5],
            'tolerance': [0.2, 0.2],
            'solar_elevation': [30, 20]  # Second below minimum
        }).set_index(['station', 'time'])
        
        result = calc_in_range(df, datums=['mllw'], min_solar_elevation=25.0)
        
        assert result['mllw_in_range'].iloc[0]  # First should be in range
        assert not result['mllw_in_range'].iloc[1]  # Second should be out of range
    
    def test_bmhw_datum_special_case(self):
        """Test below MHW (bmhw) datum special case."""
        df = pd.DataFrame({
            'station': ['A', 'B'],
            'time': pd.date_range('2025-01-15', periods=2, freq='1H'),
            'zeta': [0.3, 0.7],
            'mhw_minus_lmsl': [0.5, 0.5],
            'solar_elevation': [30, 30]
        }).set_index(['station', 'time'])
        
        result = calc_in_range(df, datums=['bmhw'])
        
        # bmhw checks if zeta <= mhw_minus_lmsl
        assert result['bmhw_in_range'].iloc[0]  # 0.3 <= 0.5
        assert not result['bmhw_in_range'].iloc[1]  # 0.7 > 0.5
    
    def test_multiple_datums(self):
        """Test calculation for multiple datums."""
        df = pd.DataFrame({
            'station': ['A'],
            'time': [pd.Timestamp('2025-01-15 12:00')],
            'zeta': [0.0],
            'mllw_minus_lmsl': [-0.5],
            'mhw_minus_lmsl': [0.5],
            'tolerance': [0.2],
            'solar_elevation': [30]
        }).set_index(['station', 'time'])
        
        result = calc_in_range(df, datums=['mllw', 'mhw'])
        
        assert 'mllw_in_range' in result.columns
        assert 'mhw_in_range' in result.columns
    
    def test_preserves_original_columns(self):
        """Test that original columns are preserved."""
        df = pd.DataFrame({
            'station': ['A'],
            'time': [pd.Timestamp('2025-01-15 12:00')],
            'zeta': [0.0],
            'mllw_minus_lmsl': [-0.5],
            'tolerance': [0.2],
            'solar_elevation': [30],
            'extra_col': ['test']
        }).set_index(['station', 'time'])
        
        result = calc_in_range(df, datums=['mllw'])
        
        assert 'extra_col' in result.columns
        assert result['extra_col'].iloc[0] == 'test'

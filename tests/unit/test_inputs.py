"""Unit tests for inputs.py module."""

import pytest
import pandas as pd
import geopandas as gpd
import shapely
import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock
import logging

from inputs import (
    load_lines_gdf,
    load_images_field_gdf,
    load_images_final_gdf,
    get_forecast_init_time
)


@pytest.mark.unit
class TestLoadLinesGdf:
    """Test cases for load_lines_gdf function."""
    
    def test_load_valid_lines_file(self, sample_lines_csv):
        """Test loading a valid flight lines file."""
        gdf = load_lines_gdf(str(sample_lines_csv))
        
        assert isinstance(gdf, gpd.GeoDataFrame)
        assert len(gdf) == 2
        assert 'LINE' in gdf.columns
        assert 'geometry' in gdf.columns
        assert all(isinstance(geom, shapely.LineString) for geom in gdf.geometry)
    
    def test_geometry_coordinates(self, sample_lines_csv):
        """Test that geometries have correct coordinates."""
        gdf = load_lines_gdf(str(sample_lines_csv))
        
        # Check first line coordinates
        first_line = gdf.geometry.iloc[0]
        coords = list(first_line.coords)
        
        # First point should be approximately lon1, lat1
        assert abs(coords[0][0] - (-80.50416667)) < 1e-5
        assert abs(coords[0][1] - 25.75833333) < 1e-5
        
        # Second point should be approximately lon2, lat2
        assert abs(coords[1][0] - (-80.33611111)) < 1e-5
        assert abs(coords[1][1] - 25.84583333) < 1e-5
    
    def test_all_columns_preserved(self, sample_lines_csv):
        """Test that all input columns are preserved."""
        gdf = load_lines_gdf(str(sample_lines_csv))
        
        expected_cols = ['LINE', 'LON1', 'LAT1', 'LON2', 'LAT2', 
                        'PHOTOS', 'SCALE', 'EMULSION', 'GRND_EL', 'geometry']
        for col in expected_cols:
            assert col in gdf.columns
    
    def test_invalid_file_path(self):
        """Test that invalid file path raises error."""
        with pytest.raises(FileNotFoundError):
            load_lines_gdf('nonexistent_file.wpt')
    
    def test_data_types(self, sample_lines_csv):
        """Test that loaded data has correct types."""
        gdf = load_lines_gdf(str(sample_lines_csv))
        
        assert gdf['LINE'].dtype in [int, 'int64']
        assert gdf['PHOTOS'].dtype in [int, 'int64']
        assert gdf['SCALE'].dtype in [int, 'int64']
        assert isinstance(gdf['LON1'].iloc[0], str)
        assert isinstance(gdf['LAT1'].iloc[0], str)


@pytest.mark.unit
class TestLoadImagesFieldGdf:
    """Test cases for load_images_field_gdf function."""
    
    def test_load_valid_field_images(self, sample_images_field_csv):
        """Test loading a valid field images file."""
        gdf = load_images_field_gdf(str(sample_images_field_csv))
        
        assert isinstance(gdf, gpd.GeoDataFrame)
        assert len(gdf) == 3
        assert 'geometry' in gdf.columns
        assert 'datetime' in gdf.columns
    
    def test_geometry_points_created(self, sample_images_field_csv):
        """Test that point geometries are created correctly."""
        gdf = load_images_field_gdf(str(sample_images_field_csv))
        
        assert all(isinstance(geom, shapely.Point) for geom in gdf.geometry)
        
        # Check first point coordinates
        first_point = gdf.geometry.iloc[0]
        assert abs(first_point.x - (-80.50416667)) < 1e-5
        assert abs(first_point.y - 25.75833333) < 1e-5
    
    def test_datetime_conversion(self, sample_images_field_csv):
        """Test that GPS time is converted to datetime."""
        gdf = load_images_field_gdf(str(sample_images_field_csv))
        
        assert 'datetime' in gdf.columns
        assert pd.api.types.is_datetime64_any_dtype(gdf['datetime'])
    
    def test_column_renaming(self, sample_images_field_csv):
        """Test that Latitude/Longitude are renamed to lat/long."""
        gdf = load_images_field_gdf(str(sample_images_field_csv))
        
        assert 'lat' in gdf.columns
        assert 'long' in gdf.columns
        assert 'Latitude' not in gdf.columns
        assert 'Longitude' not in gdf.columns
    
    def test_missing_lat_lon_columns(self, tmp_path, caplog):
        """Test handling of missing lat/lon columns."""
        csv_content = """Time,Roll,Pitch,Heading
501234.5,0.5,1.2,45.3
"""
        csv_file = tmp_path / "ImageEvents_C147643_011525559565_003_RGB1.csv"
        csv_file.write_text(csv_content)
        
        with caplog.at_level(logging.WARNING):
            result = load_images_field_gdf(str(csv_file))
        
        # Should return DataFrame without geometry
        assert isinstance(result, pd.DataFrame)
        assert 'Unable to find latitude & longitude names' in caplog.text
    
    def test_gps_week_calculation(self, sample_images_field_csv):
        """Test GPS week origin calculation from filename."""
        gdf = load_images_field_gdf(str(sample_images_field_csv))
        
        # File is dated 011525 (Jan 15, 2025)
        # Check that datetime conversion produced reasonable dates
        assert all(gdf['datetime'].dt.year == 2025)
        assert all(gdf['datetime'].dt.month == 1)


@pytest.mark.unit
class TestLoadImagesFinalGdf:
    """Test cases for load_images_final_gdf function."""
    
    def test_load_valid_final_images(self, sample_images_final_csv):
        """Test loading a valid final images file."""
        gdf = load_images_final_gdf(str(sample_images_final_csv))
        
        assert isinstance(gdf, gpd.GeoDataFrame)
        assert len(gdf) == 3
        assert 'geometry' in gdf.columns
        assert 'datetime' in gdf.columns
    
    def test_geometry_points_created(self, sample_images_final_csv):
        """Test that point geometries are created correctly."""
        gdf = load_images_final_gdf(str(sample_images_final_csv))
        
        assert all(isinstance(geom, shapely.Point) for geom in gdf.geometry)
        
        # Check first point coordinates
        first_point = gdf.geometry.iloc[0]
        assert abs(first_point.x - (-80.50416667)) < 1e-5
        assert abs(first_point.y - 25.75833333) < 1e-5
    
    def test_datetime_conversion(self, sample_images_final_csv):
        """Test that Date and Time columns are converted to datetime."""
        gdf = load_images_final_gdf(str(sample_images_final_csv))
        
        assert 'datetime' in gdf.columns
        assert pd.api.types.is_datetime64_any_dtype(gdf['datetime'])
        
        # Check first datetime
        first_dt = gdf['datetime'].iloc[0]
        assert first_dt.year == 2025
        assert first_dt.month == 1
        assert first_dt.day == 15
        assert first_dt.hour == 12
        assert first_dt.minute == 0
    
    def test_column_renaming(self, sample_images_final_csv):
        """Test that Lat/Long are renamed to lat/long."""
        gdf = load_images_final_gdf(str(sample_images_final_csv))
        
        assert 'lat' in gdf.columns
        assert 'long' in gdf.columns
        assert 'Lat' not in gdf.columns
        assert 'Long' not in gdf.columns
    
    def test_missing_lat_lon_columns(self, tmp_path, caplog):
        """Test handling of missing lat/lon columns."""
        csv_content = """Date,Time,Roll,Pitch,Heading
15-Jan-2025,12:00:00,0.5,1.2,45.3
"""
        csv_file = tmp_path / "final_images.csv"
        csv_file.write_text(csv_content)
        
        with caplog.at_level(logging.WARNING):
            result = load_images_final_gdf(str(csv_file))
        
        # Should return DataFrame without geometry
        assert isinstance(result, pd.DataFrame)
        assert 'Unable to find latitude & longitude names' in caplog.text
    
    def test_invalid_datetime_format(self, tmp_path, caplog):
        """Test handling of invalid datetime format."""
        csv_content = """Date,Time,Lat,Long
invalid-date,invalid-time,25.75833333,-80.50416667
"""
        csv_file = tmp_path / "final_images.csv"
        csv_file.write_text(csv_content)
        
        with caplog.at_level(logging.WARNING):
            result = load_images_final_gdf(str(csv_file))
        
        assert 'Unable to convert Date and Time columns' in caplog.text


@pytest.mark.unit
class TestGetForecastInitTime:
    """Test cases for get_forecast_init_time function."""
    
    def test_basic_forecast_init_calculation(self, sample_image_times):
        """Test basic forecast initialization time calculation."""
        init_time = get_forecast_init_time(sample_image_times)
        
        assert isinstance(init_time, datetime.datetime)
        assert init_time.year == 2025
        assert init_time.month == 1
        assert init_time.day == 15
        assert init_time.hour == 12
    
    def test_init_hour_selection(self):
        """Test that correct initialization hour is selected."""
        # Test different start times
        test_cases = [
            (datetime.datetime(2025, 1, 15, 0, 30), 0),
            (datetime.datetime(2025, 1, 15, 5, 30), 0),
            (datetime.datetime(2025, 1, 15, 6, 30), 6),
            (datetime.datetime(2025, 1, 15, 11, 30), 6),
            (datetime.datetime(2025, 1, 15, 12, 30), 12),
            (datetime.datetime(2025, 1, 15, 17, 30), 12),
            (datetime.datetime(2025, 1, 15, 18, 30), 18),
            (datetime.datetime(2025, 1, 15, 23, 30), 18),
        ]
        
        for image_time, expected_hour in test_cases:
            image_times = pd.Series([image_time])
            init_time = get_forecast_init_time(image_times)
            assert init_time.hour == expected_hour
    
    def test_warning_for_next_cycle(self, caplog):
        """Test warning when last image is in next forecast cycle."""
        base_time = datetime.datetime(2025, 1, 15, 12, 0, 0)
        image_times = pd.Series([
            base_time,
            base_time + datetime.timedelta(hours=7)  # More than 6 hours later
        ])
        
        with caplog.at_level(logging.WARNING):
            init_time = get_forecast_init_time(image_times)
        
        assert 'more than 6 hours' in caplog.text
        assert init_time.hour == 12
    
    def test_error_for_outside_forecast_period(self, caplog):
        """Test error when images are outside forecast period."""
        base_time = datetime.datetime(2025, 1, 15, 12, 0, 0)
        image_times = pd.Series([
            base_time,
            base_time + datetime.timedelta(days=8)  # More than 7.5 days later
        ])
        
        with caplog.at_level(logging.ERROR):
            init_time = get_forecast_init_time(image_times)
        
        assert 'more than 7.5 days' in caplog.text
    
    def test_single_image_time(self):
        """Test with a single image time."""
        image_time = datetime.datetime(2025, 1, 15, 14, 30, 0)
        image_times = pd.Series([image_time])
        
        init_time = get_forecast_init_time(image_times)
        
        assert init_time.hour == 12
        assert init_time.date() == image_time.date()
    
    def test_midnight_edge_case(self):
        """Test edge case at midnight."""
        image_time = datetime.datetime(2025, 1, 15, 0, 0, 0)
        image_times = pd.Series([image_time])
        
        init_time = get_forecast_init_time(image_times)
        
        assert init_time.hour == 0
        assert init_time == image_time
    
    def test_multiple_images_spanning_hours(self):
        """Test with multiple images spanning several hours."""
        base_time = datetime.datetime(2025, 1, 15, 8, 0, 0)
        image_times = pd.Series([
            base_time,
            base_time + datetime.timedelta(hours=1),
            base_time + datetime.timedelta(hours=2),
            base_time + datetime.timedelta(hours=3)
        ])
        
        init_time = get_forecast_init_time(image_times)
        
        # Should use 6:00 as init time
        assert init_time.hour == 6
        assert init_time.date() == base_time.date()

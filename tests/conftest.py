"""Pytest configuration and shared fixtures for NGS Flight Planning tests."""

import pytest
import pandas as pd
import geopandas as gpd
import shapely
import numpy as np
import datetime
from pathlib import Path
import tempfile


# Sample data fixtures
@pytest.fixture
def sample_hdms_coords():
    """Sample HDMS coordinate strings for testing."""
    return {
        'lon1': 'W80 30 15',
        'lat1': 'N25 45 30',
        'lon2': 'W80 20 10',
        'lat2': 'N25 50 45'
    }


@pytest.fixture
def sample_decimal_coords():
    """Sample decimal degree coordinates."""
    return {
        'lon1': -80.50416667,
        'lat1': 25.75833333,
        'lon2': -80.33611111,
        'lat2': 25.84583333
    }


@pytest.fixture
def sample_lines_csv(tmp_path):
    """Create a sample flight lines CSV file."""
    csv_content = """LINE,LON1,LAT1,LON2,LAT2,PHOTOS,SCALE,EMULSION,GRND_EL
1,W80 30 15,N25 45 30,W80 20 10,N25 50 45,10,10000,RGB,50
2,W80 25 20,N25 40 15,W80 15 30,N25 55 20,8,10000,RGB,45
"""
    csv_file = tmp_path / "test_lines.wpt"
    csv_file.write_text(csv_content)
    return csv_file


@pytest.fixture
def sample_lines_gdf():
    """Create a sample GeoDataFrame with flight lines."""
    data = {
        'LINE': [1, 2],
        'LON1': ['W80 30 15', 'W80 25 20'],
        'LAT1': ['N25 45 30', 'N25 40 15'],
        'LON2': ['W80 20 10', 'W80 15 30'],
        'LAT2': ['N25 50 45', 'N25 55 20'],
        'PHOTOS': [10, 8],
        'SCALE': [10000, 10000],
        'EMULSION': ['RGB', 'RGB'],
        'GRND_EL': [50, 45]
    }
    gdf = gpd.GeoDataFrame(
        data,
        geometry=[
            shapely.LineString([[-80.50416667, 25.75833333], [-80.33611111, 25.84583333]]),
            shapely.LineString([[-80.42222222, 25.67083333], [-80.25833333, 25.92222222]])
        ]
    )
    return gdf


@pytest.fixture
def sample_images_field_csv(tmp_path):
    """Create a sample field images CSV file."""
    # Create a filename with embedded date (format: MMDDYY)
    csv_content = """Time,Latitude,Longitude,Roll,Pitch,Heading
501234.5,25.75833333,-80.50416667,0.5,1.2,45.3
501294.5,25.76833333,-80.49416667,0.6,1.1,45.5
501354.5,25.77833333,-80.48416667,0.4,1.3,45.7
"""
    # Create filename with date pattern (Jan 15, 2025 -> 011525)
    csv_file = tmp_path / "ImageEvents_C147643_011525559565_003_RGB1.csv"
    csv_file.write_text(csv_content)
    return csv_file


@pytest.fixture
def sample_images_final_csv(tmp_path):
    """Create a sample final images CSV file."""
    csv_content = """Date,Time,Lat,Long,Roll,Pitch,Heading,Image
15-Jan-2025,12:00:00,25.75833333,-80.50416667,0.5,1.2,45.3,IMG001.jpg
15-Jan-2025,12:01:00,25.76833333,-80.49416667,0.6,1.1,45.5,IMG002.jpg
15-Jan-2025,12:02:00,25.77833333,-80.48416667,0.4,1.3,45.7,IMG003.jpg
"""
    csv_file = tmp_path / "final_images.csv"
    csv_file.write_text(csv_content)
    return csv_file


@pytest.fixture
def sample_image_times():
    """Create sample image timestamps."""
    base_time = datetime.datetime(2025, 1, 15, 12, 0, 0)
    return pd.Series([
        base_time,
        base_time + datetime.timedelta(hours=1),
        base_time + datetime.timedelta(hours=2),
        base_time + datetime.timedelta(hours=3)
    ])


@pytest.fixture
def sample_xarray_dataset():
    """Create a sample xarray Dataset for testing."""
    import xarray as xr
    
    times = pd.date_range('2025-01-15', periods=10, freq='1H')
    lats = np.linspace(25.0, 26.0, 5)
    lons = np.linspace(-81.0, -80.0, 5)
    
    data = np.random.rand(10, 5, 5)
    
    ds = xr.Dataset(
        {
            'water_level': (['time', 'lat', 'lon'], data)
        },
        coords={
            'time': times,
            'lat': lats,
            'lon': lons
        }
    )
    return ds


@pytest.fixture
def temp_output_dir(tmp_path):
    """Create a temporary output directory for test files."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return output_dir


# Mock fixtures for external dependencies
@pytest.fixture
def mock_stofs_data():
    """Mock STOFS forecast data."""
    import xarray as xr
    
    times = pd.date_range('2025-01-15', periods=24, freq='1H')
    lats = np.linspace(24.0, 27.0, 10)
    lons = np.linspace(-82.0, -79.0, 10)
    
    # Create realistic water level data (in meters)
    water_level = np.random.uniform(-0.5, 0.5, (24, 10, 10))
    
    ds = xr.Dataset(
        {
            'zeta': (['time', 'lat', 'lon'], water_level)
        },
        coords={
            'time': times,
            'lat': lats,
            'lon': lons
        }
    )
    return ds


@pytest.fixture
def mock_vdatum_data():
    """Mock VDatum transformation data."""
    lats = np.linspace(24.0, 27.0, 10)
    lons = np.linspace(-82.0, -79.0, 10)
    
    # Mock datum offsets (meters)
    mllw_offset = np.random.uniform(-1.0, -0.5, (10, 10))
    mhw_offset = np.random.uniform(0.5, 1.0, (10, 10))
    
    return {
        'mllw': mllw_offset,
        'mhw': mhw_offset,
        'lats': lats,
        'lons': lons
    }


# Marker helpers
def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as a performance benchmark"
    )

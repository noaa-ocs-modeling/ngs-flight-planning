"""Performance benchmarks for NGS Flight Planning."""

import pytest
import numpy as np
import pandas as pd
import geopandas as gpd
import shapely
import datetime


@pytest.mark.performance
class TestUtilsPerformance:
    """Performance benchmarks for utils module."""
    
    def test_hdms_to_dd_performance(self, benchmark):
        """Benchmark hdms_to_dd conversion."""
        from utils import hdms_to_dd
        
        result = benchmark(hdms_to_dd, 'W80 30 15')
        assert isinstance(result, float)
    
    def test_hdms_to_dd_batch_performance(self, benchmark):
        """Benchmark batch HDMS conversions."""
        from utils import hdms_to_dd
        
        hdms_coords = [
            'W80 30 15', 'W80 20 10', 'N25 45 30', 'N25 50 45'
        ] * 100  # 400 conversions
        
        def batch_convert():
            return [hdms_to_dd(coord) for coord in hdms_coords]
        
        result = benchmark(batch_convert)
        assert len(result) == 400
    
    def test_switch_lon_lims_performance(self, benchmark):
        """Benchmark longitude conversion."""
        from utils import switch_lon_lims
        
        lon_array = np.linspace(-180, 180, 1000)
        result = benchmark(switch_lon_lims, lon_array, min_lon=0.0)
        assert len(result) == 1000


@pytest.mark.performance
class TestInputsPerformance:
    """Performance benchmarks for inputs module."""
    
    def test_load_lines_gdf_performance(self, benchmark, sample_lines_csv):
        """Benchmark flight lines loading."""
        from inputs import load_lines_gdf
        
        result = benchmark(load_lines_gdf, str(sample_lines_csv))
        assert isinstance(result, gpd.GeoDataFrame)
    
    def test_load_images_field_performance(self, benchmark, sample_images_field_csv):
        """Benchmark field images loading."""
        from inputs import load_images_field_gdf
        
        result = benchmark(load_images_field_gdf, str(sample_images_field_csv))
        assert isinstance(result, gpd.GeoDataFrame)


@pytest.mark.performance
class TestProcessingPerformance:
    """Performance benchmarks for processing module."""
    
    def test_point_table_from_lines_performance(self, benchmark, sample_lines_gdf):
        """Benchmark point generation from flight lines."""
        from processing import point_table_from_lines
        
        result = benchmark(point_table_from_lines, sample_lines_gdf)
        assert isinstance(result, gpd.GeoDataFrame)
    
    def test_calc_sun_alt_performance(self, benchmark):
        """Benchmark solar elevation calculation."""
        from processing import calc_sun_alt
        
        # Create larger dataset for meaningful benchmark
        df = pd.DataFrame({
            'station': ['A'] * 100 + ['B'] * 100,
            'time': pd.date_range('2025-01-15', periods=200, freq='1H'),
            'node_lon': [-80.0] * 200,
            'node_lat': [25.0] * 200
        }).set_index(['station', 'time'])
        
        result = benchmark(calc_sun_alt, df)
        assert 'solar_elevation' in result.columns
    
    def test_calc_in_range_performance(self, benchmark):
        """Benchmark in-range calculation."""
        from processing import calc_in_range
        
        # Create dataset
        df = pd.DataFrame({
            'station': ['A'] * 100,
            'time': pd.date_range('2025-01-15', periods=100, freq='1H'),
            'zeta': np.random.uniform(-0.5, 0.5, 100),
            'mllw_minus_lmsl': [-0.5] * 100,
            'mhw_minus_lmsl': [0.5] * 100,
            'tolerance': [0.2] * 100,
            'solar_elevation': [30] * 100
        }).set_index(['station', 'time'])
        
        result = benchmark(calc_in_range, df, datums=['mllw', 'mhw'])
        assert 'mllw_in_range' in result.columns


@pytest.mark.performance
class TestMeshHandlingPerformance:
    """Performance benchmarks for mesh_handling module."""
    
    def test_get_box_performance(self, benchmark, sample_lines_gdf):
        """Benchmark bounding box creation."""
        from mesh_handling import get_box
        
        result = benchmark(get_box, sample_lines_gdf, buffer=0.5)
        assert isinstance(result, shapely.Polygon)
    
    def test_get_box_large_dataset_performance(self, benchmark):
        """Benchmark bounding box with large dataset."""
        from mesh_handling import get_box
        
        # Create large GeoDataFrame
        points = [shapely.Point(lon, lat) 
                 for lon in np.linspace(-81, -79, 100)
                 for lat in np.linspace(24, 26, 100)]
        gdf = gpd.GeoDataFrame(geometry=points)
        
        result = benchmark(get_box, gdf, buffer=0.5)
        assert isinstance(result, shapely.Polygon)


# Performance summary markers
@pytest.mark.performance
def test_performance_summary_marker():
    """Marker test for performance summary."""
    # This is a placeholder to ensure performance suite runs
    pass

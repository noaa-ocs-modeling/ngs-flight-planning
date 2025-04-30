"""
"""


import geopandas as gpd
import pandas as pd
import shapely
import datetime
from typing import List
import sys


def geopackage_prediction(
    df_lines: gpd.GeoDataFrame,
    df_line_windows: pd.DataFrame,
    df_points: gpd.GeoDataFrame,
    df_point_windows: pd.DataFrame,
    project_name: str,
    datum_list: List[str],
    init_datetime: datetime.datetime
) -> None:
    """Write geopackage with time window predictions.

    Creates a two layer geopackage file with layers:
    1. flightlines
        Contains columns: 
            project (arg)
            line_name (from df_line_windows)
            datum (from df_line_windows)
            start (from df_line_windows)
            end (from df_line_windows)
            duration (calculate)
            lat1 (df_lines)
            long1 (df_lines)
            lat2 (df_lines)
            long2 (df_lines)
            geometry (df_lines)
    2. flightpoints
        Contains columns:
            project (arg)
            line_name (df_points)
            point_num (df_points)
            lat (df_points)
            long (df_points)
            datum (df_point_windows)
            start (df_point_windows)
            end (df_point_windows)
            duration (calculate)
            geometry (df_points)
    """
    # Construct lines layer data frame.
    result_l = df_line_windows.join(df_lines.set_index('LINE'), 
                                    on='line', how='left', lsuffix='_window')
    result_l['project'] = project_name
    result_l['duration'] = (result_l['end_time'] - 
                            result_l['start_time'])\
                           /datetime.timedelta(minutes=1)
    line_cols = {
        'project':'project',
        'line':'line_name',
        'datum':'datum',
        'start_time':'start',
        'end_time':'end',
        'duration':'duration',
        'LAT1':'lat1',
        'LON1':'long1',
        'LAT2':'lat2',
        'LON2':'long2',
        'geometry':'geometry'
    }
    result_l = result_l[list(line_cols.keys())].rename(columns=line_cols)
    # Construct points layer data frame.
    result_p = df_point_windows.join(df_points, on='station', 
                                     how='left', lsuffix='_window')
    result_p['project'] = project_name
    result_p['duration'] = (result_p['end_time'] - 
                            result_p['start_time'])\
                           /datetime.timedelta(minutes=1)
    point_cols = {
        'project':'project', 
        'line':'line_name',
        'POINT_NUM':'point_num',
        'LAT':'lat',
        'LON':'long', 
        'datum':'datum',
        'start_time':'start',
        'end_time':'end',
        'duration':'duration',
        'geometry':'geometry'
    }
    result_p = result_p[list(point_cols.keys())].rename(columns=point_cols)
    # Write file.
    datestr = init_datetime.strftime('%Y%m%dT%H')
    outdir = 'data/output/'
    fileext = '.gpkg'
    filename = '_'.join([project_name, '_'.join(datum_list), datestr])
    gpd.GeoDataFrame(result_l).to_file(outdir + filename + fileext, 
                                       layer='flightlines', 
                                       driver='GPKG')
    gpd.GeoDataFrame(result_p).to_file(outdir + filename + fileext, 
                                       layer='flightpoints', 
                                       driver='GPKG')
    return None



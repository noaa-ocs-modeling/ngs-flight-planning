"""Functions for writing NGS flight planning output files.

Functions
---------
output_all_prediction
geopackage_prediction
lines_shapefile_prediction
lines_geojson_prediction
points_shapefile_prediction
points_geojson_prediction
line_text_prediction
date_text_prediction

"""


import geopandas as gpd
import pandas as pd
import numpy as np
import shapely
import datetime
import pathlib
from typing import List
import sys
import logging


logger = logging.getLogger(__name__)


def output_all_prediction(
    df_lines: gpd.GeoDataFrame,
    df_line_windows: pd.DataFrame,
    df_points: gpd.GeoDataFrame,
    df_point_windows: pd.DataFrame,
    project_name: str,
    datum_list: List[str],
    init_datetime: datetime.datetime,
    outdir: str | pathlib.Path
) -> None:
    """Write all outputs for time window predictions.
    
    Parameters
    ----------
    df_lines
        Contains data about the flight lines.
    df_line_windows
        Contains data about the calculated time windows for
        each flight line.
    df_points
       Contains data about the imaging points along the flight lines.
    df_point_windows
        Contains data about the calculated time windows for
        each imaging point along the flight lines.
    project_name
        The name of the project, used to specify filenames.
    datum_list
        The list of datums to include in the output files (and
        also used in the output filenames).
    init_datetime
        The forecast initialization time, used in the output filenames.
    outdir
        The directory in which to save output files.

    Returns
    -------
    None
    
    """
    geopackage_prediction(df_lines, df_line_windows, df_points, df_point_windows, project_name, datum_list, init_datetime,outdir)
    lines_shapefile_prediction(df_lines, df_line_windows, project_name, datum_list, init_datetime, outdir)
    lines_geojson_prediction(df_lines, df_line_windows, project_name, datum_list, init_datetime, outdir)
    points_shapefile_prediction(df_points, df_point_windows, project_name, datum_list, init_datetime, outdir)
    points_geojson_prediction(df_points, df_point_windows, project_name, datum_list, init_datetime, outdir)
    line_text_prediction(df_lines, df_line_windows, project_name, datum_list, init_datetime, outdir)
    date_text_prediction(df_lines, df_line_windows, project_name, datum_list, init_datetime, outdir)
    return None

def geopackage_prediction(
    df_lines: gpd.GeoDataFrame,
    df_line_windows: pd.DataFrame,
    df_points: gpd.GeoDataFrame,
    df_point_windows: pd.DataFrame,
    project_name: str,
    datum_list: List[str],
    init_datetime: datetime.datetime,
    outdir: str | pathlib.Path
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
    fileext = '.gpkg'
    filename = '_'.join([project_name, '_'.join(datum_list), datestr])
    gpd.GeoDataFrame(result_l).to_file(pathlib.Path(outdir) / 
                                       (filename + fileext), 
                                       layer='flightlines', 
                                       driver='GPKG')
    gpd.GeoDataFrame(result_p).to_file(pathlib.Path(outdir) / 
                                       (filename + fileext), 
                                       layer='flightpoints', 
                                       driver='GPKG')
    return None


def lines_shapefile_prediction(
    df_lines: gpd.GeoDataFrame,
    df_line_windows: pd.DataFrame,
    project_name: str,
    datum_list: List[str],
    init_datetime: datetime.datetime,
    outdir: str | pathlib.Path
) -> None:
    """Write shapefile with line-wise time window predictions.

    Contains columns: 
        project (arg)
        line_name (from df_line_windows)
        datum (from df_line_windows)
        start_date (from df_line_windows)
        start (from df_line_windows)
        end_date (from df_line_windows)
        end (from df_line_windows)
        duration (calculate)
        lat1 (df_lines)
        long1 (df_lines)
        lat2 (df_lines)
        long2 (df_lines)
        geometry (df_lines)
        timezone (df_line_windows)
    """
    # Construct lines layer data frame.
    result_l = df_line_windows.join(df_lines.set_index('LINE'), 
                                    on='line', how='left', lsuffix='_window')
    result_l['project'] = project_name
    result_l['duration'] = (result_l['end_time'] - 
                            result_l['start_time'])\
                           /datetime.timedelta(minutes=1)
    result_l['start_date'] = result_l['start_time'].dt.strftime('%Y-%m-%d')
    result_l['start_hms'] = result_l['start_time'].dt.strftime('%H:%M:%S')
    result_l['start_tz'] = result_l['start_time'].apply(lambda t: t.tzinfo)
    result_l['end_date'] = result_l['end_time'].dt.strftime('%Y-%m-%d')
    result_l['end_hms'] = result_l['end_time'].dt.strftime('%H:%M:%S')
    result_l['end_tz'] = result_l['end_time'].apply(lambda t: t.tzinfo)
    line_cols = {
        'project':'project',
        'line':'line_name',
        'datum':'datum',
        'start_date':'start_date',
        'start_hms':'start',
        'end_date':'end_date',
        'end_hms':'end',
        'duration':'duration',
        'LAT1':'lat1',
        'LON1':'long1',
        'LAT2':'lat2',
        'LON2':'long2',
        'geometry':'geometry'
    }
    if (result_l['start_tz'] == result_l['end_tz']).all():
        line_cols['start_tz'] = 'timezone'
    result_l = result_l[list(line_cols.keys())].rename(columns=line_cols)
    
    # Write file.
    datestr = init_datetime.strftime('%Y%m%dT%H')
    fileext = '.lines.shp'
    filename = '_'.join([project_name, '_'.join(datum_list), datestr])
    gpd.GeoDataFrame(result_l).to_file(pathlib.Path(outdir) / 
                                       (filename + fileext))
    return None


def lines_geojson_prediction(
    df_lines: gpd.GeoDataFrame,
    df_line_windows: pd.DataFrame,
    project_name: str,
    datum_list: List[str],
    init_datetime: datetime.datetime,
    outdir: str | pathlib.Path
) -> None:
    """Write geojson with line-wise time window predictions.

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
    
    # Write file.
    datestr = init_datetime.strftime('%Y%m%dT%H')
    fileext = '.lines.geojson'
    filename = '_'.join([project_name, '_'.join(datum_list), datestr])
    gpd.GeoDataFrame(result_l).to_file(pathlib.Path(outdir) / 
                                       (filename + fileext), 
                                       driver='GeoJSON')
    return None


def points_shapefile_prediction(
    df_points: gpd.GeoDataFrame,
    df_point_windows: pd.DataFrame,
    project_name: str,
    datum_list: List[str],
    init_datetime: datetime.datetime,
    outdir: str | pathlib.Path
) -> None:
    """Write shapefile with point-wise time window predictions.

    Contains columns:
        project (arg)
        line_name (df_points)
        point_num (df_points)
        lat (df_points)
        long (df_points)
        datum (df_point_windows)
        start_date (df_point_windows)
        start (df_point_windows)
        end_date (df_point_windows)
        end (df_point_windows)
        duration (calculate)
        geometry (df_points)
        timezone (df_point_windows)
    """
    # Construct points layer data frame.
    result_p = df_point_windows.join(df_points, on='station', 
                                     how='left', lsuffix='_window')
    result_p['project'] = project_name
    result_p['duration'] = (result_p['end_time'] - 
                            result_p['start_time'])\
                           /datetime.timedelta(minutes=1)
    result_p['start_date'] = result_p['start_time'].dt.strftime('%Y-%m-%d')
    result_p['start_hms'] = result_p['start_time'].dt.strftime('%H:%M:%S')
    result_p['start_tz'] = result_p['start_time'].apply(lambda t: t.tzinfo)
    result_p['end_date'] = result_p['end_time'].dt.strftime('%Y-%m-%d')
    result_p['end_hms'] = result_p['end_time'].dt.strftime('%H:%M:%S')
    result_p['end_tz'] = result_p['end_time'].apply(lambda t: t.tzinfo)
    point_cols = {
        'project':'project', 
        'line':'line_name',
        'POINT_NUM':'point_num',
        'LAT':'lat',
        'LON':'long', 
        'datum':'datum',
        'start_date':'start_date',
        'start_hms':'start',
        'end_date':'end_date',
        'end_hms':'end',
        'duration':'duration',
        'geometry':'geometry'
    }
    if (result_p['start_tz'] == result_p['end_tz']).all():
        point_cols['start_tz'] = 'timezone'
    result_p = result_p[list(point_cols.keys())].rename(columns=point_cols)
    
    # Write file.
    datestr = init_datetime.strftime('%Y%m%dT%H')
    fileext = '.pts.shp'
    filename = '_'.join([project_name, '_'.join(datum_list), datestr])
    gpd.GeoDataFrame(result_p).to_file(pathlib.Path(outdir) / 
                                       (filename + fileext))
    return None


def points_geojson_prediction(
    df_points: gpd.GeoDataFrame,
    df_point_windows: pd.DataFrame,
    project_name: str,
    datum_list: List[str],
    init_datetime: datetime.datetime,
    outdir: str | pathlib.Path
) -> None:
    """Write geojson with point-wise time window predictions.

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
    fileext = '.pts.geojson'
    filename = '_'.join([project_name, '_'.join(datum_list), datestr])
    gpd.GeoDataFrame(result_p).to_file(pathlib.Path(outdir) / 
                                       (filename + fileext), 
                                       driver='GeoJSON')
    return None


def line_text_prediction(
    df_lines: gpd.GeoDataFrame,
    df_line_windows: pd.DataFrame,
    project_name: str,
    datum_list: List[str],
    init_datetime: datetime.datetime,
    outdir: str | pathlib.Path
) -> None:
    """Write a text file with time windows by line then date.

    Columns are [date, datum1, ... datumN].

    Rows are formatted/grouped as:
        Flightline header
        Column headers
        One row per date
            <Blank line>
        Flightline header
        ...
    
    """
    # Define filename.
    datestr = init_datetime.strftime('%Y%m%dT%H')
    fileext = '.lines.txt'
    filename = '_'.join([project_name, '_'.join(datum_list), datestr])
    outfile = open(pathlib.Path(outdir) / (filename + fileext), 'a')
    
    # Get time zone info.
    sttzi = df_line_windows.start_time.apply(lambda t: t.tzinfo)
    ettzi = df_line_windows.end_time.apply(lambda t: t.tzinfo)
    if (sttzi == sttzi[0]).all() & (ettzi == ettzi[0]).all() & (sttzi[0] == ettzi[0]):
        tz_str = f"All times {sttzi[0]} ({sttzi[0].__repr__()})"
        outfile.write(tz_str + '\n')
    else:
        logger.error('Multiple timezones found in df_line_windows.')
    
    # Format datetimes as needed.
    df = df_line_windows.copy()
    df['date'] = df['start_time'].dt.date
    #df['YMD'] = df['start_time'].dt.strftime('%Y-%m-%d')
    df['time_window'] = ["".join([s, '-', e]) for (s,e) in 
                         zip(df['start_time'].dt.strftime('%H:%M'), 
                             df['end_time'].dt.strftime('%H:%M'))]
    
    # Get dates to be included in output.
    # Format in same way as 'date' column added to df above.
    dates_out = pd.date_range(start=df['start_time'].dt.date.min(),
                              end=df['start_time'].dt.date.max(), 
                              freq='D').to_frame(name='date',index=False)['date'].dt.date

    # Calculate maximum number of time windows per (line, date, datum)
    # and character lengths for formatting output strings.
    max_windows = df.groupby(['line', 'date', 'datum']).count().start_time.max()
    window_width = 14 * max_windows
    date_width = 15

    # Brute force loop over lines and dates to get time windows for each.
    # There are fancier ways to do this in pandas but they're kind of 
    # annoying with all the data frame index stuff.
    #
    # Loop over all lines (includes those without any windows).
    for ln in df_lines['LINE']:
        # Write flight line header.
        outfile.write(f"Line #{ln} with {str(df_lines.loc[df_lines.LINE==ln, 'PHOTOS'].values[0])} positions" + 
                      '\n')
        # Write columns headers.
        outfile.write('Date'.ljust(date_width) + 
                      ''.join([f'**{datum.upper()}**'.ljust(window_width) 
                               for datum in datum_list]) + 
                      '\n')
        # Loop over dates.
        for dt in dates_out:
            dt_str = str(dt).ljust(date_width)
            # Loop over datums.
            for datum in datum_list:
                ldd_str = '  '.join(
                    df.loc[(df.line == ln) & 
                           (df.date == dt) & 
                           (df.datum == datum), 
                           'time_window'].values
                )
                dt_str = dt_str + ldd_str.ljust(window_width)
            outfile.write(dt_str + '\n')
        outfile.write('\n')
            
    outfile.close()    
    return None


def date_text_prediction(
    df_lines: gpd.GeoDataFrame,
    df_line_windows: pd.DataFrame,
    project_name: str,
    datum_list: List[str],
    init_datetime: datetime.datetime,
    outdir: str | pathlib.Path
) -> None:
    """Write a text file with time windows by date then line.

    Columns are [line, datum1, ... datumN].

    Rows are formatted/grouped as:
        Column headers
        One row per date
            <Blank line>
        Column headers
        ...
    
    """
    # Define filename.
    datestr = init_datetime.strftime('%Y%m%dT%H')
    fileext = '.dates.txt'
    filename = '_'.join([project_name, '_'.join(datum_list), datestr])
    outfile = open(pathlib.Path(outdir) / (filename + fileext), 'a')
    
    # Get time zone info.
    sttzi = df_line_windows.start_time.apply(lambda t: t.tzinfo)
    ettzi = df_line_windows.end_time.apply(lambda t: t.tzinfo)
    if (sttzi == sttzi[0]).all() & (ettzi == ettzi[0]).all() & (sttzi[0] == ettzi[0]):
        tz_str = f"All times {sttzi[0]} ({sttzi[0].__repr__()})"
        outfile.write(tz_str + '\n')
    else:
        logger.error('Multiple timezones found in df_line_windows.')
    
    # Format datetimes as needed.
    df = df_line_windows.copy()
    df['date'] = df['start_time'].dt.date
    #df['YMD'] = df['start_time'].dt.strftime('%Y-%m-%d')
    df['time_window'] = ["".join([s, '-', e]) for (s,e) in 
                         zip(df['start_time'].dt.strftime('%H:%M'), 
                             df['end_time'].dt.strftime('%H:%M'))]
    
    # Get dates to be included in output.
    # Format in same way as 'date' column added to df above.
    dates_out = pd.date_range(start=df['start_time'].dt.date.min(),
                              end=df['start_time'].dt.date.max(), 
                              freq='D').to_frame(name='date',index=False)['date'].dt.date

    # Calculate maximum number of time windows per (line, date, datum)
    # and character lengths for formatting output strings.
    max_windows = df.groupby(['line', 'date', 'datum']).count().start_time.max()
    window_width = 14 * max_windows
    date_width = 20

    # Brute force loop over lines and dates to get time windows for each.
    # There are fancier ways to do this in pandas but they're kind of 
    # annoying with all the data frame index stuff.
    #
    # Loop over dates.
    for dt in dates_out:
        # Write columns headers.
        outfile.write(str(dt).ljust(date_width) + 
                      ''.join([f'**{datum.upper()}**'.ljust(window_width) 
                               for datum in datum_list]) + 
                      '\n')
        # Loop over all lines (includes those without any windows).
        for ln in df_lines['LINE']:
            ln_str = ln.ljust(date_width)
            # Loop over datums.
            for datum in datum_list:
                # Get time windows, as series, then numpy array, 
                # then joined together with spacing.
                ldd_str = '  '.join(
                    df.loc[(df.line == ln) & 
                           (df.date == dt) & 
                           (df.datum == datum), 
                           'time_window'].values
                )
                ln_str = ln_str + ldd_str.ljust(window_width)
            outfile.write(ln_str + '\n')
        outfile.write('\n')
            
    outfile.close()    
    return None
    
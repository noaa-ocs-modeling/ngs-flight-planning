"""Functions for writing NGS flight planning output files.

Functions
---------
get_create_output_dir
output_all_prediction
geopackage_prediction
lines_shapefile_prediction
lines_geojson_prediction
points_shapefile_prediction
points_geojson_prediction
line_text_prediction
date_text_prediction
output_all_qc
csv_qc
html_qc
geopackage_qc
shapefile_qc
geojson_qc
convert_output_z_units
get_output_z_units

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


def get_create_output_dir(
    output_dir_base: pathlib.Path | str, 
    project_name: str
) -> pathlib.Path:
    """Get (create if needed) output directory.
     
    Uses base directory and project name.

    Parameters
    ----------
    output_dir_base
        Base directory for outputs.
    project_name
        Name of the project.

    Returns
    -------
    pathlib.Path
        The output directory path.
        If it doesn't already exist, it will be created.

    """
    default_save_dir = pathlib.Path(output_dir_base) / project_name
    # TODO: Perhaps we want to add the forecast initialization to the save directory:
    # default_save_dir = pathlib.Path(output_dir) / project_name / init_datetime.strftime('%Y%m%dT%H')
    if default_save_dir.is_dir():
        # It it does exist and isn't empty.
        if any(default_save_dir.iterdir()):
            logger.warning(
                f'Target output directory {str(default_save_dir)} already ' + 
                'exists and is non-empty. This could result in output files ' + 
                'being overwritten, depending on the datums and forecast ' + 
                'initialization times of existing outputs. Specify a different' + 
                ' output directory or project name, or move/delete existing ' + 
                'output files to avoid this warning.'
            )
            save_dir = default_save_dir
            # Could use this snippet below if we want a totally new directory for each data processing run.
            # Leaving here in case it's wanted later.
            # -----
            #logger.warning(f'Target output directory {str(default_save_dir)} already exists and is non-empty. Attempting to create a new output directory.')
            #save_dir = pathlib.Path(output_dir) / '_'.join(
            #    [project_name, datetime.datetime.now().strftime('%Y%m%dT%H%M%S')]
            #)
            #pathlib.Path(dir).mkdir(parents=True, exist_ok=False)
            # -----
        # If it does exist, if it's empty, use it.
        else:
            save_dir = default_save_dir 
    # If default doesn't exist, make it.
    else:
        save_dir = default_save_dir
        save_dir.mkdir(parents=True, exist_ok=False)
    return save_dir


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
    logger.info("Saving geopackage prediction output...")
    geopackage_prediction(df_lines, df_line_windows, df_points, df_point_windows, project_name, datum_list, init_datetime,outdir)
    logger.info("Saving line prediction shapefile...")
    lines_shapefile_prediction(df_lines, df_line_windows, project_name, datum_list, init_datetime, outdir)
    logger.info("Saving line prediction geojson...")
    lines_geojson_prediction(df_lines, df_line_windows, project_name, datum_list, init_datetime, outdir)
    logger.info("Saving point prediction shapefile...")
    points_shapefile_prediction(df_points, df_point_windows, project_name, datum_list, init_datetime, outdir)
    logger.info("Saving point prediction geojson...")
    points_geojson_prediction(df_points, df_point_windows, project_name, datum_list, init_datetime, outdir)
    logger.info("Saving line-wise prediction text file...")
    line_text_prediction(df_lines, df_line_windows, project_name, datum_list, init_datetime, outdir)
    logger.info("Saving date-wise prediction text file...")
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


def output_all_qc(
    df_images: gpd.GeoDataFrame | pd.DataFrame,
    project_name: str,
    datum_list: List[str],
    z_units: str,
    init_datetime: datetime.datetime,
    outdir: str | pathlib.Path
) -> None:
    """Run all QC output functions for image QC results.

    Calls:
        csv_qc
        html_qc
        geopackage_qc
        shapefile_qc
        geojson_qc
    """
    try:
        logger.info("Saving QC CSV output...")
        csv_qc(df_images, project_name, datum_list, z_units, init_datetime, outdir)
    except Exception as e:
        logger.error(f"csv_qc failed: {e}", exc_info=True)
    try:
        logger.info("Saving QC HTML output...")
        html_qc(df_images, project_name, datum_list, z_units, init_datetime, outdir)
    except Exception as e:
        logger.error(f"html_qc failed: {e}", exc_info=True)
    try:
        logger.info("Saving QC GeoPackage output...")
        geopackage_qc(df_images, project_name, datum_list, z_units, init_datetime, outdir)
    except Exception as e:
        logger.error(f"geopackage_qc failed: {e}", exc_info=True)
    try:
        logger.info("Saving QC Shapefile output...")
        shapefile_qc(df_images, project_name, datum_list, z_units, init_datetime, outdir)
    except Exception as e:
        logger.error(f"shapefile_qc failed: {e}", exc_info=True)
    try:
        logger.info("Saving QC GeoJSON output...")
        geojson_qc(df_images, project_name, datum_list, z_units, init_datetime, outdir)
    except Exception as e:
        logger.error(f"geojson_qc failed: {e}", exc_info=True)
    return None


def convert_output_z_units(
    df: gpd.GeoDataFrame | pd.DataFrame, 
    datum_list: List[str], 
    z_units: str
) -> gpd.GeoDataFrame | pd.DataFrame:
    """Convert water level-based columns to desired output units.

    In this function, the z_units value MUST be either 'ft' or 'm'.
    Logic elsewhere should ensure this before calling this function.

    Parameters
    ----------
    df : gpd.GeoDataFrame or pd.DataFrame
        Input DataFrame containing water level data.
    datum_list : list of str
        List of vertical datums to consider for conversion.
    z_units : str
        Desired vertical units for output ('ft' or 'm').

    Returns
    -------
    gpd.GeoDataFrame or pd.DataFrame
        DataFrame with converted water level columns.

    """
    # Define conversion factor and append string.
    if z_units == 'ft':
        conversion_factor = 3.28084
        append_str = ' (ft)'
    elif z_units == 'm':
        conversion_factor = 1.0
        append_str = ' (m)'
    else:
        logger.warning(f"Warning: Unrecognized water level units '{z_units}'. No conversion applied.")
        conversion_factor = 1.0
        append_str = ''

    # Work out which columns to convert.
    cols_to_convert = []
    if 'tolerance' in df.columns:
        cols_to_convert.append('tolerance')
    if 'Tolerance' in df.columns:
        cols_to_convert.append('Tolerance') 
    for datum in datum_list:
        if datum.lower() == 'bmhw':
            search_datum = 'mhw'
        else:
            search_datum = datum
        # Most of the QC outputs just use the datum name for the
        # water level relative to that datum.
        if search_datum.upper() in df.columns:
            cols_to_convert.append(search_datum.upper())
        # HTML QC uses 'Relative to <DATUM>' for the column name.
        if 'Relative to ' + search_datum.upper() in df.columns:
            cols_to_convert.append('Relative to ' + search_datum.upper())

    # Apply the conversions.
    df_converted = df.copy()
    for col in cols_to_convert:
        df_converted[col] = df_converted[col] * conversion_factor
        df_converted = df_converted.rename(columns={col: col + append_str})

    return df_converted


def get_output_z_units(
    z_units: str,
    default_z_units: str
) -> str:
    """Get output z units string based on input z_units parameter."""
    if z_units.lower() in ['feet', 'ft', 'foot', 'f']:
        output_z_units = 'ft'
    elif z_units.lower() in ['meters', 'meter', 'm', 'metres', 'metre']:
        output_z_units = 'm'
    elif z_units.lower() == 'file_format_default':
        output_z_units = default_z_units
    else:
        logger.warning(f"Warning: Unrecognized water level units '{z_units}'. Using default units '{default_z_units}'.")
        output_z_units = default_z_units
    return output_z_units


def csv_qc(
    df_images: gpd.GeoDataFrame | pd.DataFrame,
    project_name: str,
    datum_list: List[str],
    z_units: str,
    init_datetime: datetime.datetime,
    outdir: str | pathlib.Path
) -> None:
    """Write a CSV with QC results for each image.

    Contains columns:
        ImageId
        <datum>
        <datum>_pass
            for all <datum> in datum_list
        Tolerance
        Roll
        FlightId [blank]
        FrameId [unknown hard coded constant]
        TideStage [blank]
        date
        time
        lat
        long
        
    """
    # Define units to use.
    default_z_units = 'ft'
    output_z_units = get_output_z_units(z_units, default_z_units)

    # Create a new DataFrame to hold the transformed data
    output_df = pd.DataFrame()
    
    # Add existing data.
    # The dictionary maps new column names (key) to old column names (value)
    column_mapping = {
        'ImageId': 'ImageId',
        'Tolerance': 'tolerance',
        'Roll': 'Roll',
        'lat': 'lat',
        'long': 'long'
    }
    for datum in datum_list:
        # Add pass fail column for each datum.
        column_mapping[datum.upper() + '_pass'] = datum.lower() + '_in_range'
        # Add "relative to datum" column.
        try:
            if datum.lower() == 'bmhw':
                output_df['MHW'] = df_images['zeta'] - df_images['mhw_minus_lmsl']
            else:
                output_df[datum.upper()] = df_images['zeta'] - df_images[datum.lower() + '_minus_lmsl']
        except KeyError:
            logger.warning(f"Warning: Expecting columns 'zeta' and '{datum.lower() + '_minus_lmsl'}' in the input DataFrame.")
            logger.warning(f"Found columns: {df_images.columns.tolist()}")
    
    # Remap columns from df_images to output_df.
    for new_col, old_col in column_mapping.items():
        if old_col in df_images.columns:
            output_df[new_col] = df_images[old_col]
        else:
            logger.warning(f"Warning: Column '{old_col}' not found in the input DataFrame.")
            output_df[new_col] = None # Or some other default value
    
    # Some columns are empty/arbitrary in the case of field QC,
    # but present in the final QC so should be taken if available.
    # In case of field QC sample data,
    # FlightID and TideStage seem to be empty. 
    # FrameId appears to be a constant "MM010193".
    if 'FlightId' in df_images.columns:
        output_df['FlightId'] = df_images['FlightId']
    elif 'FlightLineId' in df_images.columns:
        output_df['FlightId'] = df_images['FlightLineId']
    else:
        output_df['FlightId'] = None
    if 'TideStage' in df_images.columns:
        output_df['TideStage'] = df_images['TideStage']
    else:
        output_df['TideStage'] = None
    if 'FrameId' in df_images.columns:
        output_df['FrameId'] = df_images['FrameId']
    elif 'SerialNumber' in df_images.columns:
        output_df['FrameId'] = df_images['SerialNumber']
    else:
        output_df['FrameId'] = None
    
    # Extract date and time from datetime index.
    output_df['date'] = df_images.reset_index()['datetime'].dt.strftime('%Y/%m/%d').values
    output_df['time'] = df_images.reset_index()['datetime'].dt.strftime('%H:%M:%S').values
    
    # Ensure columns are in the correct final order
    final_columns_order = ['ImageId']
    for datum in datum_list:
        if datum.lower() == 'bmhw':
            final_columns_order.append('MHW')
        else:
            final_columns_order.append(datum.upper())
        final_columns_order.append(datum.upper() + '_pass')
    final_columns_order = final_columns_order + \
    [
        'Tolerance', 'Roll', 'FlightId', 
        'FrameId', 'TideStage', 'date', 'time', 'lat', 'long'
    ]
    output_df = output_df[final_columns_order]

    # Convert z units as needed.
    output_df = convert_output_z_units(output_df, datum_list, output_z_units)
    
    # Save the final DataFrame to CSV
    # Define filename.
    datestr = init_datetime.strftime('%Y%m%dT%H')
    fileext = '.csv'
    filename = '_'.join([project_name, '_'.join(datum_list), datestr, 'qc'])
    outpath = pathlib.Path(outdir) / (filename + fileext)
    output_df.to_csv(outpath, index=False)
    
    return None


def html_qc(
    df_images: gpd.GeoDataFrame | pd.DataFrame,
    project_name: str,
    datum_list: List[str],
    z_units: str,
    init_datetime: datetime.datetime,
    outdir: str | pathlib.Path
) -> None:
    """Write an HTML file with QC results for each image.

    Contains columns:
        ImageId
        Relative to <datum> [color -> pass or fail]
        Tolerance
        Roll
        FlightLineId [blank]
        FrameId/SerialNumber [unknown hard coded constant]
        TideStage [blank]

    The output is a styled HTML table for easy field review.
    """
    # Define units to use.
    default_z_units = 'ft'
    output_z_units = get_output_z_units(z_units, default_z_units)

    # Create a new DataFrame to hold the transformed data
    output_df = pd.DataFrame()
    
    # Add existing data.
    column_mapping = {
        'ImageId': 'ImageId',
        'Tolerance': 'tolerance',
        'Roll': 'Roll'
    }
    for datum in datum_list:
        # Add pass fail column for each datum.
        column_mapping[datum.upper() + '_pass'] = datum.lower() + '_in_range'
        # Add "relative to datum" column.
        try:
            if datum.lower() == 'bmhw':
                output_df['Relative to MHW'] = df_images['zeta'] - df_images['mhw_minus_lmsl']
            else:
                output_df['Relative to ' + datum.upper()] = df_images['zeta'] - df_images[datum.lower() + '_minus_lmsl']
        except KeyError:
            logger.warning(f"Warning: Expecting columns 'zeta' and '{datum.lower() + '_minus_lmsl'}' in the input DataFrame.")
            logger.warning(f"Found columns: {df_images.columns.tolist()}")
        
    # Remap columns from df_images to output_df.
    for new_col, old_col in column_mapping.items():
        if old_col in df_images.columns:
            output_df[new_col] = df_images[old_col]
        else:
            logger.warning(f"Warning: Column '{old_col}' not found in the input DataFrame.")
            output_df[new_col] = None
    
    # Some columns are empty/arbitrary in the case of field QC,
    # but present in the final QC so should be taken if available.
    # In case of field QC sample data,
    # FlightID and TideStage seem to be empty. 
    # FrameId appears to be a constant "MM010193".
    # Note output names are slightly different in html output
    # compared to other outputs.
    if 'FlightId' in df_images.columns:
        output_df['FlightLineId'] = df_images['FlightId']
    elif 'FlightLineId' in df_images.columns:
        output_df['FlightLineId'] = df_images['FlightLineId']
    else:
        output_df['FlightLineId'] = None
    if 'TideStage' in df_images.columns:
        output_df['TideStage'] = df_images['TideStage']
    else:
        output_df['TideStage'] = None
    if 'FrameId' in df_images.columns:
        output_df['FrameId/SerialNumber'] = df_images['FrameId']
    elif 'SerialNumber' in df_images.columns:
        output_df['FrameId/SerialNumber'] = df_images['SerialNumber']
    else:
        output_df['FrameId/SerialNumber'] = None

    # Ensure columns are in the correct final order
    final_columns_order = ['ImageId']
    for datum in datum_list:
        if datum.lower() == 'bmhw':
            final_columns_order.append('Relative to MHW')
        else:
            final_columns_order.append('Relative to ' + datum.upper())
    final_columns_order = final_columns_order + [
        'Tolerance', 'Roll', 'FlightLineId', 
        'FrameId/SerialNumber', 'TideStage'
    ]
    output_df = output_df[final_columns_order]
    output_df = output_df.reset_index(drop=True)

    # Prepare pass/fail DataFrame for styling
    pass_cols = {}
    for datum in datum_list:
        if datum.lower() == 'bmhw':
            rel_col = 'Relative to MHW'
        else:
            rel_col = 'Relative to ' + datum.upper()
        pass_col = datum.lower() + '_in_range'
        if pass_col in df_images.columns:
            pass_cols[rel_col] = df_images[pass_col].values
        else:
            pass_cols[rel_col] = [None] * len(output_df)
    pass_df = pd.DataFrame(pass_cols, index=output_df.index)

    # Define the styling function
    def style_func(val, rel_col, idx):
        passed = pass_df.at[idx, rel_col]
        if passed:
            return 'background-color: #c6efce; color: #006100;'  # green
        else:
            return 'background-color: #ffc7ce; color: #9c0006;'  # red

    # Build a DataFrame of styles
    styles = pd.DataFrame('', index=output_df.index, columns=output_df.columns)
    for rel_col in pass_cols:
        for idx in output_df.index:
            styles.at[idx, rel_col] = style_func(output_df.at[idx, rel_col], rel_col, idx)

    # Convert z units as needed.
    old_col_names = output_df.columns.tolist()
    output_df = convert_output_z_units(output_df, datum_list, output_z_units)
    new_col_names = output_df.columns.tolist()
    # Update styles DataFrame column names accordingly (slightly hacky...).
    styles = styles.rename(columns=dict(zip(old_col_names, new_col_names)))

    # Use Styler to apply the styles
    styler = output_df.style
    styler = styler.apply(lambda _: styles, axis=None)
    styler = styler.set_table_styles([
        {'selector': 'th, td', 'props': [('border-style', 'solid'),
                                        ('border-width', '1px'),
                                        ('border-color', 'lightgrey')]}
    ])
    styler = styler.hide() # This hides the index (mysteriously...)

    # Save the styled DataFrame as HTML
    datestr = init_datetime.strftime('%Y%m%dT%H')
    fileext = '.html'
    filename = '_'.join([project_name, '_'.join(datum_list), datestr, 'qc'])
    outfile = pathlib.Path(outdir) / (filename + fileext)
    styler.to_html(outfile)
    #
    return None


def geopackage_qc(
    df_images: gpd.GeoDataFrame | pd.DataFrame,
    project_name: str,
    datum_list: List[str],
    z_units: str,
    init_datetime: datetime.datetime,
    outdir: str | pathlib.Path
) -> None:
    """Write a GeoPackage with QC results for each image.

    Contains columns:
        ImageId
        <datum> (for all in datum_list)
        <datum>_pass (for all in datum_list)
        Tolerance
        Roll
        FlightId [blank]
        FrameId [unknown hard coded constant]
        TideStage [blank]
        time
        lat
        long
        geometry
    """
    # Define units to use.
    default_z_units = 'ft'
    output_z_units = get_output_z_units(z_units, default_z_units)

    # Create a new DataFrame to hold the transformed data
    output_df = pd.DataFrame()
    output_type_dict = {}

    # Add existing data.
    column_mapping = {
        'ImageId': 'ImageId',
        'Tolerance': 'tolerance',
        'Roll': 'Roll',
        'lat': 'lat',
        'long': 'long',
        'geometry': 'geometry'
    }
    for datum in datum_list:
        # Add "relative to datum" column.
        try:
            if datum.lower() == 'bmhw':
                output_df['MHW'] = df_images['zeta'] - df_images['mhw_minus_lmsl']
            else:
                output_df[datum.upper()] = df_images['zeta'] - df_images[datum.lower() + '_minus_lmsl']
        except KeyError:
            logger.warning(f"Warning: Expecting columns 'zeta' and '{datum.lower() + '_minus_lmsl'}' in the input DataFrame.")
            logger.warning(f"Found columns: {df_images.columns.tolist()}")
        # Add pass fail column for each datum.
        column_mapping[datum.upper() + '_pass'] = datum.lower() + '_in_range'
        output_type_dict[datum.upper() + '_pass'] = 'str'
    
    # Remap columns from df_images to output_df.
    for new_col, old_col in column_mapping.items():
        if old_col in df_images.columns:
            output_df[new_col] = df_images[old_col]
        else:
            logger.warning(f"Warning: Column '{old_col}' not found in the input DataFrame.")
            output_df[new_col] = None

    # Some columns are empty/arbitrary in the case of field QC,
    # but present in the final QC so should be taken if available.
    # In case of field QC sample data,
    # FlightID and TideStage seem to be empty. 
    # FrameId appears to be a constant "MM010193".
    if 'FlightId' in df_images.columns:
        output_df['FlightId'] = df_images['FlightId']
    elif 'FlightLineId' in df_images.columns:
        output_df['FlightId'] = df_images['FlightLineId']
    else:
        output_df['FlightId'] = None
    if 'TideStage' in df_images.columns:
        output_df['TideStage'] = df_images['TideStage']
    else:
        output_df['TideStage'] = None
    if 'FrameId' in df_images.columns:
        output_df['FrameId'] = df_images['FrameId']
    elif 'SerialNumber' in df_images.columns:
        output_df['FrameId'] = df_images['SerialNumber']
    else:
        output_df['FrameId'] = None
    output_type_dict['FrameId'] = str
    output_type_dict['TideStage'] = str

    # Use the "datetime" (index) column as is, if present
    try:
        output_df['time'] = df_images.index
    except KeyError:
        logger.warning("No 'datetime' column/index found in input DataFrame; setting to None.")
        output_df['time'] = None

    # Ensure columns are in the correct final order
    final_columns_order = ['ImageId']
    for datum in datum_list:
        if datum.lower() == 'bmhw':
            final_columns_order.append('MHW')
        else:
            final_columns_order.append(datum.upper())
        final_columns_order.append(datum.upper() + '_pass')
    final_columns_order = final_columns_order + \
    [
        'Tolerance', 'Roll', 'FlightId', 'FrameId', 
        'TideStage', 'time', 'lat', 'long', 'geometry'
    ]
    output_df = output_df[final_columns_order]
    # Ensure columns are of the correct type.
    output_df = output_df.astype(output_type_dict)

    # Convert z units as needed.
    output_df = convert_output_z_units(output_df, datum_list, output_z_units)

    # Save the final DataFrame to GeoPackage
    datestr = init_datetime.strftime('%Y%m%dT%H')
    fileext = '.gpkg'
    filename = '_'.join([project_name, '_'.join(datum_list), datestr, 'qc'])
    outpath = pathlib.Path(outdir) / (filename + fileext)

    gdf = gpd.GeoDataFrame(output_df, geometry='geometry')
    gdf.to_file(outpath, driver='GPKG', index=False)

    return None


def shapefile_qc(
    df_images: gpd.GeoDataFrame | pd.DataFrame,
    project_name: str,
    datum_list: List[str],
    z_units: str,
    init_datetime: datetime.datetime,
    outdir: str | pathlib.Path
) -> None:
    """Write a Shapefile with QC results for each image.

    Contains columns:
        ImageId
        <datum> (for all in datum_list)
        <datum>_pass (for all in datum_list)
        Tolerance
        Roll
        FlightId [blank]
        FrameId [unknown hard coded constant]
        TideStage [blank]
        date (yyyy-mm-dd)
        time (hh:mm:ss)
        lat
        long
        geometry
    """
    # Define units to use.
    default_z_units = 'ft'
    output_z_units = get_output_z_units(z_units, default_z_units)

    # Create a new DataFrame to hold the transformed data
    output_df = pd.DataFrame()
    output_type_dict = {}

    # Add existing data.
    column_mapping = {
        'ImageId': 'ImageId',
        'Tolerance': 'tolerance',
        'Roll': 'Roll',
        'lat': 'lat',
        'long': 'long',
        'geometry': 'geometry'
    }
    for datum in datum_list:
        # Add "relative to datum" column.
        try:
            if datum.lower() == 'bmhw':
                output_df['MHW'] = df_images['zeta'] - df_images['mhw_minus_lmsl']
            else:
                output_df[datum.upper()] = df_images['zeta'] - df_images[datum.lower() + '_minus_lmsl']
        except KeyError:
            logger.warning(f"Warning: Expecting columns 'zeta' and '{datum.lower() + '_minus_lmsl'}' in the input DataFrame.")
            logger.warning(f"Found columns: {df_images.columns.tolist()}")
        # Add pass fail column for each datum.
        column_mapping[datum.upper() + '_pass'] = datum.lower() + '_in_range'
        output_type_dict[datum.upper() + '_pass'] = 'str'

    # Remap columns from df_images to output_df.
    for new_col, old_col in column_mapping.items():
        if old_col in df_images.columns:
            output_df[new_col] = df_images[old_col]
        else:
            logger.warning(f"Warning: Column '{old_col}' not found in the input DataFrame.")
            output_df[new_col] = None

    # Some columns are empty/arbitrary in the case of field QC,
    # but present in the final QC so should be taken if available.
    # In case of field QC sample data,
    # FlightID and TideStage seem to be empty. 
    # FrameId appears to be a constant "MM010193".
    if 'FlightId' in df_images.columns:
        output_df['FlightId'] = df_images['FlightId']
    elif 'FlightLineId' in df_images.columns:
        output_df['FlightId'] = df_images['FlightLineId']
    else:
        output_df['FlightId'] = None
    if 'TideStage' in df_images.columns:
        output_df['TideStage'] = df_images['TideStage']
    else:
        output_df['TideStage'] = None
    if 'FrameId' in df_images.columns:
        output_df['FrameId'] = df_images['FrameId']
    elif 'SerialNumber' in df_images.columns:
        output_df['FrameId'] = df_images['SerialNumber']
    else:
        output_df['FrameId'] = None
    output_type_dict['FrameId'] = str
    output_type_dict['TideStage'] = str

    # Extract date and time from datetime column or index, if present
    try:
        dt_series = df_images.reset_index()['datetime']
        output_df['date'] = pd.to_datetime(dt_series).dt.strftime('%Y-%m-%d').values
        output_df['time'] = pd.to_datetime(dt_series).dt.strftime('%H:%M:%S').values
    except Exception:
        logger.warning("No 'datetime' column/index found in input DataFrame; setting date and time to None.")
        output_df['date'] = None
        output_df['time'] = None
    output_type_dict['date'] = 'datetime64[ms]'

    # Ensure columns are in the correct final order
    final_columns_order = ['ImageId']
    for datum in datum_list:
        if datum.lower() == 'bmhw':
            final_columns_order.append('MHW')
        else:
            final_columns_order.append(datum.upper())
        final_columns_order.append(datum.upper() + '_pass')
    final_columns_order += [
        'Tolerance', 'Roll', 'FlightId', 'FrameId', 'TideStage',
        'date', 'time', 'lat', 'long', 'geometry'
    ]
    output_df = output_df[final_columns_order]
    # Ensure columns are of the correct type.
    output_df = output_df.astype(output_type_dict)

    # Convert z units as needed.
    output_df = convert_output_z_units(output_df, datum_list, output_z_units)

    # Save the final DataFrame to Shapefile
    datestr = init_datetime.strftime('%Y%m%dT%H')
    fileext = '.shp'
    filename = '_'.join([project_name, '_'.join(datum_list), datestr, 'qc'])
    outpath = pathlib.Path(outdir) / (filename + fileext)

    gdf = gpd.GeoDataFrame(output_df, geometry='geometry')
    gdf.to_file(outpath, index=False)

    return None


def geojson_qc(
    df_images: gpd.GeoDataFrame | pd.DataFrame,
    project_name: str,
    datum_list: List[str],
    z_units: str,
    init_datetime: datetime.datetime,
    outdir: str | pathlib.Path
) -> None:
    """Write a GeoJSON with QC results for each image.

    Contains columns:
        ImageId
        <datum> (for all in datum_list)
        <datum>_pass (for all in datum_list)
        Tolerance
        Roll
        FlightId [blank]
        FrameId [unknown hard coded constant]
        TideStage [blank]
        time
        lat
        long
        geometry
    """
    # Define units to use.
    default_z_units = 'ft'
    output_z_units = get_output_z_units(z_units, default_z_units)

    # Create a new DataFrame to hold the transformed data
    output_df = pd.DataFrame()
    output_type_dict = {}

    # Add existing data.
    column_mapping = {
        'ImageId': 'ImageId',
        'Tolerance': 'tolerance',
        'Roll': 'Roll',
        'lat': 'lat',
        'long': 'long',
        'geometry': 'geometry'
    }
    for datum in datum_list:
        # Add "relative to datum" column.
        try:
            if datum.lower() == 'bmhw':
                output_df['MHW'] = df_images['zeta'] - df_images['mhw_minus_lmsl']
            else:
                output_df[datum.upper()] = df_images['zeta'] - df_images[datum.lower() + '_minus_lmsl']
        except KeyError:
            logger.warning(f"Warning: Expecting columns 'zeta' and '{datum.lower() + '_minus_lmsl'}' in the input DataFrame.")
            logger.warning(f"Found columns: {df_images.columns.tolist()}")
        # Add pass fail column for each datum.
        column_mapping[datum.upper() + '_pass'] = datum.lower() + '_in_range'
        output_type_dict[datum.upper() + '_pass'] = 'str'
    
    # Remap columns from df_images to output_df.
    for new_col, old_col in column_mapping.items():
        if old_col in df_images.columns:
            output_df[new_col] = df_images[old_col]
        else:
            logger.warning(f"Warning: Column '{old_col}' not found in the input DataFrame.")
            output_df[new_col] = None

    # Some columns are empty/arbitrary in the case of field QC,
    # but present in the final QC so should be taken if available.
    # In case of field QC sample data,
    # FlightID and TideStage seem to be empty. 
    # FrameId appears to be a constant "MM010193".
    if 'FlightId' in df_images.columns:
        output_df['FlightId'] = df_images['FlightId']
    elif 'FlightLineId' in df_images.columns:
        output_df['FlightId'] = df_images['FlightLineId']
    else:
        output_df['FlightId'] = None
    if 'TideStage' in df_images.columns:
        output_df['TideStage'] = df_images['TideStage']
    else:
        output_df['TideStage'] = None
    if 'FrameId' in df_images.columns:
        output_df['FrameId'] = df_images['FrameId']
    elif 'SerialNumber' in df_images.columns:
        output_df['FrameId'] = df_images['SerialNumber']
    else:
        output_df['FrameId'] = None
    output_type_dict['FrameId'] = str

    # Use the "datetime" (index) column as is, if present
    try:
        output_df['time'] = df_images.reset_index()['datetime'].values
    except KeyError:
        logger.warning("No 'datetime' column/index found in input DataFrame; setting to None.")
        output_df['time'] = None

    # Ensure columns are in the correct final order
    final_columns_order = ['ImageId']
    for datum in datum_list:
        if datum.lower() == 'bmhw':
            final_columns_order.append('MHW')
        else:
            final_columns_order.append(datum.upper())
        final_columns_order.append(datum.upper() + '_pass')
    final_columns_order = final_columns_order + \
    [
        'Tolerance', 'Roll', 'FlightId', 'FrameId', 
        'TideStage', 'time', 'lat', 'long', 'geometry'
    ]
    output_df = output_df[final_columns_order]
    # Ensure columns are of the correct type.
    output_df = output_df.astype(output_type_dict)

    # Convert z units as needed.
    output_df = convert_output_z_units(output_df, datum_list, output_z_units)

    # Save the final DataFrame to GeoPackage
    datestr = init_datetime.strftime('%Y%m%dT%H')
    fileext = '.geojson'
    filename = '_'.join([project_name, '_'.join(datum_list), datestr, 'qc'])
    outpath = pathlib.Path(outdir) / (filename + fileext)

    gdf = gpd.GeoDataFrame(output_df, geometry='geometry')
    gdf.to_file(outpath, driver='GeoJSON', index=False)

    return None


"""
Differences between field and final QC:

It seems that, for all file formats:
same format, but data seems to be slightly 
different (including times, lat, long, etc.).
Rows are in a different order too.

Tested with:
for ext in ['csv', 'shp', 'geojson', 'gpkg']:
...     df2 = gpd.read_file('~/ngs-flight-planning/data/output_files-20250321T164959Z-001/02_QC_Field_out/ImageEvents_C14764
3_1217241559565_003_RGB1_mhw_mllw_qc.' + ext)
...     df3 = gpd.read_file('AL2401_1217241559565_mhw_mllw.' + ext)
...     df2 = df2.set_index('ImageId').loc[df3.ImageId]
...     df3 = df3.set_index('ImageId')
...     print('\n\n' + ext + '\n------------------------------------------------------------------------')
...     print(df2.columns.equals(df3.columns))
...     for col in df2.columns:
...         try:
...             print(col)
...             print(df2[col].equals(df3[col]))
...             print((df2[col] - df3[col]).max())
...             print((df2[col] - df3[col]).min())
...         except:
...             pass
"""


"""Functions for reading NGS flight planning input files.

Functions
---------
load_lines_gdf

"""


import geopandas as gpd
import pandas as pd
import shapely
import sys
import logging
import pathlib
import datetime
from utils import hdms_to_dd


logger = logging.getLogger(__name__)


def load_lines_gdf(filepath: str) -> gpd.GeoDataFrame:
    """Read a flight lines file and return data as GeoDataFrame.

    Parameters
    ----------
    filepath
        The full path to the file containing flight lines,
        usually a "wpt" or waypoint file, which is a form 
        of human-readable CSV.

    Returns
    -------
    Geopandas data frame
        With one row per flight line.
        
    """
    df = pd.read_csv(filepath)
    gdf = gpd.GeoDataFrame(
        df, 
        geometry=[shapely.LineString([[hdms_to_dd(df.loc[i,'LON1']), 
                                       hdms_to_dd(df.loc[i,'LAT1'])], 
                                      [hdms_to_dd(df.loc[i,'LON2']), 
                                       hdms_to_dd(df.loc[i,'LAT2'])]]) 
                  for i in range(len(df.index))]
    )
    return gdf


def load_images_field_gdf(filepath: str) -> gpd.GeoDataFrame:
    """
    """
    df = pd.read_csv(filepath)
    
    # Convert time data.
    try:
        # Get GPS week.
        filedate_str = pathlib.Path(filepath).stem.split('_')[2][0:6]
        filedate_dt = datetime.datetime(int('20' + filedate_str[4:6]), 
                                        int(filedate_str[0:2]), 
                                        int(filedate_str[2:4]))
        gps_epoch = datetime.datetime(1980, 1, 6)
        time_difference = filedate_dt - gps_epoch
        gps_week_origin_dt = gps_epoch + datetime.timedelta(
            days=(7 * (time_difference.days // 7))
        )
        df['datetime'] = pd.to_datetime(
            df.Time, 
            unit='s', 
            origin=gps_week_origin_dt
        )
    except Exception as e:
        logger.warning(f'Unable to convert Time column to datetime: {e}')
    
    # Add Geometry.
    try:
        lat_name = 'Latitude'
        lon_name = 'Longitude'
        gdf = gpd.GeoDataFrame(
            df, 
            geometry=[
                shapely.Point(
                    [df.loc[i,lon_name], df.loc[i,lat_name]]
                ) 
                for i in range(len(df.index))
            ]
        )
        return gdf
    except Exception as e:
        logger.warning(f'Unable to find latitude & longitude names in data columns ({list(df.columns)})')
        logger.warning(e)
        return df 


def load_images_final_gdf(filepath: str) -> gpd.GeoDataFrame:
    """
    """
    df = pd.read_csv(filepath)
    
    # Convert time data.
    try:
        df['datetime'] = pd.to_datetime(
            df.Date + ' ' + df.Time, 
            format='%d-%b-%Y %H:%M:%S'
        )
    except Exception as e:
        logger.warning(f'Unable to convert Date and Time columns to datetime: {e}')
    
    # Add Geometry.
    try:
        lat_name = 'Lat'
        lon_name = 'Long'
        gdf = gpd.GeoDataFrame(
            df, 
            geometry=[
                shapely.Point(
                    [df.loc[i,lon_name], df.loc[i,lat_name]]
                ) 
                for i in range(len(df.index))
            ]
        )
        return gdf
    except Exception as e:
        logger.warning(f'Unable to find latitude & longitude names in data columns ({list(df.columns)})')
        logger.warning(f'{e}')
        return df 


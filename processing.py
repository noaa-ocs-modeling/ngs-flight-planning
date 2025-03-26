"""Functions to process data on NGS flight lines and image points.
"""


from pyproj import Geod, CRS
import geopandas as gpd
import pandas as pd
import shapely
import sys
from utils import hdms_to_dd


def point_table_from_lines(df_lines: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    """
    # Specify which columns to keep from the lines table (if they occur).
    keep_cols = [col for col in 
                 ['LINE', 'SCALE', 'EMULSION', 'GRND_EL']
                 if col in df_lines.columns]
    
    # Set up geodetic calculation.
    # NAD83:
    g = CRS.from_epsg(26917).get_geod() 
    # WGS84
    # g = Geod(ellps='WGS84')
    # Clark 1866:
    # g = Geod(ellps='clrk66')
    
    # Set up table to hold points.
    df_list = []

    # Loop over lines and calculate intermediate points.
    for ll in df_lines.index:
        int_points = g.inv_intermediate(
            hdms_to_dd(df_lines.loc[ll,'LON1']),
            hdms_to_dd(df_lines.loc[ll,'LAT1']),
            hdms_to_dd(df_lines.loc[ll,'LON2']),
            hdms_to_dd(df_lines.loc[ll,'LAT2']),
            npts=df_lines.loc[ll,'PHOTOS'],
            initial_idx=0,
            terminus_idx=0,
            return_back_azimuth=False
        )
        # Create intermediate data frame for this line.
        df_int = gpd.GeoDataFrame( 
            {**{col:df_lines.loc[ll,col] for col in keep_cols},
             'LAT':int_points.lats,
             'LON':int_points.lons,
             'geometry':[shapely.Point([lon, lat]) for lon,lat in 
                         zip(int_points.lons, int_points.lats) ]}
        )
        df_list.append(df_int)
    
    df_points = gpd.GeoDataFrame(pd.concat(df_list, ignore_index=True))
    return df_points


def interp_time(ds: xarray.Dataset, 
                timestep_seconds: int = 60) -> xarray.Dataset:
    """
    """
    pass


def calc_sun_alt(ds: xarray.Dataset,
                 time_var: str = 'time', 
                 x_var: str = 'lon', 
                 y_var: str = 'lat') -> xarray.Dataset:
    """
    """
    pass


def windows_from_bool(ds: xarray.Dataset) -> xarray.Dataset:
    """
    """
    pass


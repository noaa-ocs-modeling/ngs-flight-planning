"""Functions to process data on NGS flight lines and image points.

Functions
---------
point_table_from_lines(df_lines: gpd.GeoDataFrame) -> gpd.GeoDataFrame

"""


import logging
from pyproj import Geod, CRS
import geopandas as gpd
import pandas
import xarray
import shapely
import numpy
import pvlib
import sys
import math
from utils import hdms_to_dd


logger = logging.getLogger(__name__)


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
             'POINT_NUM':list(range(1, 1 + df_lines.loc[ll,'PHOTOS'])),
             'geometry':[shapely.Point([lon, lat]) for lon,lat in 
                         zip(int_points.lons, int_points.lats) ]}
        )
        df_list.append(df_int)
    
    df_points = gpd.GeoDataFrame(pandas.concat(df_list, ignore_index=True))
    return df_points


def interp_time(ds: xarray.Dataset, 
                timestep_seconds: int = 60) -> xarray.Dataset:
    """
    """
    time_interp = numpy.arange(ds.time.min().data, 
                               ds.time.max().data 
                               + numpy.timedelta64(1, 's'), 
                               numpy.timedelta64(timestep_seconds, 's'), 
                               dtype='datetime64[ns]')
    return ds.interp(time=time_interp, method='linear')


def calc_sun_alt(
    df: pandas.DataFrame,
    time_var: str = 'time', 
    x_var: str = 'node_lon', 
    y_var: str = 'node_lat'
) -> xarray.Dataset:
    """Add solar elevation (aka altitude) to a dataframe.

    Assumes df has a multiindex with levels ['station', 'time'],
    and has lat and lon columns (with optional custom names).
    """
    df_out = df.reset_index()
    solpos = pvlib.solarposition.get_solarposition(
        time=df_out[time_var], 
        latitude=df_out[y_var], 
        longitude=df_out[x_var]
    )
    df_out['solar_elevation'] = solpos['elevation'].to_numpy()
    return df_out.set_index(['station', 'time'])


def calc_in_range(
    df: pandas.DataFrame,
    datums: list,
    base_datum: str = 'lmsl',
    z_var: str = 'zeta',
    min_solar_elevation: float = 25.0
) -> pandas.DataFrame:
    """
    """
    df_out = df.copy()
    for dat in datums:
        dat_var = '_'.join([dat, 'minus', base_datum])
        df_out[dat + '_in_range'] = (
            (df_out[z_var] >= df_out[dat_var] - df_out['tolerance']) 
            & 
            (df_out[z_var] <= df_out[dat_var] + df_out['tolerance'])
            &
            (df_out['solar_elevation'] >= min_solar_elevation)
        )
    return df_out


def point_windows_from_bool(
    df: pandas.DataFrame,
    datums: list, 
    x_var: str = 'node_lon', 
    y_var: str = 'node_lat'
) -> pandas.DataFrame:
    """
    """
    result = pandas.DataFrame()
    
    # Calculate windows separately for each datum.
    for dat in datums:
        
        # Work out which timesteps have a different "in_range" value
        # to the previous or following timestep: these represent 
        # window starts and ends.
        diff_back = df[dat + '_in_range'].astype('int')\
                    .groupby('station').diff()
        diff_fwd = df[dat + '_in_range'].astype('int')\
                   .groupby('station').diff(periods=-1)
        # Populate any NaNs (first or last timestep) with the in_range value
        # for that timestep.
        diff_back[[math.isnan(d) for d in diff_back]] = \
            df.loc[[math.isnan(d) for d in diff_back], dat + '_in_range']\
              .astype('int')
        diff_fwd[[math.isnan(d) for d in diff_fwd]] = \
            df.loc[[math.isnan(d) for d in diff_fwd], dat + '_in_range']\
              .astype('int')
        # Convert float types to integers.
        diff_back = diff_back.astype('int')
        diff_fwd = diff_fwd.astype('int')
        
        # Construct data frame of windows for this datum.
        df_window_starts = df[diff_back == 1].reset_index()[
            ['station', y_var, x_var, 'time']
        ].rename(columns={'time':'start_time'})
        df_window_starts['datum'] = dat
        df_window_starts = df_window_starts[['station', y_var, x_var, 
                                             'datum', 'start_time']]
        df_window_ends = df[diff_fwd == 1].reset_index()[
            ['station', y_var, x_var, 'time']
        ].rename(columns={'time':'end_time'})
        if not (df_window_starts.station == df_window_ends.station).all():
            logger.warning('windows_from_bool: mismatching stations in window starts and ends.')
        
        # Join this data with other datums' results.
        result = pandas.concat(
            [result, df_window_starts.join(df_window_ends['end_time'])],
            axis=0,
            join='outer', 
            ignore_index=True,
            sort=False
        )
    #
    return result


def line_windows_from_bool(df: pandas.DataFrame, 
                           df_points: pandas.DataFrame,
                           datums:list, 
                           point_step: int = 1) -> pandas.DataFrame:
    """
    """
    result = pandas.DataFrame()
    
    # There might be a way to do this with groupby('line') calls, but keeping it 
    # simple (and slow?) for now. 
    for line in pandas.unique(df_points.LINE):
        # Get the list of points on this line.
        all_points_on_line = sorted(list(
            df_points.reset_index().loc[df_points.LINE == line, 'index']
        ))
        # Subset this list to which we actually want to check 
        # for window overlaps.
        if point_step == 0:
            check_points_on_line = [
                all_points_on_line[0],
                all_points_on_line[1]
            ]
        else:
            check_points_on_line = all_points_on_line[::point_step]
            
        for dat in datums:
            check_col = dat + '_in_range'
            
            # Calculate which timesteps are in range for all 
            # required stations on this line.
            df_line = df.loc[check_points_on_line].reset_index()\
                        .pivot(index='time', columns='station', values=check_col)\
                        .all(axis='columns', bool_only=True)
            # Work out which timesteps have a different "in_range" value
            # to the previous or following timestep: these represent 
            # window starts and ends.
            diff_back = df_line.astype('int').diff()
            diff_fwd = df_line.astype('int').diff(periods=-1)
            # Populate any NaNs (first or last timestep) with the in_range value
            # for that timestep.
            diff_back[[math.isnan(d) for d in diff_back]] = \
                df_line.loc[[math.isnan(d) for d in diff_back]].astype('int')
            diff_fwd[[math.isnan(d) for d in diff_fwd]] = \
                df_line.loc[[math.isnan(d) for d in diff_fwd]].astype('int')
            # Convert float types to integers.
            diff_back = diff_back.astype('int')
            diff_fwd = diff_fwd.astype('int')
            # Construct data frame of windows for this datum.
            df_window_starts = df_line[diff_back == 1].reset_index()\
                               .rename(columns={'time':'start_time'})
            df_window_starts['line'] = line
            df_window_starts['datum'] = dat
            df_window_ends = df_line[diff_fwd == 1].reset_index()\
                             .rename(columns={'time':'end_time'})
            
            # Join this data with other datums' results.
            result = pandas.concat(
                [result, 
                 df_window_starts[['line', 'datum', 'start_time']]\
                 .join(df_window_ends['end_time'])],
                axis=0,
                join='outer', 
                ignore_index=True,
                sort=False
            )
            
    return result


                    
                
                
            
            


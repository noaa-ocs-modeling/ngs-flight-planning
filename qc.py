import logging
import argparse
import pathlib
import geopandas as gpd
import pandas as pd
import numpy as np
import xarray as xr
import datetime
import pytz
import shapely
import pvlib
#
import inputs 
import processing  
import mesh_handling
import outputs


logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s %(name)-15s %(levelname)-8s %(message)s', 
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)
# Logging strategy:
# It's helpful to know how long some of the heavy calculations take
# so they are added at "info" level. Basic signposting for other
# parts of the process are at the "debug" level.


def field_qc():
    # This will be calculated from the times in the image input file.
    init_datetime = datetime.datetime(2024,12,15)
    # These will be passed as command line args.
    images_file = 'data/input_file_examples/input_files/02_after_flight_qc/ImageEvents_C147643_1217241559565_003_RGB1.csv'
    datums = ['mllw', 'mhw']
    min_solar_elevation = 25.0

    # Read flight paths and calculate image points. 
    logger.debug('Reading image information...')
    df_images = inputs.load_images_field_gdf(images_file)
    
    # Load and subset forecast and datum data.
    logger.info('Loading forecast subset...')
    bbox = mesh_handling.get_box(df_images)
    ds_mesh = mesh_handling.load_forecast_ds(init_datetime, bbox, convert_to_local_msl=True)
    logger.info('Finished loading forecast subset.')
    
    logger.info('Adding datums...')
    # We want all in `datums`, plus MLW and MHW to calculate range.
    for datum in list(set(datums + ['mhw', 'mlw'])):
        ds_mesh = mesh_handling.ds_add_datum(ds_mesh, datum)
    logger.info('Finished adding datums...')
    
    logger.info('Dropping NaN data...')
    # For window calculations, we need a time series with no missing data,
    # and valid datum values, so we exclude model points that don't meet 
    # that criterium.
    ds_drop = ds_mesh.dropna('node', how='any', subset=['mllw_minus_lmsl', 'zeta'])
    ds_drop_zeta = ds_mesh.dropna('node', how='any', subset=['zeta'])
    logger.info(f'Number of nodes: full subset {len(ds_mesh.node)}; ' + 
                f'NaN in zeta {len(ds_drop_zeta.node)}; ' + 
                f'NaN in zeta or datum {len(ds_drop.node)}.')
    
    if 'Latitude' in df_images.columns:
        df_x_name = 'Longitude'
        df_y_name = 'Latitude'
    elif 'Lat' in df_images.columns:
        df_x_name = 'Long'
        df_y_name = 'Lat'
    else:
        logger.warning(f'Unable to find latitude & longitude names in data columns ({list(df_images.columns)})')
    
    logger.debug('Calculating nearest nodes to image positions...')
    # Using only model nodes with no missing data, as described above. 
    inds, dists = mesh_handling.get_nearest_inds_dists(
        ds_drop,
        df_images,
        n_nearest=1,
        ds_x_var='lon', 
        ds_y_var='lat',
        df_x_var=df_x_name,
        df_y_var=df_y_name
    )
    
    logger.debug('Subsetting to nearest nodes...')
    # Note that the lat and lon values in this dataset 
    # are now the model node locations, not the image 
    # point locations. 
    ds_points_model_timeseries = ds_drop.sel(node=inds).isel(k=0)
    
    logger.debug('Calculating tidal range and tolerance...')
    # Range = MHW - MLW.
    # Tolerance based on 2014 NGS/RSD memo.
    ds_points_model_timeseries = mesh_handling.ds_add_tidal_range(
        ds_points_model_timeseries
    )
    ds_points_model_timeseries = mesh_handling.tidal_tol_from_range(
        ds_points_model_timeseries
    )
    
    # This is where the process diverges from the planning method.
    # We now interpolate from the model time series to each image's 
    # time+location separately for each point, to get water level 
    # data, as well as in/out of bounds flags, for each image point
    # (i.e., for as many rows as df_images has).
    
    # Interpolate to the image capture times.
    # This results in water level variables (zeta) where both
    # space and time dimensions have length equal to number of images.
    logger.debug('Interpolating model data in time...')
    ds_model_obs_times = ds_points_model_timeseries.interp(
        time=df_images.datetime, 
        method='linear',
        assume_sorted=False,
        method_non_numeric='nearest'
    )
    # We then want to take the diagonal elements of these square arrays.
    da_isel = xr.DataArray(
        np.zeros(len(df_images)), 
        dims=['image'], 
        coords={'image':np.arange(len(df_images))}
    )
    ds_model_interp = ds_model_obs_times.isel(
        station=da_isel.image, 
        time=da_isel.image
    )
    
    logger.debug('Converting to pandas data frame...')
    # Renames the model node lat and lon columns, both for clarity
    # and to avoid conflicts when joining with the image location
    # lat and lon.
    df_interp = ds_model_interp[
        [v for v in ds_model_interp.data_vars if 'image' in ds_model_interp[v].dims]
    ].to_dataframe().rename(columns={'lat':'node_lat', 'lon':'node_lon'})
    # Times so far are in UTC: add this explicitly.
    df_interp = df_interp.set_index('time').tz_localize('UTC').reset_index()

    logger.info('Calculating solar elevation angles...')
    # This needs a bit of hacking to get the right column names etc.
    df_interp = processing.calc_sun_alt(
        df_interp.reset_index()
        .rename(columns={'index':'station'})
        .set_index(['station','time'])
    ).reset_index().set_index('time')
    
    logger.debug('Calculating times when water level in range...')
    df_interp = processing.calc_in_range(
        df_interp, datums, min_solar_elevation=min_solar_elevation
    )
    
    # This is the data we need, and we just need to join 
    # it with the images table now.
    logger.debug('Joining water levels with image info...')
    df_out = pd.merge(
        df_images.set_index('datetime').tz_localize('UTC'), 
        df_interp, 
        left_index=True, right_index=True
    )
    
    # Create output files.
    outputs.output_all_qc(df_out, 'AL2401', datums, init_datetime, 'data/testing/qc')
    #
    return df_out


def final_qc():
    images_file = 'data/input_file_examples/input_files/03_final_qc/AL2401_1217241559565.CSV'

    # Read flight paths and calculate image points. 
    logger.debug('Reading image information...')
    df_images = inputs.load_images_final_gdf(images_file)
    
    # Load and subset forecast and datum data.
    logger.info('Loading forecast subset...')
    bbox = mesh_handling.get_box(df_images)
    """
    ds_mesh = mesh_handling.load_forecast_ds(init_datetime, bbox, convert_to_local_msl=True)
    logger.info('Finished loading forecast subset.')
    
    logger.info('Adding datums...')
    # We want all in `datums`, plus MLW and MHW to calculate range.
    for datum in list(set(datums + ['mhw', 'mlw'])):
        ds_mesh = mesh_handling.ds_add_datum(ds_mesh, datum)
    logger.info('Finished adding datums...')
    """
    
    return df_images


if __name__ == '__main__':
    df = field_qc()
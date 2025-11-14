"""The main function for post-flight QC with STOFS forecast water levels.

And also its command line argument parser.

Usage will usually be from the command line, so the functions
listed here are not often called directly. 

Example:
    $ python qc.py AL2401_qc data/ImageEvents.csv -q field -o data/testing -l DEBUG
    $ python qc.py AL2401_qc data/input_files-20250321T164954Z-001/input_files/02_after_flight_qc/ImageEvents_C147643_1217241559565_003_RGB1.csv -q field -o data/testing -l DEBUG

Functions
---------
main
qc_arg_parser

"""


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


def main(
    project_name: str,
    images_file: str,
    qc_mode: str,
    datums: list,
    output_dir: pathlib.Path | str,
    min_solar_elevation: float,
    output_time_zone: str,
) -> pd.DataFrame:
    """
    Main entry point for post-flight QC processing using STOFS forecast water levels.

    This function reads image metadata, loads and subsets the forecast model,
    interpolates water levels to image locations and times, calculates tidal
    range and tolerance, evaluates in-range flags for each datum, and writes
    a suite of QC output files in various formats.

    Parameters
    ----------
    project_name : str
        Name of the project, used in naming output files.
    images_file : str
        Path to the file containing image locations and times.
    qc_mode : str
        Quality control mode, one of ['field', 'final'].
    datums : list
        List of datum names to process (e.g., ['mllw', 'mhw']).
    output_dir : pathlib.Path or str
        Directory in which to create the project's output directory.
    min_solar_elevation : float
        Minimum solar elevation to test if image meets requirements.
    output_time_zone : str
        Timezone for output times (must be a valid pytz timezone string).

    Returns
    -------
    pd.DataFrame
        DataFrame containing the merged image and interpolated model data,
        with QC results for each image.
    
    """
    logger.info(f'Processing data for project {project_name}')
    logger.info(f'QC mode: {qc_mode}')
    logger.info(f'Flight images file: {images_file}')
    logger.info(f"Datums requested: {', '.join(datums)}")
    logger.info(f'Minimum solar elevation: {min_solar_elevation} degrees')
    if output_time_zone not in pytz.all_timezones:
        logger.warning('Specified output_time_zone not available in pytz: defaulting to UTC.')
        output_time_zone = 'UTC'
    logger.info(f'Output timezone: {output_time_zone}')

    # Get (and create, if needed) output directory.
    save_dir = outputs.get_create_output_dir(output_dir, project_name)
    logger.info(f'Output will be saved to: {str(save_dir)}')

    # Read flight paths and calculate image points. 
    logger.debug('Reading image information...')
    if qc_mode == 'field':
        df_images = inputs.load_images_field_gdf(images_file)
    elif qc_mode == 'final':
        df_images = inputs.load_images_final_gdf(images_file)
    else:
        logger.error(f"qc_mode {qc_mode} not recognized. Must be one of ['field', 'final'].")
        raise ValueError(f'qc_mode {qc_mode} not recognized.')
    
    # Calculate forecast initialization time.
    init_datetime = inputs.get_forecast_init_time(df_images.datetime)
    logger.info(f'Forecast initialization time: {init_datetime.strftime("%Y-%m-%d %HZ")}')

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
    
    if 'lat' in df_images.columns:
        df_x_name = 'long'
        df_y_name = 'lat'
    elif 'latitude' in df_images.columns:
        df_x_name = 'longitude'
        df_y_name = 'latitude'
    elif 'Lat' in df_images.columns:
        df_x_name = 'Long'
        df_y_name = 'Lat'
    elif 'Latitude' in df_images.columns:
        df_x_name = 'Longitude'
        df_y_name = 'Latitude'
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
    # For some reason, the index name can be lost in the merge.
    # Set it manually here.
    if df_out.index.name is None:
        df_out.index.name = 'datetime'

    # Convert times to desired timezone.
    logger.warning(f'Converting times to {output_time_zone}...')
    logger.warning('ATTENTION: Take care when using time information in GIS software. Geopackage (.gpkg) files may contain timezone information, but shapefiles (.shp) do not.')
    logger.debug('Before conversion:')
    logger.debug(df_out)
    df_out.index = df_out.index.tz_convert(output_time_zone)
    logger.debug('After conversion:')
    logger.debug(df_out)

    # Create output files.
    outputs.output_all_qc(df_out, project_name, datums, init_datetime, save_dir)
    #
    return df_out


def qc_arg_parser():
    """Return arg parser for NGS QC data processing function."""
    parser = argparse.ArgumentParser()
    parser.add_argument("project", type=str,
                        help="Name of project, used in naming output files.")
    parser.add_argument("images_filepath", type=str,
                        help="Path and name of file defining image locations and times. Can be a relative or absolute path.")
    parser.add_argument('-q', '--qc_mode', type=str,
                        default='field',
                        help="Quality Control mode, one of ['field', 'final'] (default: %(default)s)")
    parser.add_argument('-d', '--datums', nargs='+', 
                        default=['mllw', 'mhw'],
                        help="Space separated list of datums to process, e.g., '-d mllw mlw mhw' (default: %(default)s)")
    parser.add_argument('-o', '--output_directory', 
                        default=pathlib.Path('./data').resolve(), 
                        help="Directory within which to create the project's saved data directory (default: %(default)s)")
    parser.add_argument('-e', '--min_solar_elevation', type=float, 
                        default=25.0,
                        help="Minimum solar elevation required for imaging time selection (default: %(default)s)")
    parser.add_argument('-z', '--output_time_zone', type=str, 
                        default='UTC',
                        help="The timezone to convert output times to, e.g., 'UTC', 'US/Eastern', 'US/Alaska'. This must be one of the timezones available in `pytz`. See https://en.wikipedia.org/wiki/List_of_tz_database_time_zones for more options. (default: %(default)s)")
    parser.add_argument('-l', '--logging-level', type=str,
                        default='INFO',
                        help="Logging level passed to program logger ( one of ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'] default: %(default)s)")
    #
    return parser


if __name__ == '__main__':
    # Set up command line argument parser.
    parser = qc_arg_parser()
    args = parser.parse_args()
    logger.setLevel(level=args.logging_level)
    # Run the main script.
    df = main(
        args.project,
        pathlib.Path(args.images_filepath).resolve(),
        args.qc_mode,
        args.datums,
        pathlib.Path(args.output_directory).resolve(),
        args.min_solar_elevation,
        args.output_time_zone
    )
"""Functions for handling STOFS forecast mesh files.

Functions
---------
get_box
load_forecast_ds
get_nearest_inds_dists
ds_add_datum
ds_add_tidal_range
tidal_tol_from_range

"""


import logging
import sys
import shapely
import geopandas as gpd
import datetime
import xarray
import pandas
import numpy
import scipy
import s3fs
import xarray_subset_grid
import math
from coastalmodeling_vdatum import vdatum
from obstore.store import S3Store
from virtualizarr.parsers import HDFParser
from virtualizarr.registry import ObjectStoreRegistry
from utils import switch_lon_lims


logger = logging.getLogger(__name__)


def get_box(geometries: gpd.GeoDataFrame, 
            buffer: float = 0.1) -> shapely.box:
    """Get a buffered box around geometries in a geopandas data frame.

    Parameters
    ----------
    geometries
        The collection of geometries around which the box will be defined.
    buffer
        Additional buffer around the box.

    Returns
    -------
    Shapely box
        A single polygon containing the union of all the geometries in 
        the input data frame.
        
    """
    tb = geometries.total_bounds
    bbox = shapely.box(tb[0] - buffer, tb[1] - buffer,
                       tb[2] + buffer, tb[3] + buffer)
    return bbox


def load_forecast_ds(init_datetime: datetime.datetime, 
                     bbox: shapely.box,
                     convert_to_local_msl: bool = True) -> xarray.Dataset:
    """Subset and load a mesh file for a lat-lon box, using xarray-subset-grid.

    Hardcoded to return a single STOFS-2D-Global forecast run.
    
    Can be slow (~15 minutes).

    Parameters
    ----------
    init_datetime
        The initialization datetime of the forecast to load.
    bbox
        The bounding box of the region to load.
    convert_to_local_msl
        Whether or not to convert to local mean sea level.
    
    Returns
    -------
    xarray dataset containing forecast data on original model mesh.
    
    """
    
    # Load global dataset.
    yyyymmdd = init_datetime.strftime('%Y%m%d')
    hh = init_datetime.strftime('%H')
    aws_bucket = 'noaa-gestofs-pds'
    subdir = f'stofs_2d_glo.{yyyymmdd}'
    filename = f'stofs_2d_glo.t{hh}z.fields.cwl.nc'
    #
    store = S3Store(
        bucket=aws_bucket,
        region="us-east-1",
        skip_signature=True,
        client_options={"timeout": "300s", "connect_timeout":"60s"},
        retry_config={"max_attempts": 5}
    )
    registry = ObjectStoreRegistry({f"s3://{aws_bucket}": store})
    parser = HDFParser()
    manifest_store = parser(
        url=f"s3://{aws_bucket}/{subdir}/{filename}",
        registry=registry
    )
    logger.info('Opening data file...')
    ds = xarray.open_zarr(
        manifest_store,
        consolidated=False,
        zarr_format=3,
    )
    logger.info('Finished opening data file.')
    logger.info('Assigning grid topology...')
    ds = xarray_subset_grid.grids.ugrid.assign_ugrid_topology(ds)
    logger.info('Finished assigning grid topology.')

    # Subset to box. 
    logger.info('Subsetting...')
    subset_ds = ds.xsg.subset_polygon(shapely.get_coordinates(bbox))
    logger.info('Finished subsetting.')
    logger.info('Loading dataset...')
    logger.info('(This may take some time)')
    subset_ds.load()
    logger.info('Finished loading dataset.')

    # Optionally convert to local mean sea level.
    if convert_to_local_msl:
        lmsl_filename = 'noaa-nos-stofs2d-pds/_archive/msl_2017-2019_avg/GSTOFSv5.6.5_msl_2017-2019_avg_20241619.nc'
        logger.info('Opening LMSL dataset...')
        s3 = s3fs.S3FileSystem(anon=True)
        ds_lmsl = xarray.open_dataset(
            s3.open(f's3://{lmsl_filename}', 'rb')
        )
        logger.info('Assigning grid topology...')
        ds_lmsl = xarray_subset_grid.grids.ugrid.assign_ugrid_topology(ds_lmsl)
        logger.info('Subsetting LMSL data...')
        subset_ds_lmsl = ds_lmsl.xsg.subset_polygon(shapely.get_coordinates(bbox))
        logger.info('Loading LMSL data...')
        subset_ds_lmsl.load()
        logger.info('Subtracting LMSL...')
        if subset_ds['zeta'].node.shape == subset_ds_lmsl['mean_sea_level'].node.shape:
            subset_ds['zeta'] = subset_ds['zeta'] - subset_ds_lmsl['mean_sea_level']
        else:
            logger.warning('Cannot subtract STOFS mean sea level: shape mismatch. Attempting manual node matching.')
            if numpy.allclose(ds.y.data, ds_lmsl.y.data) and numpy.allclose(ds.x.data, ds_lmsl.x.data):
                ds = ds.assign_coords(node=('node', range(ds.node.shape[0])))
                subset_inds = ds.xsg.subset_polygon(shapely.get_coordinates(bbox))
                manual_subset_lmsl = ds_lmsl.isel(node=subset_inds['node'].data)
                subset_ds['zeta'] = subset_ds['zeta'] - manual_subset_lmsl['mean_sea_level']
                logger.info('Manual node matching successful. Subtracted LMSL.')
            else:
                logger.error('Manual node matching failed: forecast and LMSL data have different x and y coordinates. Cannot subtract LMSL.')
                raise ValueError('Manual node matching failed: forecast and LMSL data have different x and y coordinates. Cannot subtract LMSL.')



    logger.info('Renaming x and y coordinates to match thalassa.')
    return subset_ds.rename({'x':'lon', 'y':'lat'})


def get_nearest_inds_dists(
    ds_mesh: xarray.Dataset, 
    df_stations: pandas.DataFrame,
    n_nearest: int = 10,
    ds_x_var: str = 'x', 
    ds_y_var: str = 'y',
    df_x_var:str = 'longitude', 
    df_y_var: str = 'latitude'
) -> tuple[xarray.DataArray, xarray.DataArray]:
    """Get indices and distances to nearest points in dataset.

    If the "station" data frame only has 1 station, might need to use
        df_stations.loc[0].to_frame().transpose()
    or
        df_stations.loc[0:0]
    to get the right format.

    Parameters
    ----------
    ds_mesh 
        Contains the forecast data on original mesh.
    df_stations
        Contains the stations to locate.
    n_nearest
        The number of nearest mesh points to a station to return.
    ds_x_var 
        The name of the x/longitude variable in the mesh dataset.
    ds_y_var
        The name of the y/latitude variable in the mesh dataset.
    df_x_var 
        The name of the x/longitude variable in the station dataframe.
    df_y_var
        The name of the y/latitude variable in the station dataframe.
        
    Returns
    -------
    Tuple of two datasets containing (1) the indices and (2) the distances
    to the station, of the nearest mesh nodes. Each of these two datasets 
    is 2D, with having dimensions (station, k), where k denotes the position
    in the sequence from 0 to (n_nearest - 1) of proximity to the station.
    
    """
    tree = scipy.spatial.cKDTree(
        numpy.column_stack((ds_mesh[ds_x_var].data,
                            ds_mesh[ds_y_var].data))
    )
    dists, inds = tree.query(
        tuple(zip(df_stations[df_x_var], df_stations[df_y_var])), 
        k=n_nearest
    )
    # Make sure that outputs are 2-dimensional (station, k), 
    # even if some dimensions are length 1.
    if n_nearest == 1:
        dists  = numpy.expand_dims(dists, axis=1)
        inds  = numpy.expand_dims(inds, axis=1)
    return xarray.DataArray(inds, dims=["station", "k"]), \
        xarray.DataArray(dists, dims=["station", "k"])


def ds_add_datum(ds: xarray.Dataset,
                 target_datum: str,
                 base_datum: str = 'lmsl',
                 incl_time_axis: bool = False,
                 ds_y_name: str = 'lat',
                 ds_x_name: str = 'lon') -> xarray.Dataset:
    """Adds datum field to a STOFS dataset, relative to base_datum. 

    Parameters
    ----------
    ds
        The dataset to add a datum field to.
    target_datum
        The target datum to add, e.g., mllw.
    base_datum
        The datum relative to which target_datum values are expressed.
    incl_time_axis
        Whether to include time in the dimensionality of the return value.
        If True, the datum added will have dimensions (node, time).
        If False, the datum added will have dimensions (node).
    ds_y_name
        The name of the y/latitude variable in the mesh dataset.
    ds_x_name
        The name of the x/longitude variable in the mesh dataset.
    
    Returns
    -------
    A dataset that is the same as input ds, with an added field 
    representing the field target_datum=0 relative to base_datum.
    
    """
    # Array of zeros to represent base datum.
    z_dummy = numpy.zeros_like(ds[ds_y_name].data)
    
    # Convert to target (positive means below base).
    x, y, z_new = vdatum.convert(base_datum.lower(), target_datum.lower(), 
                                 ds[ds_y_name].data, ds[ds_x_name].data, z_dummy,
                                 online=True, epoch=None)
    
    # Deal with missing values and convert to height instead of depth.
    # This makes MHW (> LMSL) positive and MLLW (< LMSL) negative.
    z_ll = -1.0 * numpy.where(~numpy.isinf(z_new), z_new, numpy.nan)
    
    # Add to copy of dataset.
    ds_out = ds.copy()
    new_var_name = '_'.join([target_datum, 'minus', base_datum])
    if incl_time_axis:
        ds_out[new_var_name] = xarray.DataArray(
            numpy.tile(z_ll, (len(ds.time), 1)),
            dims=['time', 'node']
        )
        return ds_out
    else:
        ds_out[new_var_name] = xarray.DataArray(z_ll, dims=['node'])
        return ds_out


def ds_add_tidal_range(ds: xarray.Dataset,
                       incl_time_axis: bool = False,
                       ds_y_name: str = 'lat',
                       ds_x_name: str = 'lon') -> xarray.Dataset:
    """Adds tidal mean range field to a STOFS dataset.

    Parameters
    ----------
    ds
        The dataset to add a datum field to.
    incl_time_axis
        Whether to include time in the dimensionality of the return value.
        If True, the datum added will have dimensions (node, time).
        If False, the datum added will have dimensions (node).
    ds_y_name
        The name of the y/latitude variable in the mesh dataset.
    ds_x_name
        The name of the x/longitude variable in the mesh dataset.
    
    Returns
    -------
    A dataset that is the same as input ds, with an added field 
    ("mean_range") representing tidal range, i.e., (MHW - MLW)
    for most cases, or (MHW - MLLW) for the West Coast and Alaska.
    
    """
    ds_out = ds.copy()
    # Check if we need the west coast/Alaska range (MHW - MLLW)
    # or the default range (MHW - MLW).
    # For now we'll just do this assuming the entire dataset is either 
    # west coast/Alaska or not, but in the future we could make this 
    # spatially specific if needed.
    lons_m180_180 = switch_lon_lims(ds_out[ds_x_name].data, min_lon=-180.0)
    lats = ds_out[ds_y_name].data
    wcak_min_lon = -180.0
    wcak_max_lon = -110.0
    wcak_min_lat = 30.0
    wcak_max_lat = 76.0
    in_wcak = (
        (lons_m180_180 >= wcak_min_lon) & 
        (lons_m180_180 <= wcak_max_lon) & \
        (lats >= wcak_min_lat) & 
        (lats <= wcak_max_lat)
    )
    if numpy.all(in_wcak):
        logger.info('Dataset is entirely in the West Coast/Alaska region. Using range (MHW - MLLW).')
        use_wcak_range = True
    elif numpy.all(~in_wcak):
        logger.info('Dataset is entirely outside of the West Coast/Alaska region. Using default range (MHW - MLW).')
        use_wcak_range = False
    else:
        logger.error('Dataset contains some points in the West Coast/Alaska region and some points outside of it.')
        raise NotImplementedError('Cannot handle datasets that contain some points in the West Coast/Alaska region and some points outside of it. Please check the inputs or subset the data so that it is either entirely in or entirely out of the West Coast/Alaska region.')
    # Make sure we have the required variables.
    if use_wcak_range:
        range_lower_var = 'mllw_minus_lmsl'
        range_lower_datum = 'mllw'
    else:
        range_lower_var = 'mlw_minus_lmsl'
        range_lower_datum = 'mlw'
    if range_lower_var not in ds.data_vars:
        ds_out = ds_add_datum(ds, range_lower_datum, incl_time_axis=incl_time_axis, 
                              ds_y_name=ds_y_name, ds_x_name=ds_x_name)
    if 'mhw_minus_lmsl' not in ds.data_vars:
        ds_out = ds_add_datum(ds_out, 'mhw', incl_time_axis=incl_time_axis, 
                              ds_y_name=ds_y_name, ds_x_name=ds_x_name)
    # Calculate the range.
    ds_out['mean_range'] = ds_out['mhw_minus_lmsl'] - ds_out[range_lower_var]
    return ds_out


def tidal_tol_from_range(ds: xarray.Dataset,
                         range_var: str = 'mean_range') -> xarray.Dataset:
    """Calculate tolerance of water level for a given tidal range. 

    Tolerance is defined as the maximum allowable difference between water  
    level at the time of imaging and the datum level being surveyed. 
    
    The tolerance is calculated according to the 2014 NGS Memo.

    Parameters
    ----------
    ds
        Dataset containing at least a variable representing mean 
        tidal range.
    range_var
        The name of the variable in ds representing mean tidal range.
    
    Returns
    -------
    A dataset that is the same as input ds, with an added field 
    ("tolerance") representing the water level tolerance for each 
    location in the dataset. 
    
    """
    if range_var not in ds.data_vars:
        sys.exit('tidal_tol_from_range: range variable (default: mean_range) required to calculate tolerances.')
    # Tolerance calculation from memorandum of November 24, 2014. 
    ft_to_meters = 0.3048
    tol_thresh = 5.0 * ft_to_meters
    tol_fraction = 0.1
    tol_minimum = 0.5 * ft_to_meters
    tol = (tol_fraction * ds[range_var]).where(ds[range_var] > tol_thresh,
                                               other=tol_minimum, 
                                               drop=False)
    return ds.assign(tolerance=tol)
    
"""Contains functions for handling STOFS forecast mesh files.
"""


import shapely
import geopandas as gpd
import datetime
import xarray
import pandas
import scipy
import xarray_subset_grid
import s3fs
import thalassa
import math


def get_box(geometries: gpd.GeoDataFrame, 
            buffer: float = 0.1) -> shapely.box:
    """Get a buffered box around geometries in a geopandas data frame.
    """
    tb = geometries.total_bounds
    bbox = shapely.box(tb[0] - buffer, tb[1] - buffer,
                       tb[2] + buffer, tb[3] + buffer)
    return bbox


def load_forecast_ds(init_datetime: datetime.datetime, 
                     bbox: shapely.box,
                     convert_to_local_msl: bool = True) -> xarray.Dataset:
    """Subset and load a mesh file for a lat-lon box, using thalassa.

    Can be slow (~15 minutes).
    """
    # Load global dataset.
    yyyymmdd = init_datetime.strftime('%Y%m%d')
    hh = init_datetime.strftime('%H')
    aws_bucket = 'noaa-gestofs-pds'
    subdir = f'stofs_2d_glo.{yyyymmdd}'
    filename = f'stofs_2d_glo.t{hh}z.fields.cwl.nc'
    s3 = s3fs.S3FileSystem(anon=True)  # Enable anonymous access to the S3 bucket
    url = f's3://{aws_bucket}/{subdir}/{filename}'
    ds = xarray.open_dataset(s3.open(url, 'rb'), drop_variables=['nvel'])

    # Optionally convert to local mean sea level.
    if convert_to_local_msl:
        lmsl_filename = 'noaa-nos-stofs2d-pds/_archive/msl_2017-2019_avg/GSTOFSv5.6.5_msl_2017-2019_avg_20241619.nc'
        ds_lmsl = xarray.open_dataset(
            s3.open(f's3://{lmsl_filename}', 'rb')
        )
        ds['zeta'] = ds['zeta'] - ds_lmsl['mean_sea_level']
        
    # Subset to box. 
    subset_ds = thalassa.crop(thalassa.normalize(ds), bbox).load()
    return subset_ds


def load_forecast_ds_xsg(init_datetime: datetime.datetime, 
                         bbox: shapely.box,
                         convert_to_local_msl: bool = True) -> xarray.Dataset:
    """Subset and load a mesh file for a lat-lon box, using xarray-subset-grid.
    
    Can be slow (~15 minutes).
    """
    # Load global dataset.
    yyyymmdd = init_datetime.strftime('%Y%m%d')
    hh = init_datetime.strftime('%H')
    aws_bucket = 'noaa-gestofs-pds'
    subdir = f'stofs_2d_glo.{yyyymmdd}'
    filename = f'stofs_2d_glo.t{hh}z.fields.cwl.nc'
    s3 = s3fs.S3FileSystem(anon=True)  # Enable anonymous access to the S3 bucket
    url = f's3://{aws_bucket}/{subdir}/{filename}'
    ds = xarray.open_dataset(s3.open(url, 'rb'), drop_variables=['nvel'])
    ds = xarray_subset_grid.grids.ugrid.assign_ugrid_topology(ds, face_node_connectivity="element")

    # Optionally convert to local mean sea level.
    if convert_to_local_msl:
        lmsl_filename = 'noaa-nos-stofs2d-pds/_archive/msl_2017-2019_avg/GSTOFSv5.6.5_msl_2017-2019_avg_20241619.nc'
        ds_lmsl = xarray.open_dataset(
            s3.open(f's3://{lmsl_filename}', 'rb')
        )
        ds['zeta'] = ds['zeta'] - ds_lmsl['mean_sea_level']

    # Subset to box. 
    subset_ds = ds.xsg.subset_polygon(shapely.get_coordinates(bbox)).load()
    return subset_ds


def drop_nan_nodes(ds: xarray.Dataset, 
                   drop_var: str, 
                   max_nan_fraction: float = 0.0) -> xarray.Dataset:
    """Drop nodes from dataset where NaN values occur. 

    Should probably just replace this with:
        ds.dropna('node', how='any', subset=[drop_var])
    """
    # Convert max_nan_fraction to minimum count of non-NaN values.
    min_non_nan_count = min(
        math.ceil((1.0 - max_nan_fraction) * len(ds.time)),
        len(ds.time)
    )
    return ds.dropna('node', thresh=min_non_nan_count, subset=[drop_var])


def get_nearest_inds_dists(
    ds_mesh: xarray.Dataset, 
    df_stations: pandas.DataFrame,
    n_nearest: int = 10,
    ds_x_var: str = 'x', 
    ds_y_var: str = 'y',
    df_x_var:str = 'longitude', 
    df_y_var: str = 'latitude'
) -> (xarray.DataArray, xarray.DataArray):
    """Get indices and distances to nearest points in dataset.

    If the "station" data frame only has 1 station, might need to use
        df_stations.loc[0].to_frame().transpose()
    or
        df_stations.loc[0:0]
    to get the right format.
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
        dists  = np.expand_dims(dists, axis=1)
        inds  = np.expand_dims(inds, axis=1)
    return xarray.DataArray(inds, dims=["station", "k"]), \
        xarray.DataArray(dists, dims=["station", "k"])
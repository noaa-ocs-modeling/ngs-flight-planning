"""Functions for handling STOFS forecast mesh files.
"""


import shapely
import geopandas as gpd
import datetime
import xarray
import pandas
import numpy
import scipy
import s3fs
import thalassa
import math
from coastalmodeling_vdatum import vdatum

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
        
    # Subset to box. 
    subset_ds = thalassa.crop(thalassa.normalize(ds), bbox)  #.load()

    # Optionally convert to local mean sea level.
    if convert_to_local_msl:
        lmsl_filename = 'noaa-nos-stofs2d-pds/_archive/msl_2017-2019_avg/GSTOFSv5.6.5_msl_2017-2019_avg_20241619.nc'
        ds_lmsl = xarray.open_dataset(
            s3.open(f's3://{lmsl_filename}', 'rb')
        )
        subset_ds_lmsl = thalassa.crop(thalassa.normalize(ds_lmsl), bbox)  #.load()
        subset_ds['zeta'] = subset_ds['zeta'] - subset_ds_lmsl['mean_sea_level']
        
    return subset_ds


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
    """
    ds_out = ds.copy()
    if 'mlw_minus_lmsl' not in ds.data_vars:
        ds_out = ds_add_datum(ds, 'mlw', incl_time_axis=incl_time_axis, 
                              ds_y_name=ds_y_name, ds_x_name=ds_x_name)
    if 'mhw_minus_lmsl' not in ds.data_vars:
        ds_out = ds_add_datum(ds_out, 'mhw', incl_time_axis=incl_time_axis, 
                              ds_y_name=ds_y_name, ds_x_name=ds_x_name)
    ds_out['mean_range'] = ds_out['mhw_minus_lmsl'] - ds_out['mlw_minus_lmsl']
    return ds_out


def tidal_tol_from_range(ds: xarray.Dataset,
                         range_var: str = 'mean_range') -> xarray.Dataset:
    """
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
    
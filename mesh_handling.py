"""Contains functions for handling STOFS forecast mesh files.
"""


import shapely
import geopandas as gpd
import datetime
import xarray
import xarray_subset_grid
import s3fs
import thalassa


def get_box(geometries: gpd.GeoDataFrame, 
            buffer: float = 0.1) -> shapely.box:
    """Get a buffered box around geometries in a geopandas data frame.
    """
    tb = geometries.total_bounds
    bbox = shapely.box(tb[0] - buffer, tb[1] - buffer,
                       tb[2] + buffer, tb[3] + buffer)
    return bbox


def load_forecast_ds(init_datetime: datetime.datetime, 
                     bbox: shapely.box) -> xarray.Dataset:
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
    url = f"s3://{aws_bucket}/{subdir}/{filename}"
    ds = xarray.open_dataset(s3.open(url, 'rb'), drop_variables=['nvel'])

    # Subset to box. 
    subset_ds = thalassa.crop(thalassa.normalize(ds), bbox).load()
    return subset_ds


def load_forecast_ds_xsg(init_datetime: datetime.datetime, 
                         bbox: shapely.box) -> xarray.Dataset:
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
    url = f"s3://{aws_bucket}/{subdir}/{filename}"
    ds = xarray.open_dataset(s3.open(url, 'rb'), drop_variables=['nvel'])
    ds = xarray_subset_grid.grids.ugrid.assign_ugrid_topology(ds, face_node_connectivity="element")

    # Subset to box. 
    subset_ds = ds.xsg.subset_polygon(shapely.get_coordinates(bbox)).load()
    return subset_ds
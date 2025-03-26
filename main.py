import geopandas as gpd
import pandas as pd
import numpy as np
import xarray as xr
import datetime
import shapely
#
from inputs import load_lines_gdf
from processing import point_table_from_lines
import mesh_handling

# Define inputs.
lines_txt = 'data/AL2401.wpt'
init_datetime = datetime.datetime(2024,12,15,0,0)

# Read flight paths and calculate image points. 
df_lines = load_lines_gdf(lines_txt)
df_points = point_table_from_lines(df_lines)

# Load and subset forecast data.
bbox = mesh_handling.get_box(df_lines)
ds_thal = mesh_handling.load_forecast_ds(init_datetime, bbox, convert_to_local_msl=True)
ds_drop = mesh_handling.drop_nan_nodes(ds_thal, 'zeta')['zeta']
inds, dists = mesh_handling.get_nearest_inds_dists(
    ds_drop,
    df_points,
    n_nearest=1,
    ds_x_var='lon', 
    ds_y_var='lat',
    df_x_var='LON',
    df_y_var='LAT'
)
ds_points_model_timeseries = ds_drop.sel(node=inds).isel(k=0)


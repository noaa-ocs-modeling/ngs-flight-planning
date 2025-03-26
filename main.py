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
datums = ['mllw', 'mhw']

# Read flight paths and calculate image points. 
df_lines = load_lines_gdf(lines_txt)
df_points = point_table_from_lines(df_lines)

# Load and subset forecast data.
bbox = mesh_handling.get_box(df_lines)
ds_thal = mesh_handling.load_forecast_ds(init_datetime, bbox, convert_to_local_msl=True)
ds_thal = mesh_handling.ds_add_datum(ds_thal, 'mllw') # Add additional datums when ready.
ds_drop = ds_thal.dropna('node', how='any', subset=['lmsl_minus_mllw', 'zeta'])
ds_drop_zeta = ds_thal.dropna('node', how='any', subset=['zeta'])
print(f'Number of nodes: full subset {len(ds_thal.node)}; NaN in zeta {len(ds_drop_zeta.node)}; NaN in zeta or datum {len(ds_drop.node)}.')
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

# Gather datum info
#     ds_add_tidal_range(...)
# Needs additional functionality from Felicio's vdatum.
# Tolerance for each location, from range
# (Datum(s) +/- tolerance) for each location

# Process station timeseries.
# Interpolate to 1-minute
#    interp_time(...)
# Get sun angle for each
#    calc_sun_alt(...)
# Test whether in tidal range and sun angle conditions
#    ds_in_range = (() & () & () ...) too specific for function
# Aggregate boolean to windows
#    windows_from_bool(...)

# Overlap point-windows within each line. 

# Outputs


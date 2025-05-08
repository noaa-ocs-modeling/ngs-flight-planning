import geopandas as gpd
import pandas as pd
import numpy as np
import xarray as xr
import datetime
import shapely
import pvlib
#
import inputs 
import processing  
import mesh_handling
from timer import SimpleTimer

# Define inputs.
lines_txt = 'data/AL2401.wpt'
project_name = 'AL2401_test'
init_datetime = datetime.datetime(2024,12,15,0,0)
datums = ['mllw', 'mhw']

timer = SimpleTimer()

# Read flight paths and calculate image points. 
print('Reading flight lines and calculating image positions...')
df_lines = inputs.load_lines_gdf(lines_txt)
df_points = processing.point_table_from_lines(df_lines)
timer.update_print()

# Load and subset forecast and datum data.
bbox = mesh_handling.get_box(df_lines)

print('Loading forecast subset...')
ds_mesh = mesh_handling.load_forecast_ds(init_datetime, bbox, convert_to_local_msl=True)
print('Total time to load forecast data:')
timer.update_print()

print('Adding datums...')
# We want all in `datums`, plus MLW and MHW to calculate range.
for datum in list(set(datums + ['mhw', 'mlw'])):
    ds_mesh = mesh_handling.ds_add_datum(ds_mesh, datum)
timer.update_print()

print('Dropping NaN data...')
# For window calculations, we need a time series with no missing data,
# and valid datum values, so we exclude model points that don't meet 
# that criterium.
ds_drop = ds_mesh.dropna('node', how='any', subset=['mllw_minus_lmsl', 'zeta'])
ds_drop_zeta = ds_mesh.dropna('node', how='any', subset=['zeta'])
print(f'Number of nodes: full subset {len(ds_mesh.node)}; NaN in zeta {len(ds_drop_zeta.node)}; NaN in zeta or datum {len(ds_drop.node)}.')
timer.update_print()

print('Calculating nearest nodes to image positions...')
# Using only model nodes with no missing data, as 
# described above. 
inds, dists = mesh_handling.get_nearest_inds_dists(
    ds_drop,
    df_points,
    n_nearest=1,
    ds_x_var='lon', 
    ds_y_var='lat',
    df_x_var='LON',
    df_y_var='LAT'
)
timer.update_print()

print('Subsetting to nearest nodes...')
# Note that the lat and lon values in this dataset 
# are now the model node locations, not the image 
# point locations. 
ds_points_model_timeseries = ds_drop.sel(node=inds).isel(k=0)
timer.update_print()

print('Calculating tidal range and tolerance...')
# Range = MHW - MLW.
# Tolerance based on 2014 NGS/RSD memo.
ds_points_model_timeseries = mesh_handling.ds_add_tidal_range(
    ds_points_model_timeseries
)
ds_points_model_timeseries = mesh_handling.tidal_tol_from_range(
    ds_points_model_timeseries
)
timer.update_print()

print('Interpolating along time axis...')
ds_interp = processing.interp_time(ds_points_model_timeseries)
timer.update_print()

print('Converting to pandas data frame...')
# Renames the model node lat and lon columns, both for clarity
# and to avoid conflicts when joining with the image location
# lat and lon.
df_interp = ds_interp[[v for v in ds_interp.data_vars if 'station' in ds_interp[v].dims]]\
            .to_dataframe(dim_order=['station', 'time'])\
            .rename(columns={'lat':'node_lat', 'lon':'node_lon'})
timer.update_print()

print('Calculating solar elevation angles...')
df_interp = processing.calc_sun_alt(df_interp)
timer.update_print()

print('Calculating times when water level in range...')
df_interp = processing.calc_in_range(df_interp, datums)
timer.update_print()

print('Calculating windows by point...')
df_point_windows = processing.point_windows_from_bool(df_interp, datums)

# Add line column and reorder.
df_point_windows = df_point_windows.join(df_points.LINE, on='station')\
                                   .rename(columns={'LINE':'line'})
df_point_windows = df_point_windows[['station', 'node_lat', 'node_lon', 
                                     'line', 'datum',
                                     'start_time', 'end_time']]
timer.update_print()

print('Calculating windows by line...')
# This is actually done by going back to the boolean time series,
# rather than calculating line windows from point windows.
df_line_windows = processing.line_windows_from_bool(df_interp, df_points, datums)
timer.update_print()

print('Writing outputs...')
outputs.output_all_prediction(df_lines, df_line_windows, 
                              df_points, df_point_windows, 
                              project_name, datums, init_datetime)


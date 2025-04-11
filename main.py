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
ds_mesh = mesh_handling.ds_add_datum(ds_mesh, 'mllw')
ds_mesh = mesh_handling.ds_add_datum(ds_mesh, 'mlw')
ds_mesh = mesh_handling.ds_add_datum(ds_mesh, 'mhw')
timer.update_print()

print('Dropping NaN data...')
ds_drop = ds_mesh.dropna('node', how='any', subset=['mllw_minus_lmsl', 'zeta'])
ds_drop_zeta = ds_mesh.dropna('node', how='any', subset=['zeta'])
print(f'Number of nodes: full subset {len(ds_mesh.node)}; NaN in zeta {len(ds_drop_zeta.node)}; NaN in zeta or datum {len(ds_drop.node)}.')
timer.update_print()

print('Calculating nearest nodes to image positions...')
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
ds_points_model_timeseries = ds_drop.sel(node=inds).isel(k=0)
timer.update_print()

# Calculate tidal range and tolerance.
print('Calculating tidal range and tolerance...')
ds_points_model_timeseries = mesh_handling.ds_add_tidal_range(
    ds_points_model_timeseries
)
ds_points_model_timeseries = mesh_handling.tidal_tol_from_range(
    ds_points_model_timeseries
)
timer.update_print()

# Process station timeseries.
print('Interpolating along time axis...')
ds_interp = processing.interp_time(ds_points_model_timeseries)
timer.update_print()

# Convert to pandas data frame.
print('Converting to pandas data frame...')
df_interp = ds_interp[[v for v in ds_interp.data_vars if 'station' in ds_interp[v].dims]]\
            .to_dataframe(dim_order=['station', 'time'])
timer.update_print()

# Get sun angle for each row of data frame.
print('Calculating solar elevation angles...')
df_interp = processing.calc_sun_alt(df_interp)
timer.update_print()

# Test whether in tidal range and sun angle conditions
print('Calculating times when water level in range...')
df_interp = processing.calc_in_range(df_interp, datums)
timer.update_print()

# Aggregate boolean to windows by point.
print('Calculating windows by point...')
df_point_windows = processing.point_windows_from_bool(df_interp, datums)

# Add line column and reorder.
df_point_windows = df_point_windows.join(df_points.LINE, on='station')\
                                   .rename(columns={'LINE':'line'})
df_point_windows = df_point_windows[['station', 'lat', 'lon', 'line', 'datum',
                                     'start_time', 'end_time']]
timer.update_print()

# Overlap point-windows within each line.
# Done by calculating windows from boolean time series.
print('Calculating windows by line...')
df_line_windows = processing.line_windows_from_bool(df_interp, df_points, datums)
timer.update_print()

# Outputs


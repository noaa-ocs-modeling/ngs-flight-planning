import geopandas as gpd
import pandas as pd
import numpy as np
import xarray as xr
import datetime
import shapely
import pvlib
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

# Load and subset forecast and datum data.
bbox = mesh_handling.get_box(df_lines)
print('Loading forecast subset...\n')
ds_thal = mesh_handling.load_forecast_ds(init_datetime, bbox, convert_to_local_msl=True)
print('Finished loading forecast subset.\n')
ds_thal = mesh_handling.ds_add_datum(ds_thal, 'mllw')
ds_thal = mesh_handling.ds_add_datum(ds_thal, 'mlw')
ds_thal = mesh_handling.ds_add_datum(ds_thal, 'mhw')
ds_drop = ds_thal.dropna('node', how='any', subset=['mllw_minus_lmsl', 'zeta'])
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

# Calculate tidal range and tolerance.
ds_points_model_timeseries = mesh_handling.ds_add_tidal_range(
    ds_points_model_timeseries
)
ds_points_model_timeseries = mesh_handling.tidal_tol_from_range(
    ds_points_model_timeseries
)

# Process station timeseries.
ds_interp = processing.interp_time(ds_points_model_timeseries)

# Convert to pandas data frame.
df_interp = ds_interp[[v for v in ds_interp.data_vars if 'station' in ds_interp[v].dims]]\
            .to_dataframe(dim_order=['station', 'time'])

# Get sun angle for each row of data frame.
df_interp = processing.calc_sun_alt(df_interp)

# Test whether in tidal range and sun angle conditions
#    ds_in_range = (() & () & () ...) too specific for function
for dat in datums:
    df_interp[dat + '_in_range'] = (
        (df_interp['zeta'] >= df_interp[dat + '_minus_lmsl'] - df_interp['tolerance']) 
        & 
        (df_interp['zeta'] <= df_interp[dat + '_minus_lmsl'] + df_interp['tolerance'])
        &
        (df_interp['solar_elevation'] >= 25.0)
    )

# Aggregate boolean to windows
#    windows_from_bool(...)

# Overlap point-windows within each line. 

# Outputs


"""Tests speed of subset loading functions.

Results for a single forecast file for box
array([[-87.63242486,  30.14828831],
       [-87.63242486,  31.00258547],
       [-88.42893096,  31.00258547],
       [-88.42893096,  30.14828831],
       [-87.63242486,  30.14828831]]):
       
    Time for xrray_subset_grid method: 0:15:10.095264 (H:M:S) 
    Time for thalassa method: 0:12:10.918310 (H:M:S)

Note that the resulting subsets are not the same:
xsg version has 58315 nodes;
thalassa version has 57946 nodes.
"""


import mesh_handling
import datetime
import geopandas as gpd


flightpath_filename = 'data/AL2401L-wpt.shp'
flight_paths = gpd.read_file(flightpath_filename)
bbox = mesh_handling.get_box(flight_paths)

t3 = datetime.datetime.now()
ds_xsg = mesh_handling.load_forecast_ds_xsg(datetime.datetime(2024,12,15,6,0), bbox)
t4 = datetime.datetime.now()
print(f'Time for xrray_subset_grid method: {t4 - t3}')

t1 = datetime.datetime.now()
ds_thal = mesh_handling.load_forecast_ds(datetime.datetime(2024,12,15,0,0), bbox)
t2 = datetime.datetime.now()
print(f'Time for thalassa method: {t2 - t1}')

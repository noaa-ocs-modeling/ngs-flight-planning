import geopandas as gpd
from inputs import load_lines_gdf
from processing import point_table_from_lines
import pandas as pd
import numpy as np
import shapely

lines_txt = 'data/AL2401.wpt'
imagepoints_filename = 'data/AL2401c-wpt.shp'
lines_filename = 'data/AL2401L-wpt.shp'
flight_image_points = gpd.read_file(imagepoints_filename)

df_lines = load_lines_gdf(lines_txt)
df_points = point_table_from_lines(df_lines)

# Calculate distances between provided and calculated image points.
dists = pd.Series([shapely.distance(df_points.loc[i, 'geometry'], 
                                    flight_image_points.loc[i, 'geometry']) 
                   for i in df_points.index])

deg_to_m_upper_limit = 60.0 * 1852.0

print('Upper bounds of location errors:')
print(f'    Maximum distance: {float(dists.max() * deg_to_m_upper_limit):.2f} m')
print(f'    Minimum distance: {float(dists.min() * deg_to_m_upper_limit):.2f} m')
print(f'    Mean distance: {float(dists.mean() * deg_to_m_upper_limit):.2f} m')
print('(Note these calculations use simple degrees-to-meters conversion, so are upper bounds of actual distances.)')


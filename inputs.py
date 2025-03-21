"""
"""


import geopandas as gpd
import pandas as pd
import shapely
import sys
from utils import hdms_to_dd


def load_lines_gdf(filepath: str) -> gpd.GeoDataFrame:
    """
    """
    df = pd.read_csv(filepath)
    gdf = gpd.GeoDataFrame(
        df, 
        geometry=[shapely.LineString([[hdms_2_dd(df.loc[i,'LON1']), 
                                       hdms_2_dd(df.loc[i,'LAT1'])], 
                                      [hdms_2_dd(df.loc[i,'LON2']), 
                                       hdms_2_dd(df.loc[i,'LAT2'])]]) 
                  for i in range(len(df.index))]
    )
    return gdf
"""Functions for reading NGS flight planning input files.

Functions
---------
load_lines_gdf(filepath: str) -> gpd.GeoDataFrame

"""


import geopandas as gpd
import pandas as pd
import shapely
import sys
from utils import hdms_to_dd


def load_lines_gdf(filepath: str) -> gpd.GeoDataFrame:
    """Read a flight lines file and return data as GeoDataFrame.

    Parameters
    ----------
    filepath
        The full path to the file containing flight lines,
        usually a "wpt" or waypoint file, which is a form 
        of human-readable CSV.

    Returns
    -------
    Geopandas data frame
        With one row per flight line.
        
    """
    df = pd.read_csv(filepath)
    gdf = gpd.GeoDataFrame(
        df, 
        geometry=[shapely.LineString([[hdms_to_dd(df.loc[i,'LON1']), 
                                       hdms_to_dd(df.loc[i,'LAT1'])], 
                                      [hdms_to_dd(df.loc[i,'LON2']), 
                                       hdms_to_dd(df.loc[i,'LAT2'])]]) 
                  for i in range(len(df.index))]
    )
    return gdf
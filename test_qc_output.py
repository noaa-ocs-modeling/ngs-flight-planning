"""Script to compare QC output files with samples provided.

Usage: python test_qc_output.py <file_extension> <qc_type>
Where <file_extension> is the file extension (e.g., 'geojson',
'shp') and <qc_type> is either '2'/'field' or '3'/'final'.

Example: python test_qc_output.py geojson field

The file locations and names are hardcoded within the script.
They could be modified as needed by editing the variables at 
the top of the script (dir_ref_2, file_root_ref_2, etc.).
"""


import sys
import geopandas as gpd


dir_ref_2 = 'data/output_files-20250321T164959Z-001/02_QC_Field_out'
file_root_ref_2 = 'ImageEvents_C147643_1217241559565_003_RGB1_mhw_mllw_qc'
dir_ref_3 = 'data/output_files-20250321T164959Z-001/03_QC_Final_out'
file_root_ref_3 = 'AL2401_1217241559565_mhw_mllw'

dir_new_2 = 'data/testing/AL2401_qc'
dir_new_3 = 'data/testing/AL2401_qc_final'
file_root_new_2 = 'AL2401_qc_mllw_mhw_20241217T12_qc'
file_root_new_3 = 'AL2401_qc_final_mllw_mhw_20241217T12_qc'

def get_ref_file(file_ext, qc_type):
    if qc_type == '2' or qc_type == 'field':
        dir_ref = dir_ref_2
        file_root_ref = file_root_ref_2
    elif qc_type == '3' or qc_type == 'final':
        dir_ref = dir_ref_3
        file_root_ref = file_root_ref_3
    else:
        raise ValueError("qc_type must be '2'/'field' or '3'/'final'")
    return gpd.read_file(f"{dir_ref}/{file_root_ref}.{file_ext}")

def get_new_file(file_ext, qc_type):
    if qc_type == '2' or qc_type == 'field':
        dir_new = dir_new_2
        file_root_new = file_root_new_2
    elif qc_type == '3' or qc_type == 'final':
        dir_new = dir_new_3
        file_root_new = file_root_new_3
    else:
        raise ValueError("qc_type must be '2'/'field' or '3'/'final'")
    return gpd.read_file(f"{dir_new}/{file_root_new}.{file_ext}")

if __name__ == "__main__":
    file_ext = sys.argv[1]
    qc_type = sys.argv[2] 
    df_old = get_ref_file(file_ext, qc_type)
    df_new = get_new_file(file_ext, qc_type)
    if df_new.shape != df_old.shape: 
        print(f"Shape mismatch: {df_new.shape} vs {df_old.shape}")
    for col in df_old.columns:
        if col not in df_new.columns:
            print(f"Column {col} missing in new data")
        if df_new[col].dtype != df_old[col].dtype:
            print(f"Type mismatch in column {col}: {df_new[col].dtype} vs {df_old[col].dtype}")
    for col in df_new.columns:
        if col not in df_old.columns:
            print(f"Column {col} has no equivalent in old data")
    for col in df_old.columns:
        print(str(df_new[col].iloc[0]) + 
              '     vs.     ' + 
              str(df_old[col].iloc[0]))
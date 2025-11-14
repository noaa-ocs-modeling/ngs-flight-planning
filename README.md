Calculate water levels to support NGS flight planning.

# Installation
This package has been developed using `python` 3.12, and tested with `python` 3.12 and 3.11. If you don't have one of these, you can use `conda` or `mamba` to set up a `python` 3.12 environment with the following steps:
```
# Install miniconda if needed:
wget "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-$(uname)-$(uname -m).sh"
bash "Miniforge3-$(uname)-$(uname -m).sh" -b -p "${HOME}/conda"
source "${HOME}/conda/etc/profile.d/conda.sh"
source "${HOME}/conda/etc/profile.d/mamba.sh"

# Set up a python 3.12 env:
mamba create --name=py312 python=3.12
mamba activate py312
# Replace the "2"s with "1"s if you want python 3.11!
```

Get the package code by cloning from github:
```
git clone git@github.com:noaa-ocs-modeling/ngs-flight-planning.git
```

Then, to set up the minimal environment to run the main scripts in the package, follow the "Standard" instructions below. To use the accompanying Jupyter notebook(s), or to use the exact environment used in development, follow the "Development & Jupyter notebooks" instructions.

## Standard
```
cd ngs-flight-planning
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Development & Jupyter notebooks
```
cd ngs-flight-planning
python -m venv .venv
source .venv/bin/activate
pip install -r dev_requirements.txt
```

# Usage
Eventually, the aim is to use the package for long-term (months ahead) flight planning, near-term (days ahead) flight planning, and post flight QC (preliminary and final). For now, only the near-term flight planning has been implemeted. This is run using a python command line script. The process should output the same types of files as the existing TCARI method. 

## Flight planning
Run the script `predict.py`, with three required command line arguments:
```
python predict.py <project_name> <path_to_flight_lines>.wpt <STOFS_forecast_initialization>
```
replacing the parts in angle brackets `<...>` with actual values. More detailed descriptions of these arguments, as well as a number of additional, optional command line arguments, can be accessed by running
```
python predict.py -h
```
An example command might look like:
```
python predict.py AL2401 data/AL2401.wpt 2025-01-01T12:00 -o data/testing -l DEBUG
```
If this executes successfully, the following output files should be saved in `./data/testing/AL2401/`:
```
AL2401_mllw_mhw_20250101T12.dates.txt      AL2401_mllw_mhw_20250101T12.lines.shp  AL2401_mllw_mhw_20250101T12.pts.geojson
AL2401_mllw_mhw_20250101T12.gpkg           AL2401_mllw_mhw_20250101T12.lines.shx  AL2401_mllw_mhw_20250101T12.pts.shp
AL2401_mllw_mhw_20250101T12.lines.cpg      AL2401_mllw_mhw_20250101T12.lines.txt  AL2401_mllw_mhw_20250101T12.pts.shx
AL2401_mllw_mhw_20250101T12.lines.dbf      AL2401_mllw_mhw_20250101T12.pts.cpg
AL2401_mllw_mhw_20250101T12.lines.geojson  AL2401_mllw_mhw_20250101T12.pts.dbf
```

## QC
Run the script `qc.py`, with two required command line arguments:
```
python qc.py <project_name> <path_to_images_file>.csv <STOFS_forecast_initialization>
```
replacing the parts in angle brackets `<...>` with actual values. More detailed descriptions of these arguments, as well as a number of additional, optional command line arguments, can be accessed by running
```
python qc.py -h
```
The most commonly used optional command line arguments might be `-q`, with value `field` or `final`, to select which stage of QC is being run, and `-d` to list datums to analyze. These default to `field` and ['mllw', 'mhw'], respectively.

An example command might look like:
```
python qc.py \
    AL2401_qc \
    data/ImageEvents_C147643_1217241559565_003_RGB1.csv \
    -o data/testing \
    -l DEBUG
```
If this executes successfully, the following output files should be saved in `./data/testing/AL2401_qc/`:
```
AL2401_qc_mllw_mhw_20241217T12_qc.html
AL2401_qc_mllw_mhw_20241217T12_qc.geojson
AL2401_qc_mllw_mhw_20241217T12_qc.csv
AL2401_qc_mllw_mhw_20241217T12_qc.gpkg
AL2401_qc_mllw_mhw_20241217T12_qc.shp
AL2401_qc_mllw_mhw_20241217T12_qc.cpg
AL2401_qc_mllw_mhw_20241217T12_qc.shx
AL2401_qc_mllw_mhw_20241217T12_qc.dbf
```
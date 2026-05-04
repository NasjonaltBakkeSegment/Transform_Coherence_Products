# Transform Coherence Products

Tools to convert SAR coherence and backscatter GeoTIFFs into a single CF‑friendly NetCDF file, using attributes from configuration YAML files.

## Repository layout

- `config/`
  - `global_attributes.yaml` – global NetCDF attributes
  - `variable_attributes.yaml` – per‑variable and coordinate attributes (`VV_coherence`, `VV_gamma_nought`, `VV_sigma_nought`, `VH_gamma_nought`, `VH_sigma_nought`, `x`, `y`, etc.)
- `src/coherence_to_netcdf/`
  - `io.py`      – YAML/config loading helpers
  - `coords.py`  – coordinate generation from raster transforms
  - `crs.py`     – CRS → CF grid_mapping attribute logic
  - `dataset.py` – core logic to build the `xarray.Dataset`
  - `cli.py`     – simple command‑line interface
- `build_netcdf.py` – small driver script to run the conversion
- `combined_data.nc` – example output NetCDF (created by the script)

## Running

From the repository root:

```bash
python build_netcdf.py
```

By default this will:

- read input GeoTIFFs from the base directory configured inside `build_dataset` (in `src/coherence_to_netcdf/dataset.py`),
- read variable and global attributes from the YAML files in `config/`,
- write `combined_data.nc` in the repository root.

You can change the input base directory or output filename by editing `build_netcdf.py` or the `main()` function in `src/coherence_to_netcdf/cli.py`.

A more realistic example with explicit arguments (if you wire them through `cli.py`) might look like:

```bash
python build_netcdf.py \
  --base-dir coherence_products/dsc/081/W01N67/20250820/ \
  --output outputs/W01N67_081_20250820.nc
```

Here:

- `--base-dir` points to the directory containing the input GeoTIFFs,
- `--output` sets the path of the NetCDF file to create.
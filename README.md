# Transform Coherence Products

Tools to process incoming SAR coherence/backscatter GeoTIFFs through a pipeline:

1. **NetCDF creation** – Convert GeoTIFFs to CF-compliant NetCDF (always created unless skipped)
2. **MMD generation** – Create and enrich MMD XML metadata (optional, controlled by `--create-mmd` flag)

## Quick Start

```bash
# Create NetCDF only (default)
python process.py --base-dir coherence_products/dsc/081/W01N67/20250820/

# Create NetCDF + MMD
python process.py --base-dir <path> --create-mmd

# Force recreation (even if files exist)
python process.py --base-dir <path> --create-mmd --overwrite
```

## Repository Layout

```
transform_coherence_products/
├── config/                          # Configuration files
│   ├── global_attributes.yaml       # NetCDF global attributes
│   ├── variable_attributes.yaml     # Per-variable coordinate attributes
│   ├── mmd_update.yaml              # MMD metadata update rules
│   └── paths.yaml                   # External paths (mdharvest)
├── src/                             # Source code
│   ├── coherence_to_netcdf/         # NetCDF building module
│   │   ├── cli.py
│   │   ├── dataset.py
│   │   ├── coords.py
│   │   ├── crs.py
│   │   └── io.py
│   └── mmd/                         # MMD metadata module
│       ├── __init__.py
│       └── mmd_updater.py
├── scripts/                         # Internal implementation (used by process.py)
│   ├── build_netcdf.py
│   ├── create_mmd.py
│   └── run_pipeline.py
├── coherence_products/              # Input data directory
├── netcdf_output/                   # NetCDF output (auto-created)
├── mmd_output/                      # MMD output (auto-created)
├── process.py                       # ⭐ MAIN PRODUCTION ENTRY POINT
├── requirements.txt
└── README.md
```

## Configuration

### External Paths (`config/paths.yaml`)
```yaml
mdharvest:
  src_path: /path/to/mdharvest/src
```

### MMD Metadata Updates (`config/mmd_update.yaml`)
```yaml
mmd_update:
  dataset_production_status: Complete
  project_short_name: NBS
  use_constraint_license_text: <license URL>
  data_center:
    short_name: METNO
    long_name: Norwegian Meteorological Institute
    data_center_url: https://met.no
  sentinel1:
    product_type: SAR-IW-L2-OCN
    instrument_short_name: SAR-C
    instrument_long_name: Synthetic Aperture Radar (C-band)
    instrument_resource: https://www.wmo-sat.info/oscar/instruments/view/sar_c_sentinel_1
  sios:
    enabled: true
    north_threshold: 70.0
```

**Note:** Sentinel-1 platform metadata is derived from the NetCDF global attributes populated during the GeoTIFF conversion step.

## Usage

### Default Behavior: NetCDF Only

```bash
python process.py --base-dir coherence_products/dsc/081/W01N67/20250820/
```

- ✓ Creates `netcdf_output/<title>.nc` if it doesn't exist
- ✓ Skips if file already exists (use `--overwrite` to force)

### With MMD Creation

```bash
python process.py --base-dir <path> --create-mmd
```

- ✓ Creates NetCDF (if needed)
- ✓ Creates MMD with all metadata enhancements
- ✓ Skips if files exist (use `--overwrite` to force)

### Custom Output Paths

```bash
python process.py --base-dir <path> \
                  --netcdf-output netcdf_output/custom.nc \
                  --mmd-output mmd_output/custom.xml \
                  --create-mmd
```

### Verbose Mode

```bash
python process.py --base-dir <path> --create-mmd --verbose
```

Shows which steps are skipped vs. executed.

## Command-Line Options

```
--base-dir DIR              Input directory with GeoTIFFs
                           (default: coherence_products/dsc/081/W01N67/20250820/)

--netcdf-output PATH       NetCDF output path
                           (default: netcdf_output/<derived_name>.nc)

--mmd-output PATH          MMD output path
                           (default: mmd_output/<derived_name>.xml)

--create-mmd               Enable MMD creation (default: disabled)

--overwrite                Force recreation even if output exists

--verbose                  Enable verbose logging
```

## Exit Codes

- `0` – Success (files created or already exist)
- `1` – Error (invalid input, missing required options, processing failed)
- `2` – Skipped (output exists and `--overwrite` not specified)

## Production Workflow

### 1. Initial Setup
```bash
# Copy/configure your input data
cp -r /data/coherence_products coherence_products/

# Edit config files
nano config/paths.yaml          # Set mdharvest path
nano config/mmd_update.yaml     # Customize metadata
```

### 2. Single Product Run
```bash
python process.py --base-dir coherence_products/path/to/product/ \
                  --create-mmd
```

### 3. Batch Processing
```bash
#!/bin/bash
for product_dir in coherence_products/dsc/081/*/20250820/; do
    python process.py --base-dir "$product_dir" \
            --create-mmd \
                      --verbose
    if [ $? -ne 0 ]; then
        echo "Failed: $product_dir"
        exit 1
    fi
done
```

### 4. Re-process with Updated Config
```bash
# Update config then force recreation
python process.py --base-dir <path> --create-mmd --overwrite
```

## Design Principles

- **Single entry point** – `process.py` is the canonical interface
- **Intelligent caching** – Skips processing if outputs exist
- **Configurable** – YAML files control behavior
- **Production-ready** – Exit codes, verbose logging, error handling
- **Modular** – NetCDF and MMD can run independently or chained

This creates the MMD using `mdharvest` and then applies your project-specific updates.

### Notes on configuration

- External `mdharvest` location: `config/paths.yaml`
- MMD update settings (license, project/data center, SIOS rule, Sentinel-1 instrument metadata): `config/mmd_update.yaml`
- Sentinel-1 platforms in the MMD are derived from the NetCDF global attributes `earlier_acquisition_platform_name` and `later_acquisition_platform_name`.
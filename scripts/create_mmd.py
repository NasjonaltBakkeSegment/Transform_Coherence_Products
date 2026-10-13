#!/usr/bin/env python3
"""
Create and update MMD from coherence NetCDF.

Usage:
    python scripts/create_mmd.py --input-file netcdf_output/product.nc --output-path mmd_output/
"""
import sys
import os
import argparse
import importlib
from pathlib import Path
import yaml
import xarray as xr

# Add parent directory to path for imports
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))

BASE_DIR = str(repo_root)  # Repository root


def load_yaml(path):
    """Load and parse a YAML configuration file."""
    with open(path, 'r') as handle:
        return yaml.safe_load(handle)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description='Create and update MMD from coherence NetCDF.')
    parser.add_argument(
        '--input-file',
        default='W01N67_track_081_20250814-20250820_coherence.nc',
        help='Input NetCDF file path.',
    )
    parser.add_argument(
        '--output-path',
        default='./mmd_output/',
        help='Output directory for generated MMD.',
    )
    return parser.parse_args(argv)


# Load configuration files
paths_config = load_yaml(os.path.join(BASE_DIR, 'config', 'paths.yaml'))
update_config = load_yaml(os.path.join(BASE_DIR, 'config', 'mmd_update.yaml'))

# Add project src to path
project_src = os.path.join(BASE_DIR, 'src')
sys.path.insert(0, project_src)

# Add mdharvest/src to path from config
mdharvest_src = paths_config['mdharvest']['src_path']
sys.path.insert(0, mdharvest_src)

# Import the MMD updater from new location
from mmd.mmd_updater import MMDUpdater


def load_mdharvest_dependencies():
    """Import mdharvest conversion dependencies lazily."""
    nc_to_mmd_main = importlib.import_module('mdh_modules.nc_to_mmd').main
    importlib.import_module('vocab.ControlledVocabulary')
    importlib.import_module('vocab.CFGCMD')
    importlib.import_module('vocab.KEYWORDS')
    vocab = importlib.import_module('vocab')

    return nc_to_mmd_main, vocab


def process_coherence_product(input_file, output_path):
    """
    Convert a coherence NetCDF product to MMD format.
    
    Args:
        input_file (str): Path to the input NetCDF file
        output_path (str): Path where MMD output should be written
    """
    nc_to_mmd_main, vocab = load_mdharvest_dependencies()
    nc_to_mmd_main(
        input_file=input_file,
        output_path=output_path,
        vocabulary=vocab,
        parse_services=False,
        parse_wmslayers=False,
        print_file=True
    )


def derive_platforms_from_netcdf(input_file):
    """Read unique Sentinel-1 platform codes from NetCDF global attributes."""
    platform_name_to_code = {
        'Sentinel-1A': 'S1A',
        'Sentinel-1B': 'S1B',
        'Sentinel-1C': 'S1C',
        'Sentinel-1D': 'S1D',
    }

    with xr.open_dataset(input_file) as ds:
        platform_names = [
            ds.attrs.get('earlier_acquisition_platform_name'),
            ds.attrs.get('later_acquisition_platform_name'),
        ]

    platforms = []
    for platform_name in platform_names:
        if not platform_name:
            continue

        platform_code = platform_name_to_code.get(platform_name)
        if platform_code is None:
            raise ValueError(
                f"Unsupported Sentinel-1 platform name '{platform_name}' in NetCDF attributes."
            )
        if platform_code not in platforms:
            platforms.append(platform_code)

    if not platforms:
        raise ValueError(
            'Could not derive Sentinel-1 platforms from NetCDF attributes. '
            'Expected earlier_acquisition_platform_name and/or later_acquisition_platform_name.'
        )

    return platforms


def derive_related_datasets_from_netcdf(input_file):
    """Read unique earlier/later acquisition product names from NetCDF global attributes."""
    with xr.open_dataset(input_file) as ds:
        dataset_names = [
            ds.attrs.get('earlier_acquisition_product_name'),
            ds.attrs.get('later_acquisition_product_name'),
        ]

    related_datasets = []
    for dataset_name in dataset_names:
        if not dataset_name:
            continue
        if dataset_name not in related_datasets:
            related_datasets.append(dataset_name)

    return related_datasets


def update_mmd_metadata(mmd_file_path, data_file_path, mmd_cfg):
    """
    Update the generated MMD file with coherence product specific metadata.
    
    This function applies various updates to standardize and enhance the MMD
    metadata for coherence products.
    
    Args:
        mmd_file_path (str): Path to the MMD XML file to update.
        data_file_path (str): Path to the source NetCDF file.
        mmd_cfg (dict): MMD update configuration loaded from YAML.
    """
    updater = MMDUpdater(mmd_file_path)
    sentinel_cfg = mmd_cfg.get('sentinel1', {})
    data_center_cfg = mmd_cfg.get('data_center', {})
    sios_cfg = mmd_cfg.get('sios', {})
    platforms = derive_platforms_from_netcdf(data_file_path)
    related_datasets = derive_related_datasets_from_netcdf(data_file_path)
    parent_uuid = mmd_cfg.get('parent_uuid')

    # Apply updates using method chaining
    (updater
        .update_dataset_production_status(mmd_cfg.get('dataset_production_status', 'Complete'))
        .update_project_short_name(mmd_cfg.get('project_short_name', 'NBS'))
        .upsert_use_constraint_license(mmd_cfg.get('use_constraint_license_text'))
        .upsert_data_center(
            short_name=data_center_cfg.get('short_name', 'METNO'),
            long_name=data_center_cfg.get('long_name', 'Norwegian Meteorological Institute'),
            url=data_center_cfg.get('data_center_url', 'https://met.no'),
        )
        .add_sentinel1_platforms(
            platforms=platforms,
            product_type=sentinel_cfg.get('product_type', 'SAR-IW-L2-OCN'),
            instrument_short_name=sentinel_cfg.get('instrument_short_name', 'SAR-C'),
            instrument_long_name=sentinel_cfg.get('instrument_long_name', 'Synthetic Aperture Radar (C-band)'),
            instrument_resource=sentinel_cfg.get('instrument_resource',
                'https://www.wmo-sat.info/oscar/instruments/view/sar_c_sentinel_1'),
        )
        .add_related_datasets_is_derived_from(related_datasets)
        .add_related_datasets_parent([parent_uuid] if parent_uuid else [])
        .update_storage_information_from_file(data_file_path)
        .ensure_sios_collection_if_north_above(threshold=sios_cfg.get('north_threshold', 70.0))
        .save()
    )
    print(f'Updated MMD file: {mmd_file_path}')


def run_create_mmd(input_file, output_path, mmd_cfg):
    """
    Standalone function for use in pipeline.
    
    Converts NetCDF to MMD and applies all metadata updates.
    Returns the path to the created MMD file.
    
    Args:
        input_file (str): Path to input NetCDF file
        output_path (str): Directory for MMD output
        mmd_cfg (dict): MMD configuration
        
    Returns:
        str: Path to the generated MMD XML file
    """
    process_coherence_product(input_file, output_path)
    
    # Find the generated MMD file (mdharvest creates it with same basename + .xml)
    input_path = Path(input_file)
    mmd_file_path = os.path.join(output_path, f"{input_path.stem}.xml")
    
    update_mmd_metadata(mmd_file_path, input_file, mmd_cfg)
    
    print(f'Final MMD path: {mmd_file_path}')
    return mmd_file_path


def main(argv=None):
    args = parse_args(argv)
    
    run_create_mmd(
        input_file=args.input_file,
        output_path=args.output_path,
        mmd_cfg=update_config.get('mmd_update', {}),
    )


if __name__ == '__main__':
    main()

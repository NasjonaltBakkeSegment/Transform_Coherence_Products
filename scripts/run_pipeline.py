#!/usr/bin/env python3
"""
Full processing pipeline: GeoTIFFs -> NetCDF -> MMD (with updates).

Usage:
    python scripts/run_pipeline.py --base-dir coherence_products/dsc/081/W01N67/20250820/ \
                                    --mmd-output-path mmd_output/
    
    python scripts/run_pipeline.py --base-dir <path> \
                                    --netcdf-output netcdf_output/custom.nc \
                                    --mmd-output-path mmd_output/
"""
import argparse
import sys
import os
from pathlib import Path

# Add parent directory to path
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))

# Import entry points from the reorganized scripts
scripts_dir = str(repo_root / 'scripts')
if scripts_dir not in sys.path:
    sys.path.insert(0, scripts_dir)
    
from build_netcdf import main as build_netcdf_main
from create_mmd import run_create_mmd, update_config


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description='Run full processing pipeline: GeoTIFFs -> NetCDF -> MMD (+ updates).'
    )
    parser.add_argument(
        '--base-dir',
        default='coherence_products/dsc/081/W01N67/20250820/',
        help='Base directory containing input GeoTIFFs for NetCDF creation.',
    )
    parser.add_argument(
        '--netcdf-output',
        default=None,
        help='Optional output NetCDF path. If omitted, file is created in netcdf_output/ '
             'with name derived from dataset title.',
    )
    parser.add_argument(
        '--mmd-output-path',
        default='./mmd_output/',
        help='Directory where MMD XML should be written.',
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    build_args = ['--base-dir', args.base_dir]
    if args.netcdf_output:
        build_args.extend(['--output', args.netcdf_output])

    netcdf_path = build_netcdf_main(build_args)
    print(f'Pipeline step complete: NetCDF at {netcdf_path}')

    mmd_path = run_create_mmd(
        input_file=netcdf_path,
        output_path=args.mmd_output_path,
        mmd_cfg=update_config.get('mmd_update', {}),
    )
    print(f'Pipeline step complete: MMD at {mmd_path}')
    return mmd_path


if __name__ == '__main__':
    main()

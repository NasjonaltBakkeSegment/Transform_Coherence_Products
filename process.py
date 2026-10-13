#!/usr/bin/env python3
"""
Process SAR coherence products: GeoTIFFs → NetCDF → MMD (optional).

This is the main production entry point. It orchestrates the complete pipeline
with intelligent caching and conditional execution.

Usage:
    # Create NetCDF only (default behavior)
    python process.py --base-dir coherence_products/dsc/081/W01N67/20250820/
    
    # Force recreate everything
    python process.py --base-dir <path> --overwrite
    
    # Create NetCDF and MMD
    python process.py --base-dir <path> --create-mmd
    
    # Force MMD recreation only (NetCDF must exist)
    python process.py --base-dir <path> --create-mmd --overwrite
    
    # Custom output locations
    python process.py --base-dir <path> \
                     --netcdf-output netcdf_output/custom.nc \
                     --mmd-output mmd_output/custom.xml \
                     --create-mmd

Exit codes:
    0 = Success (files created or already exist)
    1 = Error (missing required file, invalid input, etc.)
    2 = Skipped (file exists and --overwrite not specified)
"""

import argparse
import sys
import os
from pathlib import Path

# Add repo root to path
repo_root = Path(__file__).parent
sys.path.insert(0, str(repo_root))

from scripts.build_netcdf import main as build_netcdf_main
from scripts.create_mmd import run_create_mmd, update_config


def parse_args(argv=None):
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Process SAR coherence products: GeoTIFFs → NetCDF → MMD (optional).',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # NetCDF only (default)
  python process.py --base-dir coherence_products/dsc/081/W01N67/20250820/
  
  # Create both NetCDF and MMD
    python process.py --base-dir <path> --create-mmd
  
  # Force recreation
    python process.py --base-dir <path> --create-mmd --overwrite
        """,
    )
    
    parser.add_argument(
        '--base-dir',
        default='coherence_products/dsc/081/W01N67/20250820/',
        help='Base directory containing input GeoTIFFs.',
    )
    
    parser.add_argument(
        '--netcdf-output',
        default=None,
        help='NetCDF output path. Defaults to netcdf_output/<derived_name>.nc',
    )
    
    parser.add_argument(
        '--mmd-output',
        default=None,
        help='MMD output path. Defaults to mmd_output/<derived_name>.xml',
    )
    
    parser.add_argument(
        '--create-mmd',
        action='store_true',
        help='Create/update MMD after NetCDF (optional, disabled by default).',
    )
    
    parser.add_argument(
        '--overwrite',
        action='store_true',
        help='Force creation/recreation even if output files already exist.',
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output.',
    )
    
    return parser.parse_args(argv)


def path_exists(path_str):
    """Check if a file or directory exists."""
    return Path(path_str).exists() if path_str else False


def get_latest_netcdf():
    """Get the most recently modified NetCDF file in netcdf_output directory."""
    output_dir = Path('netcdf_output')
    if output_dir.exists():
        files = list(output_dir.glob('*.nc'))
        if files:
            return str(max(files, key=lambda p: p.stat().st_mtime))
    return None


def derive_mmd_path_from_netcdf(netcdf_path):
    """Derive MMD path from NetCDF path (same basename, .xml extension)."""
    if netcdf_path is None:
        return 'mmd_output/output.xml'
    
    stem = Path(netcdf_path).stem
    return f"mmd_output/{stem}.xml"


def main(argv=None):
    """
    Main production orchestrator.
    
    Returns:
        0 = Success
        1 = Error
        2 = Skipped (output exists, not overwriting)
    """
    args = parse_args(argv)
    
    # ========== STEP 1: Build NetCDF ==========
    netcdf_path = args.netcdf_output
    
    # Determine if NetCDF should be skipped
    if netcdf_path:
        # Explicit output path provided - check if it exists
        skip_netcdf = path_exists(netcdf_path) and not args.overwrite
    else:
        # Using derived name - check if any NetCDF exists in output directory
        skip_netcdf = get_latest_netcdf() is not None and not args.overwrite
    
    if skip_netcdf:
        if args.verbose:
            msg = "NetCDF already exists" if path_exists(netcdf_path) else "NetCDF output found"
            print(f"[SKIP] {msg}: {netcdf_path or 'netcdf_output/*.nc'}")
        
        # If we're skipping, get the path of the existing NetCDF file
        if not netcdf_path:
            netcdf_path = get_latest_netcdf()
    else:
        if args.overwrite and (path_exists(netcdf_path) or get_latest_netcdf() is not None):
            if args.verbose and path_exists(netcdf_path):
                print(f"[OVERWRITE] Removing existing NetCDF: {netcdf_path}")
            if path_exists(netcdf_path):
                Path(netcdf_path).unlink()
        
        if args.verbose:
            print(f"[BUILD] Creating NetCDF from {args.base_dir}")
        
        build_args = ['--base-dir', args.base_dir]
        if args.netcdf_output:
            build_args.extend(['--output', args.netcdf_output])
        
        try:
            netcdf_path = build_netcdf_main(build_args)
            print(f"✓ NetCDF created: {netcdf_path}")
        except Exception as e:
            print(f"ERROR: Failed to create NetCDF: {e}", file=sys.stderr)
            return 1
    
    # ========== STEP 2: Build MMD (optional) ==========
    if args.create_mmd:
        mmd_output_dir = Path(args.mmd_output).parent if args.mmd_output else Path('mmd_output')
        mmd_output_dir.mkdir(parents=True, exist_ok=True)
        
        mmd_path = args.mmd_output or derive_mmd_path_from_netcdf(netcdf_path)
        mmd_exists = path_exists(mmd_path)
        
        if mmd_exists and not args.overwrite:
            if args.verbose:
                print(f"[SKIP] MMD already exists: {mmd_path}")
        else:
            if args.overwrite and mmd_exists:
                if args.verbose:
                    print(f"[OVERWRITE] Removing existing MMD: {mmd_path}")
                Path(mmd_path).unlink()
            
            if args.verbose:
                print(f"[BUILD] Creating MMD from {netcdf_path}")
            
            try:
                mmd_path = run_create_mmd(
                    input_file=netcdf_path,
                    output_path=str(mmd_output_dir),
                    mmd_cfg=update_config.get('mmd_update', {}),
                )
                print(f"✓ MMD created: {mmd_path}")
            except Exception as e:
                print(f"ERROR: Failed to create MMD: {e}", file=sys.stderr)
                return 1
    
    print("\n✓ Processing complete")
    return 0


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)

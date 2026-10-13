#!/usr/bin/env python3
"""
Build NetCDF from SAR GeoTIFFs.

Usage:
    python scripts/build_netcdf.py --base-dir coherence_products/dsc/081/W01N67/20250820/
    python scripts/build_netcdf.py --base-dir <path> --output netcdf_output/custom_name.nc
"""
import argparse
import re
import sys
import os
from pathlib import Path

# Add parent directory to path for imports
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))

from src.coherence_to_netcdf.dataset import build_dataset


def sanitize_title_for_filename(title: str) -> str:
    """Convert dataset title to a valid filename."""
    print(title)
    s = title.replace("–", "-").strip()
    s = s.replace(" ", "_")
    s = re.sub(r"[^A-Za-z0-9_.-]+", "", s)
    print(s)
    return s


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build NetCDF from SAR GeoTIFFs.")
    parser.add_argument(
        "--base-dir",
        default="coherence_products/dsc/081/W01N67/20250820/",
        help="Base directory containing the GeoTIFFs.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output NetCDF file path. If not given, a file is created in netcdf_output/ "
             "with a name derived from the dataset title.",
    )

    args = parser.parse_args(argv)

    # Normalize base dir because downstream path-building expects a trailing separator.
    base_dir = args.base_dir if args.base_dir.endswith('/') else f"{args.base_dir}/"

    ds = build_dataset(base_dir=base_dir)

    title = ds.attrs.get("title")
    if title is None:
        raise ValueError(
            "Dataset has no 'title' attribute. Either add one in global_attributes.yaml "
            "or implement title derivation in build_dataset."
        )

    if args.output is None:
        # Create netcdf_output directory if it doesn't exist
        os.makedirs("netcdf_output", exist_ok=True)
        stem = sanitize_title_for_filename(title)
        output_path = f"netcdf_output/{stem}.nc"
    else:
        output_path = args.output

    ds.to_netcdf(output_path)
    print(f"NetCDF written to: {output_path}")
    return output_path


if __name__ == "__main__":
    main()

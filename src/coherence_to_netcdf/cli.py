import argparse
from src.coherence_to_netcdf.dataset import build_dataset

def main(argv=None):
    parser = argparse.ArgumentParser(description="Build NetCDF from SAR GeoTIFFs.")
    parser.add_argument(
        "--base-dir",
        default="coherence_products/dsc/081/W01N67/20250820/",
        help="Base directory containing the GeoTIFFs.",
    )
    parser.add_argument(
        "--output",
        default="combined_data.nc",
        help="Output NetCDF file path.",
    )

    args = parser.parse_args(argv)

    ds = build_dataset(base_dir=args.base_dir)
    ds.to_netcdf(args.output)
    print(f"NetCDF written to: {args.output}")
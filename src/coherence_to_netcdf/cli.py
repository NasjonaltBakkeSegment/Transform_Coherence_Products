import argparse
import re
from src.coherence_to_netcdf.dataset import build_dataset

def sanitize_title_for_filename(title: str) -> str:
    # replace spaces with underscores and remove bad characters
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
        help="Output NetCDF file path. If not given, a name is derived from the dataset title.",
    )

    args = parser.parse_args(argv)

    ds = build_dataset(base_dir=args.base_dir)

    title = ds.attrs.get("title")
    if title is None:
        raise ValueError(
            "Dataset has no 'title' attribute. Either add one in global_attributes.yaml "
            "or implement title derivation in build_dataset."
        )

    if args.output is None:
        stem = sanitize_title_for_filename(title)
        output_path = f"{stem}.nc"
    else:
        output_path = args.output

    ds.to_netcdf(output_path)
    print(f"NetCDF written to: {output_path}")
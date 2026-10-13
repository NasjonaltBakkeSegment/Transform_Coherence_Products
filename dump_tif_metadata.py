#!/usr/bin/env python3
"""
Script to extract and dump metadata from TIF files to text files.
"""
import os
import sys
from pathlib import Path
import rasterio


def dump_tif_metadata(tif_path, output_dir=None):
    """Extract and save metadata from a TIF file to a text file."""
    tif_path = Path(tif_path)
    
    if not tif_path.exists():
        print(f"ERROR: {tif_path} does not exist")
        return False
    
    if output_dir is None:
        output_dir = tif_path.parent
    else:
        output_dir = Path(output_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / f"{tif_path.stem}_metadata.txt"
    
    try:
        with rasterio.open(tif_path) as src:
            with open(output_file, 'w') as f:
                f.write(f"Metadata for: {tif_path.name}\n")
                f.write("=" * 80 + "\n\n")
                
                # Basic properties
                f.write("BASIC PROPERTIES\n")
                f.write("-" * 80 + "\n")
                f.write(f"Driver: {src.driver}\n")
                f.write(f"Width: {src.width}\n")
                f.write(f"Height: {src.height}\n")
                f.write(f"Count (bands): {src.count}\n")
                f.write(f"Data type: {src.dtypes[0] if src.dtypes else 'Unknown'}\n")
                f.write(f"Nodata value: {src.nodata}\n")
                f.write("\n")
                
                # CRS and Transform
                f.write("COORDINATE REFERENCE SYSTEM\n")
                f.write("-" * 80 + "\n")
                f.write(f"CRS: {src.crs}\n")
                f.write(f"Transform:\n{src.transform}\n")
                f.write(f"Bounds: {src.bounds}\n")
                f.write("\n")
                
                # Band information
                f.write("BAND INFORMATION\n")
                f.write("-" * 80 + "\n")
                for i in range(1, src.count + 1):
                    band = src.read(i)
                    f.write(f"\nBand {i}:\n")
                    f.write(f"  Data type: {src.dtypes[i-1]}\n")
                    f.write(f"  Min value: {band.min()}\n")
                    f.write(f"  Max value: {band.max()}\n")
                    f.write(f"  Mean value: {band.mean()}\n")
                    f.write(f"  Std dev: {band.std()}\n")
                    f.write(f"  Nodata value: {src.nodata}\n")
                
                f.write("\n")
                
                # Tags and metadata
                f.write("METADATA TAGS\n")
                f.write("-" * 80 + "\n")
                if src.tags():
                    for key, value in src.tags().items():
                        f.write(f"{key}: {value}\n")
                else:
                    f.write("No tags found\n")
                
                f.write("\n")
                
                # Band tags
                f.write("BAND-SPECIFIC TAGS\n")
                f.write("-" * 80 + "\n")
                for i in range(1, src.count + 1):
                    band_tags = src.tags(bidx=i)
                    if band_tags:
                        f.write(f"\nBand {i} tags:\n")
                        for key, value in band_tags.items():
                            f.write(f"  {key}: {value}\n")
                    else:
                        f.write(f"\nBand {i}: No tags\n")
                
                f.write("\n")
                
                # Profile
                f.write("FILE PROFILE\n")
                f.write("-" * 80 + "\n")
                for key, value in src.profile.items():
                    f.write(f"{key}: {value}\n")
        
        print(f"✓ Metadata dumped to: {output_file}")
        return True
    
    except Exception as e:
        print(f"ERROR processing {tif_path}: {e}")
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python dump_tif_metadata.py <base_dir> [output_dir]")
        print("  base_dir: Directory containing TIF files")
        print("  output_dir: (Optional) Directory to save metadata files. Default: same as base_dir")
        sys.exit(1)
    
    base_dir = Path(sys.argv[1])
    output_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else base_dir
    
    if not base_dir.exists():
        print(f"ERROR: {base_dir} does not exist")
        sys.exit(1)
    
    # Find all TIF files
    tif_files = sorted(base_dir.glob("*.tif"))
    
    if not tif_files:
        print(f"No TIF files found in {base_dir}")
        sys.exit(0)
    
    print(f"Found {len(tif_files)} TIF file(s) in {base_dir}\n")
    
    success_count = 0
    for tif_file in tif_files:
        if dump_tif_metadata(tif_file, output_dir):
            success_count += 1
    
    print(f"\n✓ Successfully processed {success_count}/{len(tif_files)} files")


if __name__ == "__main__":
    main()

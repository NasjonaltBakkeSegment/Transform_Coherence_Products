from typing import Dict, Any
import rasterio
from pyproj import CRS, Transformer


def build_cf_crs_attrs_from_rasterio(src: rasterio.io.DatasetReader) -> Dict[str, Any]:
    """
    Build CF-style CRS attributes using pyproj instead of rasterio's WKT parsing.
    """
    attrs: Dict[str, Any] = {}

    # Build a pyproj CRS from the rasterio CRS dict
    crs_dict = src.crs.to_dict()
    crs = CRS.from_dict(crs_dict)

    # Get CF-style dict from pyproj
    cf = crs.to_cf()
    # 'cf' is a dict like {'grid_mapping_name': ..., 'semi_major_axis': ..., ...}

    attrs.update(cf)

    # Keep a spatial_ref / epsg_code for completeness
    attrs["spatial_ref"] = crs.to_wkt()
    try:
        epsg = crs.to_epsg()
    except Exception:
        epsg = None
    if epsg is not None:
        attrs["epsg_code"] = f"EPSG:{epsg}"

    return attrs

def make_utm_to_latlon_transformer(src: rasterio.io.DatasetReader) -> Transformer:
    """
    Create a pyproj Transformer from the raster CRS to WGS84 (EPSG:4326).
    """
    crs_dict = src.crs.to_dict()
    src_crs = CRS.from_dict(crs_dict)
    dst_crs = CRS.from_epsg(4326)
    transformer = Transformer.from_crs(src_crs, dst_crs, always_xy=True)
    return transformer
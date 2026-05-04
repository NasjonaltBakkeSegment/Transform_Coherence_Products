from typing import Dict, Any
import rasterio


def build_cf_crs_attrs_from_rasterio(src: rasterio.io.DatasetReader) -> Dict[str, Any]:
    """
    Build a CF-style grid_mapping attributes dict from a rasterio dataset,
    using only information available in the CRS (no guessed values).
    """
    crs = src.crs
    if crs is None:
        return {}

    attrs: Dict[str, Any] = {}

    # WKT as descriptive metadata
    attrs["spatial_ref"] = crs.to_wkt()

    # EPSG code, if reported
    to_epsg = getattr(crs, "to_epsg", None)
    epsg = to_epsg() if callable(to_epsg) else None
    if epsg is not None:
        attrs["epsg_code"] = f"EPSG:{epsg}"

    # PROJ / CRS dict – contains numeric parameters corresponding to WKT
    crs_dict = crs.to_dict()
    proj_name = crs_dict.get("proj", "").lower()

    # Map known proj names to CF grid_mapping_name and parameters,
    # but only when parameters are present in crs_dict.
    if proj_name in {"utm", "tmerc", "transverse_mercator"}:
        attrs["grid_mapping_name"] = "transverse_mercator"

        if "lon_0" in crs_dict:
            attrs["longitude_of_central_meridian"] = float(crs_dict["lon_0"])
        if "lat_0" in crs_dict:
            attrs["latitude_of_projection_origin"] = float(crs_dict["lat_0"])
        if "k" in crs_dict:
            attrs["scale_factor_at_central_meridian"] = float(crs_dict["k"])
        if "x_0" in crs_dict:
            attrs["false_easting"] = float(crs_dict["x_0"])
        if "y_0" in crs_dict:
            attrs["false_northing"] = float(crs_dict["y_0"])

    elif proj_name in {"longlat", "latlong"}:
        attrs["grid_mapping_name"] = "latitude_longitude"
    else:
        attrs["grid_mapping_name"] = proj_name or "unknown"

    # Ellipsoid parameters
    if "a" in crs_dict:
        attrs["semi_major_axis"] = float(crs_dict["a"])
    if "rf" in crs_dict and crs_dict["rf"]:
        attrs["inverse_flattening"] = float(crs_dict["rf"])

    units = crs_dict.get("units")
    if units:
        attrs["units"] = units

    return attrs
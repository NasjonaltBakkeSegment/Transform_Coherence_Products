from typing import Dict, Any
import xarray as xr
import rasterio

from src.coherence_to_netcdf.io import load_yaml
from src.coherence_to_netcdf.coords import compute_coordinates
from src.coherence_to_netcdf.crs import build_cf_crs_attrs_from_rasterio


def load_raster_as_dataarray(
    var_name: str,
    path: str,
    var_attrs_from_yaml: Dict[str, Any],
) -> xr.DataArray:
    """
    Load a single GeoTIFF as an xarray.DataArray.
    """
    with rasterio.open(path) as src:
        data = src.read(1)
        x, y = compute_coordinates(src)

        da = xr.DataArray(
            data,
            dims=("y", "x"),
            coords={"x": x, "y": y},
            name=var_name,
        )

        da.attrs.update(var_attrs_from_yaml or {})
        da.attrs.update({
            "transform": str(src.transform),
            "nodata": src.nodata,
        })

    return da


def build_dataset(base_dir: str) -> xr.Dataset:
    """
    Build the xarray.Dataset from the 5 known GeoTIFFs in `base_dir`.
    """
    input_files = {
        "VV_coherence": base_dir + "W01N67_081_20250814_20250820_VV_coherence.tif",
        "VV_gamma_nought": base_dir + "W01N67_081_20250820_VV_gamma_nought.tif",
        "VH_gamma_nought": base_dir + "W01N67_081_20250820_VH_gamma_nought.tif",
        "VV_sigma_nought": base_dir + "W01N67_081_20250820_VV_sigma_nought.tif",
        "VH_sigma_nought": base_dir + "W01N67_081_20250820_VH_sigma_nought.tif",
    }

    var_attr_yaml_path = "config/variable_attributes.yaml"
    global_attr_yaml_path = "config/global_attributes.yaml"

    variable_attrs_all = load_yaml(var_attr_yaml_path)
    global_attrs = load_yaml(global_attr_yaml_path)

    data_vars: Dict[str, xr.DataArray] = {}

    for var_name, tif_path in input_files.items():
        var_attrs = variable_attrs_all.get(var_name, {})
        da = load_raster_as_dataarray(var_name, tif_path, var_attrs)
        data_vars[var_name] = da

    ds = xr.Dataset(data_vars)
    ds.attrs.update(global_attrs)

    # Apply x/y attributes from config, if present
    x_attrs = variable_attrs_all.get("x", {})
    y_attrs = variable_attrs_all.get("y", {})
    if "x" in ds.coords:
        ds.coords["x"].attrs.update(x_attrs)
    if "y" in ds.coords:
        ds.coords["y"].attrs.update(y_attrs)

    # CRS / grid_mapping
    first_path = next(iter(input_files.values()))
    with rasterio.open(first_path) as src:
        crs_attrs = build_cf_crs_attrs_from_rasterio(src)

    if crs_attrs:
        ds["crs"] = xr.DataArray(0, attrs=crs_attrs)
        for v in ds.data_vars:
            ds[v].attrs["grid_mapping"] = "crs"

    return ds
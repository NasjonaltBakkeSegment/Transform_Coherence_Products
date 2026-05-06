from typing import Dict, Any
import xarray as xr
import rasterio
import uuid
import datetime as dt
from pathlib import Path
from src.coherence_to_netcdf.io import load_yaml
from src.coherence_to_netcdf.coords import compute_coordinates, compute_latlon_2d
from src.coherence_to_netcdf.crs import build_cf_crs_attrs_from_rasterio, make_utm_to_latlon_transformer

def derive_title_from_tif(tif_path: str) -> str:
    """
    Derive a human-readable title from a GeoTIFF filename.
    Example filename: W01N67_081_20250814_20250820_VV_coherence.tif
    -> "W01N67 081 20250814–20250820 VV coherence"
    """
    p = Path(tif_path)
    stem = p.stem  # filename without extension

    parts = stem.split("_")
    if len(parts) >= 5:
        tile_id = parts[0]        # W01N67
        track = parts[1]          # 081
        date1 = parts[2]          # 20250814
        date2 = parts[3]          # 20250820
        prod  = parts[4]          # VV_coherence
        prod = prod.replace("_", " ")

        title = f"{tile_id} track {track} {date1}-{date2} coherence"
    else:
        # Fallback: just use the stem
        title = stem

    return title

def generate_nbs_id(filename):
    '''
    Generate a UUID with a reverse domain name as a prefix e.g. no.met.nbs:bb520b13-206a-5622-aba3-395ea5a59815
    v5 uuids are created as a function of a string. Here the product name (suffix removed) is used.
    The same id is created if the code is run again for the same product.
    '''
    product_name = filename.split('.')[0]
    rdn='no.met.nbs:' # reverse domain name
    nbs_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, product_name)
    nbs_id = rdn + str(nbs_uuid)
    return nbs_id

def update_global_attributes(global_attributes, lat, lon):

    t0 = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    global_attributes.update({
        'date_metadata_modified': t0,
        'date_metadata_modified_type': 'Created',
        'date_created': t0,
        'history': f'{t0}: Converted from SAFE to NetCDF by NBS team.',
        'geospatial_lat_min': float(lat.min()),
        'geospatial_lat_max': float(lat.max()),
        'geospatial_lon_min': float(lon.min()),
        'geospatial_lon_max': float(lon.max()),
    })

    if global_attributes['geospatial_lat_max'] > 70:
        global_attributes['collection'] += ',SIOS'

    global_attributes['id'] = generate_nbs_id(global_attributes['title'])

    return global_attributes

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

    # If title is not already set in YAML, derive it from one of the TIFFs
    if "title" not in global_attrs:
        ref_tif = input_files["VV_coherence"]
        derived_title = derive_title_from_tif(ref_tif)
        if not derived_title:
            raise ValueError("No title in global_attributes.yaml and could not derive title from TIFF.")
        global_attrs["title"] = derived_title


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
        x = ds.coords["x"].values
        y = ds.coords["y"].values

        # Build transformer and CF CRS attrs using pyproj
        transformer = make_utm_to_latlon_transformer(src)
        lon2d, lat2d = compute_latlon_2d(x, y, transformer)
        crs_attrs = build_cf_crs_attrs_from_rasterio(src)

    ds["lon"] = xr.DataArray(
        lon2d,
        dims=("y", "x"),
        attrs=variable_attrs_all.get("lon", {}),
    )
    ds["lat"] = xr.DataArray(
        lat2d,
        dims=("y", "x"),
        attrs=variable_attrs_all.get("lat", {}),
    )

    if crs_attrs:
        ds["crs"] = xr.DataArray(0, attrs=crs_attrs)
        for v in ds.data_vars:
            ds[v].attrs["grid_mapping"] = "crs"

    global_attrs = update_global_attributes(global_attrs, ds["lat"], ds["lon"])
    ds.attrs.update(global_attrs)

    return ds
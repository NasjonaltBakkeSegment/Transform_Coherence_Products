import numpy as np
import rasterio
from pyproj import Transformer

def compute_coordinates(src: rasterio.io.DatasetReader):
    """
    Compute x/y coordinates from the rasterio dataset using the affine transform.
    Assumes north-up image.
    """
    transform = src.transform

    x = src.bounds.left + (np.arange(src.width) + 0.5) * transform.a
    y = src.bounds.top + (np.arange(src.height) + 0.5) * transform.e

    return x.astype("float32"), y.astype("float32")

def compute_latlon_2d(
    x: np.ndarray,
    y: np.ndarray,
    transformer: Transformer,
):
    """
    Compute 2D lon/lat arrays using a pyproj Transformer.
    x, y are 1D projection coordinates (metres); transformer goes to EPSG:4326.
    """
    xx, yy = np.meshgrid(x, y)
    xx_flat = xx.ravel()
    yy_flat = yy.ravel()

    lon_flat, lat_flat = transformer.transform(xx_flat, yy_flat)
    lon = np.asarray(lon_flat, dtype="float32").reshape(yy.shape)
    lat = np.asarray(lat_flat, dtype="float32").reshape(yy.shape)

    return lon, lat
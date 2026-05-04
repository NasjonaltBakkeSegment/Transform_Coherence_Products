import numpy as np
import rasterio


def compute_coordinates(src: rasterio.io.DatasetReader):
    """
    Compute x/y coordinates from the rasterio dataset using the affine transform.
    Assumes north-up image.
    """
    transform = src.transform

    x = src.bounds.left + (np.arange(src.width) + 0.5) * transform.a
    y = src.bounds.top + (np.arange(src.height) + 0.5) * transform.e

    return x.astype("float32"), y.astype("float32")
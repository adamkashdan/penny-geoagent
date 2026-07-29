"""
Creates a 2017 raster DEM from MCoRDS L2 flight track points using linear interpolation,
and compares it as a continuous raster grid with the 2015-2016 DEM.
Saves the interpolated DEM as a GeoTIFF and outputs comparison maps.
"""
from __future__ import annotations
import os
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.transform import from_origin
from rasterio.warp import transform
from scipy.interpolate import griddata
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
DATA_DIR = os.path.join(BASE_DIR, "data")
DEM_DIR = os.path.join(DATA_DIR, "DEM_2015-2016")

TIF_DEM_PATH = os.path.join(DEM_DIR, "baffin_glacier_Name_Penny Ice Cap.tif")
SHP_PATH = os.path.join(DEM_DIR, "Name_Penny Ice Cap.shp")
CSV_PATH = os.path.join(DATA_DIR, "IRMCR2_20170428_03_raw_data.csv")
TIF_2017_PATH = os.path.join(DATA_DIR, "penny_dem_2017_interpolated.tif")


def load_mcords_points() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Loads 2017 MCoRDS points and returns projected coordinates (x, y) and elevation values."""
    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(f"Missing primary data file at {CSV_PATH}")
    df = pd.read_csv(CSV_PATH)
    df = df.dropna(subset=["LAT", "LON"])
    df["z_2017"] = df.apply(
        lambda row: float(row["ELEVATION"] - row["SURFACE"]) 
        if row["ELEVATION"] > -9000 and row["SURFACE"] > -9000 else np.nan, 
        axis=1
    )
    df = df.dropna(subset=["z_2017"])
    
    # Project to Albers (ESRI:102008)
    print("Projecting MCoRDS 2017 points to Albers (ESRI:102008)...")
    xs, ys = transform('EPSG:4326', 'ESRI:102008', df['LON'].tolist(), df['LAT'].tolist())
    return np.array(xs), np.array(ys), df['z_2017'].to_numpy()


def run_dem_interpolation():
    print("=== Creating 2017 DEM from MCoRDS Track Points ===")
    
    # Load 2017 points
    xs, ys, zs = load_mcords_points()
    points = np.column_stack((xs, ys))
    
    # Find bounding box of flight lines
    x_min, x_max = xs.min(), xs.max()
    y_min, y_max = ys.min(), ys.max()
    print(f"Flight line extent UTM (ESRI:102008):")
    print(f"  X: {x_min:.1f} to {x_max:.1f}")
    print(f"  Y: {y_min:.1f} to {y_max:.1f}")
    
    # Define regular grid size (300 x 300 cells)
    grid_size = 300
    x_grid = np.linspace(x_min, x_max, grid_size)
    y_grid = np.linspace(y_max, y_min, grid_size)  # top to bottom for raster rows
    grid_x, grid_y = np.meshgrid(x_grid, y_grid)
    
    # Interpolate using linear method
    print("Interpolating points to grid (linear method)...")
    grid_z17 = griddata(points, zs, (grid_x, grid_y), method="linear")
    
    # Mask out nan values for writing to TIFF
    # We will write it with a nodata value of -9999.0
    grid_z17_write = np.where(np.isnan(grid_z17), -9999.0, grid_z17).astype(np.float32)
    
    # Define GeoTIFF transform parameters
    res_x = (x_max - x_min) / (grid_size - 1)
    res_y = (y_max - y_min) / (grid_size - 1)
    # top-left corner is (x_min, y_max)
    transform_new = from_origin(x_min, y_max, res_x, res_y)
    
    print(f"Saving interpolated 2017 DEM to GeoTIFF: {TIF_2017_PATH}")
    with rasterio.open(
        TIF_2017_PATH,
        'w',
        driver='GTiff',
        height=grid_size,
        width=grid_size,
        count=1,
        dtype=np.float32,
        crs='ESRI:102008',
        transform=transform_new,
        nodata=-9999.0
    ) as dst:
        dst.write(grid_z17_write, 1)
        
    print("DEM GeoTIFF written successfully.")
    
    # 5. Load 2015-2016 DEM and sample it at the grid locations
    print("Sampling 2015-2016 DEM at the same grid cells...")
    grid_coords = np.column_stack((grid_x.ravel(), grid_y.ravel()))
    
    with rasterio.open(TIF_DEM_PATH) as src_dem:
        grid_zdem = np.array([val[0] for val in src_dem.sample(grid_coords)]).reshape((grid_size, grid_size))
        grid_zdem = np.where(grid_zdem == src_dem.nodata, np.nan, grid_zdem)
        
    # Calculate elevation change
    # dz = z_dem - z_2017
    # Note: Mean datum offset between ellipsoidal (2017) and orthometric (2015-2016) is ~21.15m
    grid_dz_raw = grid_zdem - grid_z17
    grid_dz_corrected = grid_dz_raw - 21.153
    
    # Load Shapefile outline for overlay
    print("Loading glacier boundary outline...")
    gdf = gpd.read_file(SHP_PATH)
    
    # Plotting
    print("Generating comparison plots...")
    dem_extent = [x_min, x_max, y_min, y_max]
    
    # Plot 1: Interpolated 2017 DEM
    fig, ax = plt.subplots(figsize=(6, 5))
    im = ax.imshow(grid_z17, cmap="terrain", extent=dem_extent, origin="upper")
    gdf.boundary.plot(ax=ax, color="black", linewidth=1.0)
    ax.set_title("Penny Ice Cap: Interpolated DEM (2017)", fontsize=10, fontweight="bold")
    ax.set_xlabel("Easting (meters, North America Albers)", fontsize=8)
    ax.set_ylabel("Northing (meters, North America Albers)", fontsize=8)
    fig.colorbar(im, ax=ax, label="Elevation (m above ellipsoid)")
    out_17 = os.path.join(BASE_DIR, "penny_dem_2017_interpolated.png")
    fig.savefig(out_17, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved 2017 DEM plot to {out_17}")
    
    # Plot 2: Corrected Elevation Change Map
    # Filter extreme outliers in the visualization
    grid_dz_vis = np.where((grid_dz_corrected < -20.0) | (grid_dz_corrected > 20.0), np.nan, grid_dz_corrected)
    
    fig, ax = plt.subplots(figsize=(6, 5))
    im = ax.imshow(grid_dz_vis, cmap="RdBu", extent=dem_extent, origin="upper", vmin=-15, vmax=15)
    gdf.boundary.plot(ax=ax, color="black", linewidth=1.0)
    ax.set_title("Glacier Thinning / Elevation Change (2015-2016 vs 2017)\n(Datum Corrected, N = -21.15 m)", fontsize=9, fontweight="bold")
    ax.set_xlabel("Easting (meters, North America Albers)", fontsize=8)
    ax.set_ylabel("Northing (meters, North America Albers)", fontsize=8)
    fig.colorbar(im, ax=ax, label="Elevation Change (meters)")
    out_diff = os.path.join(BASE_DIR, "glacier_dem_change_raster.png")
    fig.savefig(out_diff, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved difference raster plot to {out_diff}")
    
    # Compute raster-based stats
    valid_dz = grid_dz_corrected[~np.isnan(grid_dz_corrected)]
    print(f"\n=== Raster-Based DEM Comparison Stats ===")
    print(f"Total overlapping pixels (within flight tract convex hull): {len(valid_dz)}")
    print(f"Mean Net Change: {valid_dz.mean():.3f} meters")
    print(f"Median Net Change: {np.median(valid_dz):.3f} meters")
    print(f"Std Dev of Change: {valid_dz.std():.3f} meters")


if __name__ == "__main__":
    run_dem_interpolation()

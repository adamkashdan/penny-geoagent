"""
Historical analysis script for the Penny Ice Cap.
Compares surface elevation and ice thickness measurements
across 2013, 2014, 2015, and 2017 flight campaigns.
Applies subglacial bedrock calibration to correct for geodetic vertical datum offsets.
"""
from __future__ import annotations
import os
import glob
import numpy as np
import pandas as pd
import geopandas as gpd
from rasterio.warp import transform
from scipy.interpolate import griddata
from scipy.spatial import cKDTree
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
DATA_DIR = os.path.join(BASE_DIR, "data")
DEM_DIR = os.path.join(DATA_DIR, "DEM_2015-2016")
SHP_PATH = os.path.join(DEM_DIR, "Name_Penny Ice Cap.shp")


def load_year_data(year: int) -> pd.DataFrame:
    """Loads and filters raw MCoRDS data for a specific year, calculating surface and bed elevations."""
    if year == 2017:
        paths = [os.path.join(DATA_DIR, "IRMCR2_20170428_03_raw_data.csv")]
    else:
        paths = glob.glob(os.path.join(DATA_DIR, f"IRMCR2_{year}*.csv"))
        
    dfs = []
    for p in paths:
        if os.path.exists(p):
            dfs.append(pd.read_csv(p))
            
    if not dfs:
        raise FileNotFoundError(f"No files found for year {year}")
        
    df = pd.concat(dfs, ignore_index=True)
    df = df.dropna(subset=["LAT", "LON"])
    
    # Crop to Penny Ice Cap bounding box
    df = df[
        (df["LAT"] >= 66.3) & (df["LAT"] <= 68.0) &
        (df["LON"] >= -67.8) & (df["LON"] <= -63.5)
    ].copy()
    
    # z_surf = ELEVATION - SURFACE (ellipsoidal height)
    df["z_surf"] = df.apply(
        lambda row: float(row["ELEVATION"] - row["SURFACE"]) 
        if row["ELEVATION"] > -9000 and row["SURFACE"] > -9000 else np.nan, 
        axis=1
    )
    
    df["ice_thickness"] = df["THICK"].apply(lambda val: float(val) if val > 0 else np.nan)
    
    # z_bed = z_surf - ice_thickness
    df["z_bed"] = df["z_surf"] - df["ice_thickness"]
    
    return df


def run_historical_analysis():
    print("=== Starting Penny Ice Cap Bedrock-Calibrated Historical Analysis (2013-2017) ===")
    
    years = [2013, 2014, 2015, 2017]
    data_by_year = {}
    
    for yr in years:
        print(f"Loading data for {yr}...")
        data_by_year[yr] = load_year_data(yr)
        
    # Project all points to North America Albers (ESRI:102008)
    projected_points = {}
    for yr, df in data_by_year.items():
        xs, ys = transform('EPSG:4326', 'ESRI:102008', df['LON'].tolist(), df['LAT'].tolist())
        df['x_proj'] = xs
        df['y_proj'] = ys
        projected_points[yr] = np.column_stack((xs, ys))
        
    # Build KDTrees for track-based co-location matching
    # We will use 2017 as the baseline year
    df_17 = data_by_year[2017]
    tree_17 = cKDTree(projected_points[2017])
    
    # Calculate geodetic datum corrections based on the static bedrock elevation at overlapping points (within 100m)
    # We define 2017 as the reference datum (Correction = 0.0)
    corrections = {2017: 0.0}
    
    print("\n--- Performing Bedrock Calibration ---")
    for yr in [2013, 2014, 2015]:
        df_yr = data_by_year[yr]
        pts_yr = projected_points[yr]
        
        # Query closest 2017 points
        dists, indices = tree_17.query(pts_yr)
        df_yr['dist_to_17'] = dists
        df_yr['idx_17'] = indices
        
        # Select overlapping points (distance <= 100m) with valid bedrock data in both years
        overlap = df_yr[df_yr['dist_to_17'] <= 100.0].copy()
        corr_17 = df_17.iloc[overlap['idx_17']].copy().reset_index(drop=True)
        overlap = overlap.reset_index(drop=True)
        
        valid_mask = overlap['z_bed'].notna() & corr_17['z_bed'].notna()
        
        if valid_mask.sum() > 0:
            # Bedrock difference: z_bed_17 - z_bed_yr
            bed_diff = corr_17.loc[valid_mask, 'z_bed'].to_numpy() - overlap.loc[valid_mask, 'z_bed'].to_numpy()
            mean_offset = float(np.mean(bed_diff))
            corrections[yr] = mean_offset
            print(f"Year {yr}: Found {valid_mask.sum()} co-located bedrock points. Mean vertical offset = {mean_offset:.3f} m")
        else:
            corrections[yr] = 0.0
            print(f"Year {yr}: No co-located bedrock points found. Setting vertical offset to 0.0 m")
            
    # Apply vertical datum corrections to raw surface elevations
    print("\nApplying vertical datum corrections to z_surf...")
    for yr in years:
        offset = corrections[yr]
        data_by_year[yr]['z_surf_corr'] = data_by_year[yr]['z_surf'] + offset
        data_by_year[yr]['z_bed_corr'] = data_by_year[yr]['z_surf_corr'] - data_by_year[yr]['ice_thickness']
        
    # Now interpolate the calibrated datasets onto a regular grid for spatial mapping
    x_min, x_max = df_17['x_proj'].min(), df_17['x_proj'].max()
    y_min, y_max = df_17['y_proj'].min(), df_17['y_proj'].max()
    
    grid_size = 200
    x_grid = np.linspace(x_min, x_max, grid_size)
    y_grid = np.linspace(y_max, y_min, grid_size)
    grid_x, grid_y = np.meshgrid(x_grid, y_grid)
    grid_pts = np.column_stack((grid_x.ravel(), grid_y.ravel()))
    
    # 2000m proximity mask to hide extrapolation artifacts
    dists_grid, _ = tree_17.query(grid_pts)
    mask = dists_grid.reshape((grid_size, grid_size)) > 2000.0
    
    gridded_surf = {}
    gridded_thick = {}
    
    for yr, df in data_by_year.items():
        print(f"Interpolating calibrated {yr} data onto grid...")
        
        # Surface elevation
        df_s = df.dropna(subset=['z_surf_corr'])
        pts_s = np.column_stack((df_s['x_proj'], df_s['y_proj']))
        grid_s = griddata(pts_s, df_s['z_surf_corr'].to_numpy(), (grid_x, grid_y), method='linear')
        grid_s[mask] = np.nan
        gridded_surf[yr] = grid_s
        
        # Ice thickness
        df_t = df.dropna(subset=['ice_thickness'])
        pts_t = np.column_stack((df_t['x_proj'], df_t['y_proj']))
        grid_t = griddata(pts_t, df_t['ice_thickness'].to_numpy(), (grid_x, grid_y), method='linear')
        grid_t[mask] = np.nan
        gridded_thick[yr] = grid_t
        
    # Calculate calibrated changes (2017 minus 2013)
    dz_surf_corr = gridded_surf[2017] - gridded_surf[2013]
    d_thick = gridded_thick[2017] - gridded_thick[2013]
    
    valid_dz = dz_surf_corr[~np.isnan(dz_surf_corr)]
    valid_dh = d_thick[~np.isnan(d_thick)]
    
    print("\n=== Calibrated Overlapping Stats (2017 minus 2013) ===")
    print(f"Mean Calibrated Surface Elevation Change: {valid_dz.mean():.3f} meters")
    print(f"Median Calibrated Surface Elevation Change: {np.median(valid_dz):.3f} meters")
    print(f"Mean Ice Thickness Change: {valid_dh.mean():.3f} meters")
    print(f"Median Ice Thickness Change: {np.median(valid_dh):.3f} meters")
    
    annual_change_rate = valid_dz.mean() / 4.0
    print(f"Calibrated annual thinning rate: {annual_change_rate:.3f} m/year")
    
    # Save text report
    summary_text = f"""=== Penny Ice Cap Calibrated Historical Analysis (2013-2017) ===
Comparison Period: 2013 to 2017 (4 years)
Total Gridded Cells Examined (2km buffer): {len(valid_dz)}

Geodetic Vertical Datum Corrections Applied (aligned to 2017 baseline):
  - 2013 correction: {corrections[2013]:+.3f} meters
  - 2014 correction: {corrections[2014]:+.3f} meters
  - 2015 correction: {corrections[2015]:+.3f} meters
  - 2017 correction: {corrections[2017]:+.3f} meters

Calibrated Surface Elevation Change (z_2017 - z_2013):
  - Mean Change: {valid_dz.mean():.3f} meters
  - Median Change: {np.median(valid_dz):.3f} meters
  - Std Dev: {valid_dz.std():.3f} meters
  - Average Thinning Rate: {annual_change_rate:.3f} meters/year

Ice Thickness Change (H_2017 - H_2013):
  - Mean Change: {valid_dh.mean():.3f} meters
  - Median Change: {np.median(valid_dh):.3f} meters
  - Std Dev: {valid_dh.std():.3f} meters
"""
    summary_path = os.path.join(DATA_DIR, "historical_analysis_summary.txt")
    with open(summary_path, "w") as f:
        f.write(summary_text)
    print(f"Saved calibrated text report to: {summary_path}")
    
    # Save the plots
    # Plot 1: Trend line (calibrated means on a shared mask)
    print("Generating calibrated temporal trend plots...")
    combined_mask = mask.copy()
    for yr in years:
        combined_mask |= np.isnan(gridded_surf[yr]) | np.isnan(gridded_thick[yr])
        
    mean_surf = [np.mean(gridded_surf[yr][~combined_mask]) for yr in years]
    mean_thick = [np.mean(gridded_thick[yr][~combined_mask]) for yr in years]
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.5))
    
    ax1.plot(years, mean_surf, marker='o', color='blue', linewidth=2)
    ax1.set_title("Calibrated Mean Surface Elevation", fontsize=10, fontweight="bold")
    ax1.set_ylabel("Elevation (m above ellipsoid)", fontsize=9)
    ax1.set_xticks(years)
    ax1.grid(True, linestyle="--", alpha=0.5)
    
    ax2.plot(years, mean_thick, marker='s', color='red', linewidth=2)
    ax2.set_title("Mean Ice Thickness", fontsize=10, fontweight="bold")
    ax2.set_ylabel("Thickness (m)", fontsize=9)
    ax2.set_xticks(years)
    ax2.grid(True, linestyle="--", alpha=0.5)
    
    fig.suptitle("Penny Ice Cap: Calibrated Glaciological Trends (2013-2017)", fontsize=12, fontweight="bold")
    trend_plot_path = os.path.join(BASE_DIR, "historical_glacier_trends.png")
    fig.savefig(trend_plot_path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved trends plot to: {trend_plot_path}")
    
    # Plot 2: Calibrated Surface Elevation Change and Thickness Change Map (Two-Panel Figure)
    print("Generating calibrated surface and thickness change maps (two-panel)...")
    gdf_boundary = gpd.read_file(SHP_PATH) if os.path.exists(SHP_PATH) else None
    extent = [x_min, x_max, y_min, y_max]
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5.5), sharey=True)
    
    # Left subplot (ax1): Surface elevation change
    im1 = ax1.imshow(dz_surf_corr, cmap="RdBu", extent=extent, origin="upper", vmin=-15, vmax=15)
    if gdf_boundary is not None:
        gdf_boundary.boundary.plot(ax=ax1, color="black", linewidth=1.0)
    ax1.set_title("(a) Calibrated Surface Elevation Change\n(2017 minus 2013)", fontsize=10, fontweight="bold")
    ax1.set_xlabel("Easting (m, North America Albers)", fontsize=8)
    ax1.set_ylabel("Northing (m, North America Albers)", fontsize=8)
    ax1.grid(True, linestyle="--", alpha=0.3)
    cbar1 = fig.colorbar(im1, ax=ax1, shrink=0.7, pad=0.03)
    cbar1.set_label("Elevation Change (meters)", fontsize=8)
    
    # Right subplot (ax2): Thickness change
    im2 = ax2.imshow(d_thick, cmap="RdBu", extent=extent, origin="upper", vmin=-15, vmax=15)
    if gdf_boundary is not None:
        gdf_boundary.boundary.plot(ax=ax2, color="black", linewidth=1.0)
    ax2.set_title("(b) Ice Thickness Change\n(2017 minus 2013)", fontsize=10, fontweight="bold")
    ax2.set_xlabel("Easting (m, North America Albers)", fontsize=8)
    ax2.grid(True, linestyle="--", alpha=0.3)
    cbar2 = fig.colorbar(im2, ax=ax2, shrink=0.7, pad=0.03)
    cbar2.set_label("Thickness Change (meters)", fontsize=8)
    
    fig.tight_layout()
    
    surf_change_path = os.path.join(BASE_DIR, "historical_elevation_change_map.png")
    fig.savefig(surf_change_path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved calibrated two-panel change map to: {surf_change_path}")
    
    # Plot 3: Standalone Ice Thickness Change Map (for compatibility)
    print("Generating individual thickness change map...")
    fig, ax = plt.subplots(figsize=(6, 5))
    im = ax.imshow(d_thick, cmap="RdBu", extent=extent, origin="upper", vmin=-15, vmax=15)
    if gdf_boundary is not None:
        gdf_boundary.boundary.plot(ax=ax, color="black", linewidth=1.0)
    ax.set_title("Penny Ice Cap: Ice Thickness Change (2017 - 2013)", fontsize=9, fontweight="bold")
    ax.set_xlabel("Easting (m, North America Albers)", fontsize=8)
    ax.set_ylabel("Northing (m, North America Albers)", fontsize=8)
    cbar = fig.colorbar(im, ax=ax, shrink=0.8, pad=0.03)
    cbar.set_label("Thickness Change (meters)", fontsize=8)
    
    thick_change_path = os.path.join(BASE_DIR, "historical_thickness_change_map.png")
    fig.savefig(thick_change_path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved thickness change map to: {thick_change_path}")


if __name__ == "__main__":
    run_historical_analysis()

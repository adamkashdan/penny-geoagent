"""
Digital Elevation Model (DEM) 2022 analysis and comparison script.
Compares 2022 DEM elevations with 2017 MCoRDS L2 surface elevations
to estimate glacier elevation change (ablation/thinning).
"""
from __future__ import annotations
import os
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.warp import transform
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
DATA_DIR = os.path.join(BASE_DIR, "data")
DEM_DIR = os.path.join(DATA_DIR, "DEM_2022")

TIF_PATH = os.path.join(DEM_DIR, "baffin_glacier_Name_Penny Ice Cap.tif")
SHP_PATH = os.path.join(DEM_DIR, "Name_Penny Ice Cap.shp")
CSV_PATH = os.path.join(DATA_DIR, "IRMCR2_20170428_03_raw_data.csv")


def load_mcords_surface_data() -> pd.DataFrame:
    """Loads 2017 MCoRDS L2 flight track and computes surface elevation."""
    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(f"Missing primary data file at {CSV_PATH}")
    df = pd.read_csv(CSV_PATH)
    df = df.dropna(subset=["LAT", "LON"])
    
    # Compute surface elevation = GPS Altitude - Range to top of ice
    df["z_2017"] = df.apply(
        lambda row: float(row["ELEVATION"] - row["SURFACE"]) 
        if row["ELEVATION"] > -9000 and row["SURFACE"] > -9000 else np.nan, 
        axis=1
    )
    df = df.dropna(subset=["z_2017"])
    return df


def run_dem_analysis():
    print("=== Launching DEM 2022 & Surface Elevation Analysis ===")
    
    # 1. Check file existence
    if not os.path.exists(TIF_PATH) or not os.path.exists(SHP_PATH):
        print("Error: Missing DEM TIFF or boundary Shapefile in data/DEM_2022.")
        return
        
    # 2. Load boundary shapefile
    print("Loading glacier boundary shapefile...")
    gdf = gpd.read_file(SHP_PATH)
    
    # 3. Load and plot DEM
    print("Opening 2022 DEM TIFF...")
    with rasterio.open(TIF_PATH) as src:
        dem_crs = src.crs.to_string()
        print(f"DEM CRS: {dem_crs}")
        
        # Read downsampled DEM for visualization
        factor = 10
        dem_data = src.read(1, out_shape=(src.height // factor, src.width // factor))
        dem_data = np.where(dem_data == src.nodata, np.nan, dem_data)
        
        # Get bounds of downsampled image
        dem_extent = [src.bounds.left, src.bounds.right, src.bounds.bottom, src.bounds.top]
        
        # Plot 2022 DEM Topography
        print("Generating DEM topography map...")
        fig, ax = plt.subplots(figsize=(7, 6))
        im = ax.imshow(dem_data, cmap="terrain", extent=dem_extent, origin="upper")
        gdf.boundary.plot(ax=ax, color="black", linewidth=1.2, label="Glacier Boundary")
        ax.set_title("Penny Ice Cap 2022: Digital Elevation Model (DEM)", fontsize=10, fontweight="bold")
        ax.set_xlabel("Easting (meters, North America Albers)", fontsize=8)
        ax.set_ylabel("Northing (meters, North America Albers)", fontsize=8)
        ax.grid(True, linestyle="--", alpha=0.5)
        fig.colorbar(im, ax=ax, label="Elevation (m above sea level)")
        
        dem_map_path = os.path.join(BASE_DIR, "dem_2022_topography.png")
        fig.savefig(dem_map_path, dpi=120, bbox_inches="tight")
        plt.close(fig)
        print(f"Saved DEM map to: {dem_map_path}")
        
        # 4. Compare with 2017 MCoRDS Surface Elevation
        print("Loading 2017 MCoRDS flight tracks...")
        m_df = load_mcords_surface_data()
        
        # Project 2017 flight points (Lat/Lon) to DEM's CRS
        print("Projecting 2017 points to DEM's CRS...")
        xs, ys = transform('EPSG:4326', src.crs, m_df['LON'].tolist(), m_df['LAT'].tolist())
        m_df['x_dem'] = xs
        m_df['y_dem'] = ys
        
        # Filter points within DEM bounds
        valid_idx = (
            (m_df['x_dem'] >= src.bounds.left) & (m_df['x_dem'] <= src.bounds.right) &
            (m_df['y_dem'] >= src.bounds.bottom) & (m_df['y_dem'] <= src.bounds.top)
        )
        comp_df = m_df[valid_idx].copy()
        
        # Extract DEM values at these coordinates
        print(f"Sampling 2022 DEM elevations at {len(comp_df)} flight points...")
        coords = [(x, y) for x, y in zip(comp_df['x_dem'], comp_df['y_dem'])]
        comp_df['z_2022'] = [val[0] for val in src.sample(coords)]
        
        # Filter out NoData samples (-9999.0)
        comp_df = comp_df[comp_df['z_2022'] != src.nodata]
        print(f"Extracted valid comparisons for {len(comp_df)} points.")
        
        if comp_df.empty:
            print("Error: No overlapping coordinates between MCoRDS track and DEM.")
            return
            
        # Calculate elevation change dz = z_2022 - z_2017 (in meters)
        comp_df['dz'] = comp_df['z_2022'] - comp_df['z_2017']
        
        # Exclude extreme outliers (greater than +/- 100 meters, which are likely errors in radar/DEM matching)
        comp_df = comp_df[(comp_df['dz'] >= -100.0) & (comp_df['dz'] <= 100.0)]
        print(f"Cleaned comparisons count (excluding outliers): {len(comp_df)}")
        
        # Compute Stats
        mean_dz = comp_df['dz'].mean()
        median_dz = comp_df['dz'].median()
        std_dz = comp_df['dz'].std()
        pearson_r = comp_df['z_2017'].corr(comp_df['z_2022'])
        rmse = np.sqrt(np.mean(comp_df['dz']**2))
        
        summary_text = f"""=== DEM 2022 vs MCoRDS 2017 Surface Comparison ===
Comparison Points: {len(comp_df)}
Mean Elevation Change (dz = z_2022 - z_2017): {mean_dz:.3f} meters
Median Elevation Change: {median_dz:.3f} meters
Standard Deviation of dz: {std_dz:.3f} meters
Root Mean Squared Error (RMSE): {rmse:.3f} meters
Pearson Correlation Coefficient: {pearson_r:.5f}
"""
        print(summary_text)
        
        # Save summary to file
        txt_out_path = os.path.join(BASE_DIR, "dem_analysis_summary.txt")
        with open(txt_out_path, "w") as f:
            f.write(summary_text)
        print(f"Saved text report to: {txt_out_path}")
        
        # Save matched table to CSV for further usage
        csv_out_path = os.path.join(DATA_DIR, "dem_comparison_points.csv")
        comp_df[['LAT', 'LON', 'z_2017', 'z_2022', 'dz']].to_csv(csv_out_path, index=False)
        print(f"Saved comparison CSV to: {csv_out_path}")
        
        # Plot Elevation Change Map
        print("Generating elevation change map along flight tracks...")
        fig, ax = plt.subplots(figsize=(6, 5))
        sc = ax.scatter(comp_df['LON'], comp_df['LAT'], c=comp_df['dz'], cmap="RdBu", vmin=-20, vmax=20, s=2, alpha=0.8)
        ax.set_title("Penny Ice Cap: Surface Elevation Change (dz = z_2022 - z_2017)\nOperation IceBridge tracks vs 2022 DEM", fontsize=9, fontweight="bold")
        ax.set_xlabel("Longitude (deg W)", fontsize=8)
        ax.set_ylabel("Latitude (deg N)", fontsize=8)
        ax.grid(True, linestyle="--", alpha=0.5)
        cbar = fig.colorbar(sc, ax=ax, shrink=0.8)
        cbar.set_label("Elevation Change dz (meters)", fontsize=8)
        
        change_map_path = os.path.join(BASE_DIR, "glacier_elevation_change_map.png")
        fig.savefig(change_map_path, dpi=120, bbox_inches="tight")
        plt.close(fig)
        print(f"Saved elevation change map to: {change_map_path}")
        
        # Plot Scatter Plot Comparison
        print("Generating elevation comparison scatter plot...")
        fig, ax = plt.subplots(figsize=(6, 5))
        ax.scatter(comp_df['z_2017'], comp_df['z_2022'], color="blue", s=1, alpha=0.4, label="Track points")
        # 1:1 line
        lims = [
            min(comp_df['z_2017'].min(), comp_df['z_2022'].min()),
            max(comp_df['z_2017'].max(), comp_df['z_2022'].max())
        ]
        ax.plot(lims, lims, "r--", linewidth=1.5, label="1:1 line (no change)")
        ax.set_xlim(lims)
        ax.set_ylim(lims)
        ax.set_title("Elevation Comparison: 2017 MCoRDS vs 2022 DEM", fontsize=10, fontweight="bold")
        ax.set_xlabel("2017 Surface Elevation (m above sea level)", fontsize=8)
        ax.set_ylabel("2022 DEM Elevation (m above sea level)", fontsize=8)
        ax.legend(loc="upper left", fontsize=8)
        ax.grid(True, linestyle="--", alpha=0.5)
        
        scatter_path = os.path.join(BASE_DIR, "glacier_elevation_comparison_scatter.png")
        fig.savefig(scatter_path, dpi=120, bbox_inches="tight")
        plt.close(fig)
        print(f"Saved scatter plot to: {scatter_path}")


if __name__ == "__main__":
    run_dem_analysis()

"""
Validation analysis script for Penny Ice Cap comparing MCoRDS 2017
surface elevation with IceBridge ATM L2 2017 surface elevation at overlapping tracks.
"""
from __future__ import annotations
import os
import glob
import numpy as np
import pandas as pd
import geopandas as gpd
from rasterio.warp import transform
from scipy.spatial import cKDTree
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
DATA_DIR = os.path.join(BASE_DIR, "data")
DEM_DIR = os.path.join(DATA_DIR, "DEM_2015-2016")
SHP_PATH = os.path.join(DEM_DIR, "Name_Penny Ice Cap.shp")
CSV_PATH = os.path.join(DATA_DIR, "IRMCR2_20170428_03_raw_data.csv")
ATM_DIR = os.path.join(DATA_DIR, "IceBridge ATM L2 Icessn Elevation, Slope, and Roughness V002")


def run_atm_analysis():
    print("=== Starting Penny Ice Cap MCoRDS 2017 vs ATM 2017 Comparison ===")
    
    # 1. Load MCoRDS 2017 baseline
    print("Loading MCoRDS 2017 baseline data...")
    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(f"Missing MCoRDS CSV at {CSV_PATH}")
    df_17 = pd.read_csv(CSV_PATH)
    df_17 = df_17.dropna(subset=["LAT", "LON"])
    
    # z_surf = ELEVATION - SURFACE (ellipsoidal height)
    df_17["z_surf"] = df_17.apply(
        lambda row: float(row["ELEVATION"] - row["SURFACE"]) 
        if row["ELEVATION"] > -9000 and row["SURFACE"] > -9000 else np.nan, 
        axis=1
    )
    df_17 = df_17.dropna(subset=["z_surf"]).copy()
    df_17["ice_thickness"] = df_17["THICK"].apply(lambda val: float(val) if val > 0 else np.nan)
    
    # Project to Albers for KDTree queries
    print("Projecting MCoRDS points...")
    xs_17, ys_17 = transform('EPSG:4326', 'ESRI:102008', df_17['LON'].tolist(), df_17['LAT'].tolist())
    df_17['x_proj'] = xs_17
    df_17['y_proj'] = ys_17
    tree_17 = cKDTree(np.column_stack((xs_17, ys_17)))
    
    # 2. Load ATM 2017 files (ignoring smooth files)
    atm_files = [f for f in glob.glob(os.path.join(ATM_DIR, "**/*.csv"), recursive=True) if '_smooth' not in f]
    print(f"Found {len(atm_files)} raw ATM files.")
    
    all_atm = []
    for fp in atm_files:
        try:
            df_atm = pd.read_csv(fp)
            df_atm.columns = [c.strip() for c in df_atm.columns] # Strip spaces
            df_atm = df_atm.dropna(subset=['Longitude(deg)', 'Latitude(deg)', 'WGS84_Ellipsoid_Height(m)'])
            all_atm.append(df_atm)
        except Exception as e:
            print(f"Error parsing {fp}: {e}")
            
    if not all_atm:
        print("Error: No valid ATM data loaded.")
        return
        
    df_atm_all = pd.concat(all_atm, ignore_index=True)
    print(f"Total ATM points: {len(df_atm_all)}")
    
    # Project ATM coordinates
    xs_atm, ys_atm = transform('EPSG:4326', 'ESRI:102008', df_atm_all['Longitude(deg)'].tolist(), df_atm_all['Latitude(deg)'].tolist())
    df_atm_all['x_proj'] = xs_atm
    df_atm_all['y_proj'] = ys_atm
    
    # Filter non-finite projected values
    valid_mask = np.isfinite(df_atm_all['x_proj']) & np.isfinite(df_atm_all['y_proj'])
    df_atm_all = df_atm_all[valid_mask].copy()
    
    # 3. Co-locate ATM and MCoRDS tracks (100m search radius)
    print("Co-locating ATM tracks with MCoRDS baseline...")
    dists, indices = tree_17.query(np.column_stack((df_atm_all['x_proj'], df_atm_all['y_proj'])))
    df_atm_all['dist_to_17'] = dists
    df_atm_all['idx_17'] = indices
    
    # Filter overlap
    overlap = df_atm_all[df_atm_all['dist_to_17'] <= 100.0].copy()
    if overlap.empty:
        print("Error: No overlapping coordinates found between ATM and MCoRDS.")
        return
        
    corr_17 = df_17.iloc[overlap['idx_17']].copy().reset_index(drop=True)
    overlap = overlap.reset_index(drop=True)
    
    # dz = ATM (laser) - MCoRDS (radar)
    overlap['dz'] = overlap['WGS84_Ellipsoid_Height(m)'] - corr_17['z_surf']
    
    # Filter extreme outliers
    clean_mask = (overlap['dz'] >= -100.0) & (overlap['dz'] <= 100.0)
    overlap = overlap[clean_mask].copy()
    corr_17 = corr_17[clean_mask].copy()
    
    mean_dz = overlap['dz'].mean()
    median_dz = overlap['dz'].median()
    std_dz = overlap['dz'].std()
    rmse = np.sqrt(np.mean(overlap['dz']**2))
    
    summary_text = f"""=== ATM 2017 vs MCoRDS 2017 Co-Location Validation ===
Co-Located Overlapping Points: {len(overlap)}
Mean Elevation Difference (dz = z_atm - z_mcoords): {mean_dz:.3f} meters
Median Elevation Difference: {median_dz:.3f} meters
Standard Deviation of dz: {std_dz:.3f} meters
Root Mean Squared Error (RMSE): {rmse:.3f} meters
"""
    print(summary_text)
    
    # Save text summary
    summary_path = os.path.join(DATA_DIR, "atm_validation_summary.txt")
    with open(summary_path, "w") as f:
        f.write(summary_text)
    print(f"Saved report to: {summary_path}")
    
    # Load boundary Shapefile for overlays
    gdf = gpd.read_file(SHP_PATH) if os.path.exists(SHP_PATH) else None
    
    # Plot 1: atm_validation_histogram.png (Histogram of dz)
    print("Generating dz distribution histogram (atm_validation_histogram.png)...")
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.hist(overlap['dz'], bins=50, color='lightgreen', edgecolor='black', alpha=0.8)
    ax.axvline(median_dz, color='red', linestyle='--', linewidth=1.5, label=f"Median dz: {median_dz:+.2f}m")
    ax.set_title("Penny Ice Cap 2017: ATM L2 vs MCoRDS L2\nElevation Difference Distribution", fontsize=10, fontweight="bold")
    ax.set_xlabel("Elevation Difference (z_atm - z_mcoords, meters)", fontsize=9)
    ax.set_ylabel("Frequency (Count)", fontsize=9)
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend(fontsize=9)
    
    plot1_path = os.path.join(BASE_DIR, "atm_validation_histogram.png")
    fig.savefig(plot1_path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved validation histogram plot to: {plot1_path}")
    
    # Plot 2: atm_validation_map.png (Spatial differences)
    print("Generating difference map (atm_validation_map.png)...")
    fig, ax = plt.subplots(figsize=(6, 5))
    sc = ax.scatter(overlap['x_proj'], overlap['y_proj'], c=overlap['dz'], cmap="RdBu", vmin=-10, vmax=10, s=2, alpha=0.8)
    if gdf is not None:
        gdf.boundary.plot(ax=ax, color="black", linewidth=1.5)
    ax.set_title("Penny Ice Cap 2017: Spatial Elevation Difference\n(z_atm minus z_mcoords along track)", fontsize=9, fontweight="bold")
    ax.set_xlabel("Easting (m, North America Albers)", fontsize=8)
    ax.set_ylabel("Northing (m, North America Albers)", fontsize=8)
    ax.grid(True, linestyle="--", alpha=0.5)
    cbar = fig.colorbar(sc, ax=ax, shrink=0.8)
    cbar.set_label("z_atm - z_mcoords (meters)", fontsize=8)
    
    plot2_path = os.path.join(BASE_DIR, "atm_validation_map.png")
    fig.savefig(plot2_path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved difference map to: {plot2_path}")
    
    # Plot 3: atm_validation_thickness.png (Thickness along overlapping tracks)
    print("Generating thickness map (atm_validation_thickness.png)...")
    fig, ax = plt.subplots(figsize=(6, 5))
    sc = ax.scatter(corr_17['x_proj'], corr_17['y_proj'], c=corr_17['ice_thickness'], cmap="Blues", s=2, alpha=0.8)
    if gdf is not None:
        gdf.boundary.plot(ax=ax, color="black", linewidth=1.5)
    ax.set_title("Penny Ice Cap 2017: MCoRDS Ice Thickness\nat Overlapping ATM Tracks", fontsize=9, fontweight="bold")
    ax.set_xlabel("Easting (m, North America Albers)", fontsize=8)
    ax.set_ylabel("Northing (m, North America Albers)", fontsize=8)
    ax.grid(True, linestyle="--", alpha=0.5)
    cbar = fig.colorbar(sc, ax=ax, shrink=0.8)
    cbar.set_label("Ice Thickness (meters)", fontsize=8)
    
    plot3_path = os.path.join(BASE_DIR, "atm_validation_thickness.png")
    fig.savefig(plot3_path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved thickness map to: {plot3_path}")
    print("=== ATM Validation Comparison Complete ===")


if __name__ == "__main__":
    run_atm_analysis()

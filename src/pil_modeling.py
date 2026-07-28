"""
Pleistocene Ice Layer (PIL) modeling and visualization script.
Computes the estimated PIL thickness along MCoRDS flight tracks and solves the
Shallow Ice Approximation (SIA) velocity profile showing basal shear enhancement.
"""
from __future__ import annotations
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
CSV_PATH = os.path.join(BASE_DIR, "IRMCR2_20170428_03_raw_data.csv")


def load_data() -> pd.DataFrame:
    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(f"Missing primary data file at {CSV_PATH}")
    df = pd.read_csv(CSV_PATH)
    df = df.dropna(subset=["LAT", "LON"])
    df["ice_thickness"] = df["THICK"].apply(lambda val: float(val) if val > 0 else 0.0)
    
    # Compute surface elevation
    df["surface_elevation"] = df.apply(
        lambda row: float(row["ELEVATION"] - row["SURFACE"]) 
        if row["ELEVATION"] > -9000 and row["SURFACE"] > -9000 else 0.0, 
        axis=1
    )
    return df


def estimate_pil_thickness(thick: float) -> float:
    """Estimates Pleistocene Ice Layer (PIL) thickness as a basal layer.
    Typical models limit PIL to deep ice (e.g. thickness > 150m) and cap it at 80m."""
    if thick > 150.0:
        return min(0.12 * thick, 80.0)
    return 0.0


def compute_sia_velocity(H: float, Hp: float, E: float = 3.5) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Computes SIA vertical velocity profile relative to the bed.
    H: total ice thickness (meters)
    Hp: Pleistocene Ice Layer thickness (meters)
    E: enhancement factor (softness multiplier, typical 3.1 - 3.5)
    Returns:
    - z: vertical grid from bed (0) to surface (H)
    - u_with_pil: velocity profile with PIL
    - u_without_pil: velocity profile without PIL (E=1)
    """
    n = 3
    A0 = 1e-16  # base ice fluidity (Pa^-3 yr^-1)
    rho = 917.0  # ice density (kg/m^3)
    g = 9.81  # gravity (m/s^2)
    slope = 0.02  # surface slope angle (radians)
    
    factor = 2 * A0 * (rho * g * slope) ** n
    z = np.linspace(0, H, 200)
    
    # 1. Base profile (no PIL, E=1 everywhere)
    u_no = factor * (H**(n+1) - (H - z)**(n+1)) / (n+1)
    
    # 2. Profile with PIL (E enhancement for z <= Hp)
    u_pil = np.zeros_like(z)
    for i, zi in enumerate(z):
        if zi <= Hp:
            # Inside the PIL layer (enhanced fluidity E * A0)
            u_pil[i] = E * factor * (H**(n+1) - (H - zi)**(n+1)) / (n+1)
        else:
            # Above the PIL layer (normal fluidity A0)
            # Velocity at transition height Hp
            u_transition = E * factor * (H**(n+1) - (H - Hp)**(n+1)) / (n+1)
            # Added velocity above Hp
            u_above = factor * ((H - Hp)**(n+1) - (H - zi)**(n+1)) / (n+1)
            u_pil[i] = u_transition + u_above
            
    # Normalize to surface velocity of the base case for visualization
    u_surf_no = u_no[-1]
    return z, u_pil / u_surf_no, u_no / u_surf_no


def run_pil_analysis():
    print("Loading flight track data...")
    df = load_data()
    
    # Compute PIL thickness along tracks
    print("Estimating Pleistocene Ice Layer (PIL) thickness...")
    df["pil_thickness"] = df["ice_thickness"].apply(estimate_pil_thickness)
    
    # Generate Map of PIL distribution
    print("Plotting PIL distribution map...")
    fig, ax = plt.subplots(figsize=(6, 5))
    sc = ax.scatter(df["LON"], df["LAT"], c=df["pil_thickness"], cmap="Purples", s=2, alpha=0.8)
    ax.set_title("Estimated Pleistocene Ice Layer (PIL) Thickness\nPenny Ice Cap 2017", fontsize=10, fontweight="bold")
    ax.set_xlabel("Longitude (deg W)", fontsize=8)
    ax.set_ylabel("Latitude (deg N)", fontsize=8)
    ax.grid(True, linestyle="--", alpha=0.5)
    cbar = fig.colorbar(sc, ax=ax, shrink=0.8)
    cbar.set_label("PIL Thickness (meters)", fontsize=8)
    
    map_path = os.path.join(BASE_DIR, "pil_distribution_map.png")
    fig.savefig(map_path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved PIL map to: {map_path}")
    
    # Find a point with thick ice to plot the velocity profile
    thick_point = df[df["ice_thickness"] > 500].iloc[0]
    H = float(thick_point["ice_thickness"])
    Hp = estimate_pil_thickness(H)
    print(f"Selected profile location: Lat {thick_point['LAT']:.4f}, Lon {thick_point['LON']:.4f}")
    print(f"Total Ice Thickness H = {H:.1f} m, Estimated PIL Thickness Hp = {Hp:.1f} m")
    
    # Compute velocity profiles
    z, u_pil, u_no = compute_sia_velocity(H, Hp, E=3.5)
    
    # Plot Velocity Profile
    print("Plotting velocity profile comparison...")
    fig, ax = plt.subplots(figsize=(5, 6))
    ax.plot(u_no, z, "k--", label="Holocene Ice Only (E=1)")
    ax.plot(u_pil, z, "b-", label="With Basal PIL Layer (E=3.5)")
    
    # Highlight the PIL layer
    ax.axhspan(0, Hp, color="purple", alpha=0.15, label=f"Pleistocene Ice Layer (Hp={Hp:.1f}m)")
    ax.axhline(Hp, color="purple", linestyle=":", alpha=0.7)
    
    ax.set_title("Vertical Velocity Profile & Shear Zones\nPenny Ice Cap Deep Ice Site", fontsize=10, fontweight="bold")
    ax.set_xlabel("Normalized Velocity (u / u_surface_base)", fontsize=8)
    ax.set_ylabel("Height Above Bed (meters)", fontsize=8)
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(True, linestyle="--", alpha=0.5)
    
    profile_path = os.path.join(BASE_DIR, "pil_velocity_profile.png")
    fig.savefig(profile_path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved velocity profile plot to: {profile_path}")


if __name__ == "__main__":
    run_pil_analysis()

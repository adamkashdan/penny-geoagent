"""
Geospatial tool functions for the Penny Ice Cap 2017 dataset.
These functions are exposed to the Gemini API via function-calling.
They read the MCoRDS L2 flight track CSV data and return LLM-friendly summaries or maps.
"""
from __future__ import annotations
import os
import io
import base64
import yaml
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from typing import Optional

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
CSV_PATH = os.path.join(BASE_DIR, "IRMCR2_20170428_03_raw_data.csv")

with open(os.path.join(BASE_DIR, "semantic_layer.yaml")) as f:
    SEMANTIC_LAYER = yaml.safe_load(f)

# Global cache for data
_DF_CACHE: Optional[pd.DataFrame] = None


def _load_data() -> pd.DataFrame:
    global _DF_CACHE
    if _DF_CACHE is not None:
        return _DF_CACHE

    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(f"Missing primary data file at {CSV_PATH}")

    # Load raw MCoRDS data
    df = pd.read_csv(CSV_PATH)
    
    # Filter out rows with invalid coordinates
    df = df.dropna(subset=["LAT", "LON"])
    
    # Compute derived variables
    # Filter out nodata flags (-9999.0)
    df["ice_thickness"] = df["THICK"].apply(lambda val: float(val) if val > -9000 else np.nan)
    
    # Surface Elevation = Elevation - Surface Range (distance from plane to ice top)
    df["surface_elevation"] = df.apply(
        lambda row: float(row["ELEVATION"] - row["SURFACE"]) 
        if row["ELEVATION"] > -9000 and row["SURFACE"] > -9000 else np.nan, 
        axis=1
    )
    
    # Bedrock Elevation = Elevation - Bottom Range (distance from plane to bedrock base)
    df["bedrock_elevation"] = df.apply(
        lambda row: float(row["ELEVATION"] - row["BOTTOM"]) 
        if row["ELEVATION"] > -9000 and row["BOTTOM"] > -9000 else np.nan, 
        axis=1
    )

    _DF_CACHE = df
    return df


def list_datasets() -> dict:
    """Returns the semantic layer's dataset catalog -- what variables are available to query."""
    return {
        name: {
            "label": d["label"],
            "unit": d["unit"],
            "description": d["description"].strip(),
        }
        for name, d in SEMANTIC_LAYER["datasets"].items()
    }


def query_point_data(lat: float, lon: float) -> dict:
    """Finds the nearest radar measurement to a given lat/lon point and returns its physical values."""
    df = _load_data()
    if df.empty:
        return {"error": "Dataset is empty."}
        
    # Calculate distance in meters using flat-earth approximation near 67 deg N
    lat_rad = np.radians(lat)
    dy = (df["LAT"] - lat) * 111120.0
    dx = (df["LON"] - lon) * 111120.0 * np.cos(lat_rad)
    dist = np.sqrt(dx**2 + dy**2)
    
    idx = dist.idxmin()
    row = df.loc[idx]
    distance_m = float(dist.loc[idx])
    
    # If the closest point is too far away (e.g. > 100km), warn the user
    warning = None
    if distance_m > 100000:
        warning = f"Note: The nearest track point is quite far away ({distance_m/1000:.1f} km)."

    return {
        "query_lat": lat,
        "query_lon": lon,
        "nearest_lat": float(row["LAT"]),
        "nearest_lon": float(row["LON"]),
        "distance_meters": distance_m,
        "ice_thickness": float(row["ice_thickness"]) if not np.isnan(row["ice_thickness"]) else "No Data",
        "surface_elevation": float(row["surface_elevation"]) if not np.isnan(row["surface_elevation"]) else "No Data",
        "bedrock_elevation": float(row["bedrock_elevation"]) if not np.isnan(row["bedrock_elevation"]) else "No Data",
        "seconds_of_day": float(row["UTCTIMESOD"]),
        "frame_id": int(row["FRAME"]),
        "quality_flag": int(row["QUALITY"]) if not np.isnan(row["QUALITY"]) else "Unknown",
        "warning": warning
    }


def compute_zonal_statistics(dataset: str, bbox: list) -> dict:
    """Computes summary statistics (min/max/mean/std) of a variable within a bounding box [west, south, east, north]."""
    if dataset not in SEMANTIC_LAYER["datasets"]:
        return {"error": f"Unknown dataset variable '{dataset}'."}
        
    df = _load_data()
    west, south, east, north = bbox
    
    # Filter points inside bounding box
    subset = df[(df["LON"] >= west) & (df["LON"] <= east) & (df["LAT"] >= south) & (df["LAT"] <= north)]
    
    if subset.empty:
        return {"error": "No flight track points found inside this bounding box."}
        
    values = subset[dataset].dropna()
    if values.empty:
        return {"error": "No valid data values for this variable within the bounding box."}
        
    unit = SEMANTIC_LAYER["datasets"][dataset]["unit"]
    return {
        "dataset": dataset,
        "bbox": bbox,
        "unit": unit,
        "min": float(np.min(values)),
        "max": float(np.max(values)),
        "mean": float(np.mean(values)),
        "std": float(np.std(values)),
        "point_count": int(values.size),
    }


def generate_map_image(dataset: str, bbox: Optional[list] = None) -> dict:
    """Renders a map scatter plot of flight tracks colored by the chosen variable, optionally cropped to bbox.
    Returns a base64-encoded PNG image."""
    if dataset not in SEMANTIC_LAYER["datasets"]:
        return {"error": f"Unknown dataset variable '{dataset}'."}
        
    df = _load_data()
    
    # Filter to bbox if provided, otherwise use entire region bbox
    if bbox:
        west, south, east, north = bbox
    else:
        west, south, east, north = SEMANTIC_LAYER["region"]["bbox"]
        
    subset = df[(df["LON"] >= west) & (df["LON"] <= east) & (df["LAT"] >= south) & (df["LAT"] <= north)].copy()
    
    if subset.empty:
        return {"error": "No data points found in this region to map."}
        
    # Drop rows with NaN in the selected variable
    subset = subset.dropna(subset=[dataset])
    if subset.empty:
        return {"error": "No valid data to plot in this region."}

    label = SEMANTIC_LAYER["datasets"][dataset]["label"]
    unit = SEMANTIC_LAYER["datasets"][dataset]["unit"]

    # Choose colormap based on variable type
    if dataset == "ice_thickness":
        cmap = "Blues"
    elif dataset == "surface_elevation":
        cmap = "terrain"
    else:
        cmap = "BrBG"  # Brown-Green for bedrock

    fig, ax = plt.subplots(figsize=(6, 5))
    sc = ax.scatter(subset["LON"], subset["LAT"], c=subset[dataset], cmap=cmap, s=2, alpha=0.8)
    
    ax.set_title(f"Penny Ice Cap 2017: {label}\n({unit})", fontsize=10, fontweight="bold")
    ax.set_xlabel("Longitude (deg W)", fontsize=8)
    ax.set_ylabel("Latitude (deg N)", fontsize=8)
    ax.grid(True, linestyle="--", alpha=0.5)
    
    # Colorbar
    cbar = fig.colorbar(sc, ax=ax, shrink=0.8)
    cbar.set_label(f"{label} ({unit})", fontsize=8)
    
    # Format axes slightly
    ax.tick_params(labelsize=8)
    
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode("utf-8")
    
    return {"dataset": dataset, "image_base64": b64, "format": "png"}


def compare_variables(dataset_a: str, dataset_b: str, bbox: list) -> dict:
    """Compares values of two variables over the same bounding box and calculates their Pearson correlation."""
    if dataset_a not in SEMANTIC_LAYER["datasets"] or dataset_b not in SEMANTIC_LAYER["datasets"]:
        return {"error": "One or both variables are unrecognized."}
        
    df = _load_data()
    west, south, east, north = bbox
    
    subset = df[(df["LON"] >= west) & (df["LON"] <= east) & (df["LAT"] >= south) & (df["LAT"] <= north)]
    if subset.empty:
        return {"error": "No data points found inside this bounding box."}
        
    subset = subset[[dataset_a, dataset_b]].dropna()
    if len(subset) < 3:
        return {"error": "Not enough overlapping valid data points in the bounding box to compute correlation."}
        
    vals_a = subset[dataset_a]
    vals_b = subset[dataset_b]
    
    corr_coef = float(np.corrcoef(vals_a, vals_b)[0, 1])
    
    return {
        "bbox": bbox,
        "point_count": len(subset),
        dataset_a: {
            "mean": float(np.mean(vals_a)),
            "unit": SEMANTIC_LAYER["datasets"][dataset_a]["unit"]
        },
        dataset_b: {
            "mean": float(np.mean(vals_b)),
            "unit": SEMANTIC_LAYER["datasets"][dataset_b]["unit"]
        },
        "pearson_correlation_coefficient": corr_coef,
        "relationship_description": _describe_correlation(corr_coef, dataset_a, dataset_b)
    }


def _describe_correlation(r: float, var_a: str, var_b: str) -> str:
    if np.isnan(r):
        return "No relationship could be computed."
    strength = "strong" if abs(r) > 0.7 else "moderate" if abs(r) > 0.4 else "weak" if abs(r) > 0.1 else "negligible"
    direction = "positive" if r > 0 else "negative"
    
    if strength == "negligible":
        return f"There is virtually no correlation (r = {r:.2f}) between {var_a} and {var_b}."
    else:
        return f"There is a {strength} {direction} correlation (r = {r:.2f}) between {var_a} and {var_b}."


# --- Tool schema definitions for Gemini Function Calling -----------------

TOOL_DEFINITIONS = [
    {
        "name": "list_datasets",
        "description": "List all available Penny Ice Cap variables (datasets) with their descriptions and units. Call this first if unsure what variables are available.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "query_point_data",
        "description": "Retrieve the radar-measured ice thickness, surface elevation, and bedrock elevation at the nearest flight track point to a specified latitude/longitude.",
        "input_schema": {
            "type": "object",
            "properties": {
                "lat": {"type": "number", "description": "Latitude coordinate of the query point"},
                "lon": {"type": "number", "description": "Longitude coordinate of the query point"},
            },
            "required": ["lat", "lon"],
        },
    },
    {
        "name": "compute_zonal_statistics",
        "description": "Compute statistical metrics (min/max/mean/std) for a variable within a bounding box [west, south, east, north].",
        "input_schema": {
            "type": "object",
            "properties": {
                "dataset": {"type": "string", "description": "Variable name, e.g. 'ice_thickness', 'surface_elevation', 'bedrock_elevation'"},
                "bbox": {"type": "array", "items": {"type": "number"}, "minItems": 4, "maxItems": 4, "description": "[west, south, east, north] coordinates"},
            },
            "required": ["dataset", "bbox"],
        },
    },
    {
        "name": "generate_map_image",
        "description": "Generate a scatter plot map of flight tracks colored by the values of a variable, optionally cropped to a bounding box. Returns base64 PNG.",
        "input_schema": {
            "type": "object",
            "properties": {
                "dataset": {"type": "string", "description": "Variable name, e.g. 'ice_thickness', 'surface_elevation', 'bedrock_elevation'"},
                "bbox": {"type": "array", "items": {"type": "number"}, "minItems": 4, "maxItems": 4, "description": "Optional bounding box [west, south, east, north] to zoom in"},
            },
            "required": ["dataset"],
        },
    },
    {
        "name": "compare_variables",
        "description": "Compare the spatial correlation between two variables over the same bounding box.",
        "input_schema": {
            "type": "object",
            "properties": {
                "dataset_a": {"type": "string", "description": "First variable name, e.g. 'surface_elevation'"},
                "dataset_b": {"type": "string", "description": "Second variable name, e.g. 'ice_thickness'"},
                "bbox": {"type": "array", "items": {"type": "number"}, "minItems": 4, "maxItems": 4, "description": "[west, south, east, north] bounding box"},
            },
            "required": ["dataset_a", "dataset_b", "bbox"],
        },
    },
]

TOOL_FUNCTIONS = {
    "list_datasets": lambda **kwargs: list_datasets(),
    "query_point_data": query_point_data,
    "compute_zonal_statistics": compute_zonal_statistics,
    "generate_map_image": generate_map_image,
    "compare_variables": compare_variables,
}

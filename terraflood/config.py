"""
TerraFlood Hackathon Control Panel
==================================
Single source of truth for runtime variables, satellite ingestion parameters,
geospatial paths, and scientific filtering thresholds.
"""

import os
from pathlib import Path
from typing import Tuple, List, Dict

# -----------------------------------------------------------------------------
# Base Directories & Storage
# -----------------------------------------------------------------------------
PACKAGE_DIR = Path(__file__).resolve().parent
BASE_DIR = PACKAGE_DIR.parent

DATA_DIR = Path(os.getenv("TERRAFLOOD_DATA_DIR", PACKAGE_DIR / "data"))
CACHE_DIR = Path(os.getenv("TERRAFLOOD_CACHE_DIR", PACKAGE_DIR / "cache"))
EXPORTS_DIR = Path(os.getenv("TERRAFLOOD_EXPORTS_DIR", PACKAGE_DIR / "exports"))

# Ensure runtime directories exist
CACHE_DIR.mkdir(parents=True, exist_ok=True)
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Local Vector Dataset Paths (HDX Admin Boundaries & OSM Roads)
# -----------------------------------------------------------------------------
ROADS_DIR = DATA_DIR / "roads"
ADMIN_DIR = DATA_DIR / "admin"

_possible_road_files = [
    ROADS_DIR / "hotosm_npl_roads_lines.shp",
    ROADS_DIR / "roads_lines.shp",
]
ROADS_SHP_PATH = next((p for p in _possible_road_files if p.exists()), _possible_road_files[0])

_possible_admin_files = [
    ADMIN_DIR / "31Adist_polbnda_adm4_MoFALD_HRRP_wgs84.shp",
    ADMIN_DIR / "31adist_polbnda_adm4_mofald_hrrp_wgs84.shp",
]
ADMIN_SHP_PATH = next((p for p in _possible_admin_files if p.exists()), _possible_admin_files[0])

# -----------------------------------------------------------------------------
# Area of Interest (AOI): Nepal Terai Flood Corridor
# -----------------------------------------------------------------------------
# Bounding box format: [min_lon, min_lat, max_lon, max_lat]
# Covers the high-risk floodplains of the Terai (Koshi, Narayani, Bagmati basins)
AOI_COORDINATES: List[float] = [84.0, 26.5, 87.5, 27.5]

# Center coordinates for Leaflet / Folium tactical map rendering [latitude, longitude]
MAP_DEFAULT_CENTER: List[float] = [27.0, 85.75]
MAP_DEFAULT_ZOOM: int = 9

# Metric coordinate reference system for Nepal (WGS 84 / UTM Zone 45N)
METRIC_CRS: str = "EPSG:32645"
GEOGRAPHIC_CRS: str = "EPSG:4326"

# -----------------------------------------------------------------------------
# Satellite Ingestion Temporal Windows
# -----------------------------------------------------------------------------
# Reference pre-flood baseline: Dry/stable monsoon shoulder window
PRE_FLOOD_WINDOW: Tuple[str, str] = ("2026-09-01", "2026-09-15")

# Post-flood event window: Peak inundation following monsoon cloudburst
POST_FLOOD_WINDOW: Tuple[str, str] = ("2026-09-26", "2026-09-29")

# -----------------------------------------------------------------------------
# Scientific Processing & Filtering Thresholds
# -----------------------------------------------------------------------------
# Sentinel-1 SAR VV Backscatter Difference threshold in decibels (dB)
SAR_BACKSCATTER_THRESHOLD_DB: float = 1.25

# Sentinel-2 Modified Normalized Difference Water Index (MNDWI)
OPTICAL_MAX_CLOUD_PERCENT: float = 20.0
MNDWI_WATER_THRESHOLD: float = 0.0

# JRC Global Surface Water occurrence filter (% threshold)
JRC_WATER_OCCURRENCE_THRESHOLD: int = 80

# Copernicus DEM GLO-30 slope cutoff in degrees
DEM_MAX_SLOPE_DEGREES: float = 5.0

# -----------------------------------------------------------------------------
# Population Ingestion: Global Human Settlement Layer (GHSL)
# -----------------------------------------------------------------------------
# JRC GHSL GHS-POP dataset (100m resolution global population grid)
GHSL_POPULATION_DATASET: str = "JRC/GHSL/P2023A/GHS_POP"
DEFAULT_POPULATION_RASTER: Path = CACHE_DIR / "ghsl_population_terai.tif"

# -----------------------------------------------------------------------------
# Infrastructure Criticality & Scoring Weights
# -----------------------------------------------------------------------------
HIGHWAY_CRITICALITY_WEIGHTS: Dict[str, float] = {
    "motorway": 3.5,
    "trunk": 3.0,
    "primary": 2.5,
    "secondary": 2.0,
    "tertiary": 1.5,
    "residential": 1.0,
    "unclassified": 1.0,
    "track": 0.8,
    "path": 0.5,
}
DEFAULT_ROAD_WEIGHT: float = 1.0

# -----------------------------------------------------------------------------
# System Execution & Fail-Safe Modes
# -----------------------------------------------------------------------------
GEE_PROJECT_ID: str = os.getenv("GEE_PROJECT_ID", "")
FALLBACK_MODE: bool = os.getenv("TERRAFLOOD_FALLBACK_MODE", "false").lower() in ("true", "1", "yes")

# Minimum flood polygon area to retain in vectorization (km²)
MIN_FLOOD_POLYGON_AREA_SQKM: float = 0.005

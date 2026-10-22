"""
TerraFlood Impact & Spatial Intersection Engine
===============================================
Performs high-performance vectorization, spatial overlays, road network
clipping, settlement exposure quantification, and GHSL zonal population
displacement accounting for Nepal's Terai corridor.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List

import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import shape, MultiPolygon, Polygon
import rasterio
from rasterio.features import shapes
from rasterio.mask import mask

from . import config

# Configure logging
logger = logging.getLogger("terraflood.impact")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [TerraFlood Impact] %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class VectorDataLoader:
    """Efficiently loads and spatially clips local OSM roads and HDX admin shapefiles."""

    @staticmethod
    def load_admin_boundaries(
        aoi_coords: List[float] = config.AOI_COORDINATES,
        shp_path: Optional[Path] = None,
    ) -> gpd.GeoDataFrame:
        """Loads and crops HDX MoFALD Village/District administrative shapefile."""
        path = shp_path or config.ADMIN_SHP_PATH
        if not path.exists():
            raise FileNotFoundError(f"Administrative boundaries shapefile not found at: {path}")

        min_lon, min_lat, max_lon, max_lat = aoi_coords
        logger.info(f"Loading administrative boundaries from {path} with AOI bbox filter...")

        # Read using bounding box for fast indexing
        gdf = gpd.read_file(path, bbox=(min_lon, min_lat, max_lon, max_lat))
        if gdf.crs is None:
            gdf = gdf.set_crs(config.GEOGRAPHIC_CRS)
        elif gdf.crs.to_string() != config.GEOGRAPHIC_CRS:
            gdf = gdf.to_crs(config.GEOGRAPHIC_CRS)

        # Ensure uniform column naming
        col_rename = {}
        if "HRRP_VNAME" in gdf.columns:
            col_rename["HRRP_VNAME"] = "settlement"
        elif "NAME" in gdf.columns:
            col_rename["NAME"] = "settlement"
        else:
            gdf["settlement"] = "Settlement_" + gdf.index.astype(str)

        if "HRRP_DNAME" in gdf.columns:
            col_rename["HRRP_DNAME"] = "district"
        elif "DISTRICT" in gdf.columns:
            col_rename["DISTRICT"] = "district"
        else:
            gdf["district"] = "Terai"

        if col_rename:
            gdf = gdf.rename(columns=col_rename)

        # Standardize total area in km²
        if "Sq_km" in gdf.columns:
            gdf["total_area_km2"] = pd.to_numeric(gdf["Sq_km"], errors="coerce")
        else:
            # Calculate from projected geometry
            gdf_proj = gdf.to_crs(config.METRIC_CRS)
            gdf["total_area_km2"] = gdf_proj.geometry.area / 1e6

        logger.info(f"Loaded {len(gdf)} administrative units within AOI.")
        return gdf

    @staticmethod
    def load_osm_roads(
        aoi_coords: List[float] = config.AOI_COORDINATES,
        shp_path: Optional[Path] = None,
    ) -> gpd.GeoDataFrame:
        """Loads and crops OpenStreetMap road network lines within the AOI."""
        path = shp_path or config.ROADS_SHP_PATH
        if not path.exists():
            raise FileNotFoundError(f"OSM roads shapefile not found at: {path}")

        min_lon, min_lat, max_lon, max_lat = aoi_coords
        logger.info(f"Loading road network from {path} with AOI bbox filter...")

        gdf = gpd.read_file(path, bbox=(min_lon, min_lat, max_lon, max_lat))
        if gdf.crs is None:
            gdf = gdf.set_crs(config.GEOGRAPHIC_CRS)
        elif gdf.crs.to_string() != config.GEOGRAPHIC_CRS:
            gdf = gdf.to_crs(config.GEOGRAPHIC_CRS)

        # Fill missing highway classifications
        if "highway" not in gdf.columns:
            gdf["highway"] = "unclassified"
        else:
            gdf["highway"] = gdf["highway"].fillna("unclassified")

        if "name" not in gdf.columns:
            gdf["name"] = "Unnamed Route"
        else:
            gdf["name"] = gdf["name"].fillna("Unnamed Route")

        logger.info(f"Loaded {len(gdf)} road segments within AOI.")
        return gdf


class ImpactEngine:
    """Executes spatial overlays, road severing quantification, and population displacement."""

    @staticmethod
    def polygonize_raster(
        raster_path: Path,
        min_area_km2: float = config.MIN_FLOOD_POLYGON_AREA_SQKM,
    ) -> gpd.GeoDataFrame:
        """
        Converts clean binary flood mask GeoTIFF into vectorized polygon GeoDataFrame,
        filtering out insignificant noise speckles.
        """
        if not raster_path.exists():
            raise FileNotFoundError(f"Flood raster not found at: {raster_path}")

        logger.info(f"Polygonizing flood mask: {raster_path}")
        with rasterio.open(raster_path) as src:
            image = src.read(1)
            transform = src.transform
            crs = src.crs or config.GEOGRAPHIC_CRS

            # Extract shapes where pixel == 1
            mask_arr = image == 1
            shape_gen = shapes(image, mask=mask_arr, transform=transform)

            polygon_list = []
            for geom, val in shape_gen:
                if val == 1:
                    poly = shape(geom)
                    if poly.is_valid and not poly.is_empty:
                        polygon_list.append(poly)

        if not polygon_list:
            logger.warning("No flood polygons detected in raster.")
            return gpd.GeoDataFrame(
                {"flood_id": [], "area_km2": []},
                geometry=[],
                crs=crs,
            )

        gdf = gpd.GeoDataFrame({"geometry": polygon_list}, crs=crs)
        gdf["flood_id"] = range(1, len(gdf) + 1)

        # Calculate exact area in km² using metric projection
        gdf_proj = gdf.to_crs(config.METRIC_CRS)
        gdf["area_km2"] = gdf_proj.geometry.area / 1e6

        # Filter out minor noise speckles
        clean_gdf = gdf[gdf["area_km2"] >= min_area_km2].copy()
        clean_gdf = clean_gdf.reset_index(drop=True)
        clean_gdf["flood_id"] = range(1, len(clean_gdf) + 1)

        logger.info(
            f"Polygonized {len(clean_gdf)} flood polygons (Total Area: {clean_gdf['area_km2'].sum():.2f} km²)."
        )
        return clean_gdf

    @staticmethod
    def calculate_displaced_population(
        flood_gdf: gpd.GeoDataFrame,
        population_raster_path: Path,
    ) -> Tuple[int, np.ndarray, rasterio.Affine]:
        """
        Calculates Total Displaced Population by summing GHSL population pixel
        values strictly within the flooded vector polygons.
        """
        if not population_raster_path.exists() or flood_gdf.empty:
            return 0, np.array([]), None

        logger.info(f"Extracting GHSL population displacement from: {population_raster_path}")
        with rasterio.open(population_raster_path) as src:
            # Rasterio mask expects geometries in the same CRS
            geometries = [geom for geom in flood_gdf.geometry if geom.is_valid and not geom.is_empty]
            if not geometries:
                return 0, np.array([]), src.transform

            out_image, out_transform = mask(src, geometries, crop=False, filled=False)
            valid_pixels = out_image[0]
            # Sum pixels where value > 0 and not nodata
            valid_mask = (valid_pixels > 0) & (valid_pixels != src.nodata)
            total_displaced = int(np.round(np.sum(valid_pixels[valid_mask])))

        logger.info(f"Total Displaced Population calculated: {total_displaced:,} persons.")
        return total_displaced, out_image, out_transform

    @staticmethod
    def clip_severed_roads(
        roads_gdf: gpd.GeoDataFrame,
        flood_gdf: gpd.GeoDataFrame,
    ) -> Tuple[gpd.GeoDataFrame, float, Dict[str, float]]:
        """
        Intersects road linestrings with flood footprint to identify severed routes,
        computing blocked lengths per highway classification.
        """
        if roads_gdf.empty or flood_gdf.empty:
            empty_gdf = gpd.GeoDataFrame(
                {"id": [], "name": [], "highway": [], "length_km": []},
                geometry=[],
                crs=config.GEOGRAPHIC_CRS,
            )
            return empty_gdf, 0.0, {}

        logger.info("Computing spatial intersection between road network and flood extent...")
        # Unify flood geometry for fast intersection
        unified_flood = flood_gdf.unary_union

        # Spatial filter candidate roads intersecting flood boundary box
        candidates = roads_gdf[roads_gdf.intersects(unified_flood)].copy()
        if candidates.empty:
            return candidates, 0.0, {}

        # Precise geometric intersection
        clipped_geoms = candidates.geometry.intersection(unified_flood)
        valid_mask = (~clipped_geoms.is_empty) & (clipped_geoms.geom_type.isin(["LineString", "MultiLineString"]))
        severed_roads = candidates[valid_mask].copy()
        severed_roads.geometry = clipped_geoms[valid_mask]

        # Calculate exact length in km in projected CRS
        severed_proj = severed_roads.to_crs(config.METRIC_CRS)
        severed_roads["length_km"] = (severed_proj.geometry.length / 1000.0).round(2)

        total_blocked_km = float(severed_roads["length_km"].sum())
        breakdown = {k: round(v, 2) for k, v in severed_roads.groupby("highway")["length_km"].sum().to_dict().items()}

        logger.info(f"Identified {len(severed_roads)} severed road segments ({total_blocked_km:.2f} km blocked).")
        return severed_roads, total_blocked_km, breakdown

    @staticmethod
    def assess_settlement_impact(
        admin_gdf: gpd.GeoDataFrame,
        flood_gdf: gpd.GeoDataFrame,
        population_raster_path: Optional[Path] = None,
    ) -> Tuple[pd.DataFrame, gpd.GeoDataFrame]:
        """
        Quantifies settlement inundation, exposure percentage, GHSL displaced population,
        criticality impact scoring, and prioritized dispatch rankings.
        """
        if admin_gdf.empty or flood_gdf.empty:
            cols = [
                "Settlement Name",
                "District",
                "Flooded km²",
                "Exposure %",
                "Displaced Population",
                "Priority Level",
                "Impact Score",
            ]
            return pd.DataFrame(columns=cols), gpd.GeoDataFrame()

        logger.info("Assessing settlement impact, exposure scoring, and displaced persons...")
        unified_flood = flood_gdf.unary_union

        # Candidate settlements intersecting flood footprint
        intersecting_admin = admin_gdf[admin_gdf.intersects(unified_flood)].copy()
        if intersecting_admin.empty:
            cols = [
                "Settlement Name",
                "District",
                "Flooded km²",
                "Exposure %",
                "Displaced Population",
                "Priority Level",
                "Impact Score",
            ]
            return pd.DataFrame(columns=cols), gpd.GeoDataFrame()

        # Compute precise flooded intersection polygon inside each settlement
        intersecting_admin["flood_geom"] = intersecting_admin.geometry.intersection(unified_flood)

        # Calculate flooded area in km² using metric projection
        inter_gdf_proj = gpd.GeoDataFrame(
            intersecting_admin,
            geometry="flood_geom",
            crs=admin_gdf.crs,
        ).to_crs(config.METRIC_CRS)
        intersecting_admin["flooded_km2"] = inter_gdf_proj.geometry.area / 1e6

        # Filter out negligible overlaps (< 0.01 km²)
        affected_admin = intersecting_admin[intersecting_admin["flooded_km2"] >= 0.01].copy()

        # Calculate Exposure Percentage
        affected_admin["total_area_km2"] = affected_admin["total_area_km2"].replace(0, np.nan)
        affected_admin["exposure_pct"] = (
            affected_admin["flooded_km2"] / affected_admin["total_area_km2"]
        ) * 100.0
        affected_admin["exposure_pct"] = affected_admin["exposure_pct"].clip(upper=100.0).fillna(0.0)

        # Calculate Displaced Population per settlement via GHSL raster sampling
        displaced_list = []
        pop_src = None
        if population_raster_path and population_raster_path.exists():
            pop_src = rasterio.open(population_raster_path)

        for _, row in affected_admin.iterrows():
            geom = row["flood_geom"]
            if pop_src and geom is not None and not geom.is_empty and geom.is_valid:
                try:
                    out_img, _ = mask(pop_src, [geom], crop=True, filled=False)
                    vals = out_img[0]
                    pop_count = int(np.round(np.sum(vals[(vals > 0) & (vals != pop_src.nodata)])))
                except Exception:
                    # Fallback approximation: density ~ 450 persons/km²
                    pop_count = int(round(row["flooded_km2"] * 450.0))
            else:
                pop_count = int(round(row["flooded_km2"] * 450.0))
            displaced_list.append(max(0, pop_count))

        if pop_src:
            pop_src.close()

        affected_admin["displaced_population"] = displaced_list

        # Impact Score = Exposure (%) * Criticality Weight
        # Weight scales with population density and critical exposure
        criticality_weight = 1.0 + np.log10(1.0 + affected_admin["displaced_population"] / 250.0)
        affected_admin["impact_score"] = (affected_admin["exposure_pct"] * criticality_weight).round(2)

        # Assign Categorical Priority Level
        def get_priority(row):
            exp = row["exposure_pct"]
            pop = row["displaced_population"]
            if exp >= 15.0 or pop >= 4000:
                return "CRITICAL"
            elif exp >= 7.0 or pop >= 1500:
                return "HIGH"
            elif exp >= 2.0 or pop >= 300:
                return "MEDIUM"
            else:
                return "WATCH"

        affected_admin["priority_level"] = affected_admin.apply(get_priority, axis=1)

        # Format presentation DataFrame
        impact_df = pd.DataFrame(
            {
                "Settlement Name": affected_admin["settlement"],
                "District": affected_admin["district"],
                "Flooded km²": affected_admin["flooded_km2"].round(2),
                "Exposure %": affected_admin["exposure_pct"].round(2),
                "Displaced Population": affected_admin["displaced_population"],
                "Priority Level": affected_admin["priority_level"],
                "Impact Score": affected_admin["impact_score"],
            }
        ).sort_values(by=["Impact Score", "Displaced Population"], ascending=False)

        # Also prepare the geospatial result for mapping
        affected_gdf = affected_admin[
            [
                "settlement",
                "district",
                "total_area_km2",
                "flooded_km2",
                "exposure_pct",
                "displaced_population",
                "priority_level",
                "impact_score",
                "geometry",
            ]
        ].copy()
        affected_gdf["flooded_km2"] = affected_gdf["flooded_km2"].round(2)
        affected_gdf["exposure_pct"] = affected_gdf["exposure_pct"].round(1)
        affected_gdf["total_area_km2"] = affected_gdf["total_area_km2"].round(2)

        logger.info(f"Quantified impact across {len(impact_df)} affected settlements.")
        return impact_df, affected_gdf


def run_full_impact_pipeline(
    raster_path: Path,
    population_raster_path: Optional[Path] = None,
    aoi_coords: List[float] = config.AOI_COORDINATES,
) -> Dict[str, Any]:
    """
    Executes the end-to-end vector impact pipeline:
    - Raster to flood polygons
    - GHSL Total Displaced Population
    - Severed roads identification & length calculation
    - Settlement exposure scoring & Top 5 Affected settlements ranking
    """
    if population_raster_path is None:
        population_raster_path = config.DEFAULT_POPULATION_RASTER

    # 1. Polygonize flood mask
    flood_gdf = ImpactEngine.polygonize_raster(raster_path)
    total_flooded_km2 = float(flood_gdf["area_km2"].sum()) if not flood_gdf.empty else 0.0

    # 2. Calculate Total Displaced Population strictly within flood polygons
    total_displaced_pop, _, _ = ImpactEngine.calculate_displaced_population(
        flood_gdf=flood_gdf,
        population_raster_path=population_raster_path,
    )

    # 3. Load local OSM roads and HDX admin data
    roads_gdf = VectorDataLoader.load_osm_roads(aoi_coords=aoi_coords)
    admin_gdf = VectorDataLoader.load_admin_boundaries(aoi_coords=aoi_coords)

    # 4. Clip severed roads
    severed_roads_gdf, total_blocked_km, road_breakdown = ImpactEngine.clip_severed_roads(
        roads_gdf=roads_gdf,
        flood_gdf=flood_gdf,
    )

    # 5. Assess settlement impact and rank top affected
    all_settlements_df, affected_admin_gdf = ImpactEngine.assess_settlement_impact(
        admin_gdf=admin_gdf,
        flood_gdf=flood_gdf,
        population_raster_path=population_raster_path,
    )

    top_5_df = all_settlements_df.head(5).reset_index(drop=True)

    metrics = {
        "total_flooded_km2": round(total_flooded_km2, 2),
        "total_blocked_road_km": round(total_blocked_km, 2),
        "total_displaced_population": total_displaced_pop,
        "impacted_settlements_count": len(all_settlements_df),
        "critical_settlements_count": int((all_settlements_df["Priority Level"] == "CRITICAL").sum()),
        "high_settlements_count": int((all_settlements_df["Priority Level"] == "HIGH").sum()),
        "road_breakdown": road_breakdown,
    }

    return {
        "metrics": metrics,
        "top_5_settlements": top_5_df,
        "all_settlements_df": all_settlements_df,
        "flood_gdf": flood_gdf,
        "severed_roads_gdf": severed_roads_gdf,
        "affected_admin_gdf": affected_admin_gdf,
    }

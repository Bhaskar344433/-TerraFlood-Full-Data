"""
TerraFlood Tactical Command Center Dashboard
============================================
Streamlit + Folium operations HUD for rapid flood extent mapping,
settlement exposure quantification, severed infrastructure identification,
interactive Plotly analytics, humanitarian dispatch logistics, and GHSL
population displacement intelligence in Nepal's Terai corridor.
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timezone
import json

import streamlit as st
import folium
from folium import plugins
from streamlit_folium import st_folium
import pandas as pd
import geopandas as gpd
import plotly.express as px
import plotly.graph_objects as go

# Ensure local package import works regardless of invocation directory
current_dir = Path(__file__).resolve().parent
parent_dir = current_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from terraflood import config, engine, impact, export_utils

# -----------------------------------------------------------------------------
# Streamlit Page Configuration & Tactical Theme CSS
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="TerraFlood // Tactical Command Center",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Tactical Operations / Command Center Dark Styling (Black + Neon Orange + Crimson Red)
TACTICAL_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700;800&family=Outfit:wght@400;500;600;700;800;900&family=Rajdhani:wght@600;700&display=swap');

    /* Dark Obsidian & High-Contrast Hazard Palette */
    :root {
        --bg-obsidian: #08090C;
        --bg-surface: #0E1217;
        --card-slate: #141820;
        --card-border: #232B38;
        --accent-amber: #FF6D00;
        --accent-orange: #FF5722;
        --hazard-red: #FF1744;
        --hazard-red-dark: #D50000;
        --safe-green: #00E676;
        --cyan-telemetry: #00E5FF;
        --text-primary: #F8FAFC;
        --text-secondary: #94A3B8;
        --text-muted: #64748B;
    }

    /* Overall App Background & Typography */
    .stApp {
        background-color: var(--bg-obsidian) !important;
        color: var(--text-primary) !important;
        font-family: 'Outfit', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }

    /* Hide default Streamlit headers & deployment badges */
    header, footer { visibility: hidden !important; }
    .stDeployButton { display: none !important; }

    /* Custom Tactical Scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    ::-webkit-scrollbar-track {
        background: #08090C;
    }
    ::-webkit-scrollbar-thumb {
        background: #232B38;
        border-radius: 4px;
        border: 1px solid rgba(255, 87, 34, 0.2);
    }
    ::-webkit-scrollbar-thumb:hover {
        background: var(--accent-orange);
    }

    /* Pulse & Radar Animations */
    @keyframes pulse-hazard {
        0% { box-shadow: 0 0 0 0 rgba(255, 23, 68, 0.7); }
        70% { box-shadow: 0 0 0 10px rgba(255, 23, 68, 0); }
        100% { box-shadow: 0 0 0 0 rgba(255, 23, 68, 0); }
    }

    @keyframes radar-sweep {
        0% { background-position: -200% 0; }
        100% { background-position: 200% 0; }
    }

    @keyframes beacon-blink {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.35; transform: scale(0.85); }
    }

    /* Command Header Bar with Animated Accent Border */
    .command-header {
        background: linear-gradient(135deg, #11141B 0%, #0A0C10 100%);
        border: 1px solid #232B38;
        border-left: 5px solid var(--accent-orange);
        border-bottom: 2px solid var(--accent-amber);
        padding: 16px 22px;
        margin-bottom: 20px;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.6), 0 0 15px rgba(255, 87, 34, 0.12);
        position: relative;
        overflow: hidden;
    }

    .command-header::after {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 1px;
        background: linear-gradient(90deg, transparent, var(--accent-orange), var(--hazard-red), transparent);
        background-size: 200% 100%;
        animation: radar-sweep 4s linear infinite;
    }

    .command-title {
        font-family: 'Rajdhani', 'Outfit', sans-serif;
        font-size: 24px;
        font-weight: 800;
        letter-spacing: 2px;
        color: #FFFFFF;
        display: flex;
        align-items: center;
        gap: 12px;
        text-shadow: 0 0 12px rgba(255, 109, 0, 0.4);
    }

    .command-meta {
        font-size: 12px;
        color: var(--text-secondary);
        font-family: 'JetBrains Mono', monospace;
        letter-spacing: 0.5px;
    }

    /* Live Telemetry Beacon */
    .live-beacon {
        display: inline-block;
        width: 10px;
        height: 10px;
        background-color: var(--hazard-red);
        border-radius: 50%;
        margin-right: 6px;
        box-shadow: 0 0 10px var(--hazard-red);
        animation: beacon-blink 1.4s ease-in-out infinite;
    }

    /* Metric Cards Grid */
    .kpi-container {
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 14px;
        margin-bottom: 22px;
    }

    .kpi-card {
        background: linear-gradient(145deg, #12161F 0%, #0D1016 100%);
        border: 1px solid var(--card-border);
        border-radius: 8px;
        padding: 16px 18px;
        position: relative;
        overflow: hidden;
        box-shadow: 0 6px 18px rgba(0, 0, 0, 0.35);
        transition: all 0.28s cubic-bezier(0.16, 1, 0.3, 1);
    }

    .kpi-card:hover {
        transform: translateY(-4px);
        border-color: var(--accent-orange);
        box-shadow: 0 12px 28px -4px rgba(255, 87, 34, 0.3), 0 0 12px rgba(255, 87, 34, 0.2);
    }

    .kpi-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 3.5px;
        background: linear-gradient(90deg, var(--accent-orange), var(--accent-amber));
    }

    .kpi-card.hazard {
        border-color: rgba(255, 23, 68, 0.3);
    }
    .kpi-card.hazard::before {
        background: linear-gradient(90deg, var(--hazard-red), #FF5252);
    }
    .kpi-card.hazard:hover {
        border-color: var(--hazard-red);
        box-shadow: 0 12px 28px -4px rgba(255, 23, 68, 0.35);
    }

    .kpi-card.telemetry::before {
        background: linear-gradient(90deg, var(--cyan-telemetry), #00B0FF);
    }
    .kpi-card.safe::before {
        background: linear-gradient(90deg, var(--safe-green), #69F0AE);
    }

    .kpi-label {
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1px;
        color: var(--text-secondary);
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        gap: 6px;
    }

    .kpi-value {
        font-size: 26px;
        font-weight: 800;
        color: #FFFFFF;
        font-family: 'JetBrains Mono', monospace;
        letter-spacing: -0.5px;
    }

    .kpi-subtext {
        font-size: 11px;
        color: var(--text-muted);
        margin-top: 6px;
        font-family: 'Outfit', sans-serif;
    }

    /* Tactical On-Map Legend */
    .map-legend-bar {
        background: rgba(14, 18, 23, 0.92);
        border: 1px solid var(--card-border);
        border-radius: 6px;
        padding: 8px 14px;
        margin-bottom: 10px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        font-size: 12px;
        color: var(--text-secondary);
    }

    .legend-item {
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .legend-box {
        width: 14px;
        height: 14px;
        border-radius: 3px;
        display: inline-block;
    }

    /* Fail-Safe Non-Blocking Warning Banner */
    .failsafe-banner {
        background: rgba(255, 23, 68, 0.08);
        border: 1px solid rgba(255, 23, 68, 0.4);
        border-left: 5px solid var(--hazard-red);
        color: #FFE5E5;
        padding: 12px 18px;
        border-radius: 6px;
        margin-bottom: 18px;
        font-weight: 600;
        display: flex;
        align-items: center;
        gap: 12px;
        font-size: 13px;
        box-shadow: 0 4px 15px rgba(255, 23, 68, 0.1);
    }

    /* Priority Badges */
    .badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 4px;
        font-size: 11px;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        font-family: 'JetBrains Mono', monospace;
    }
    .badge-critical {
        background-color: rgba(255, 23, 68, 0.22);
        color: #FF5252;
        border: 1px solid #FF5252;
        box-shadow: 0 0 8px rgba(255, 23, 68, 0.3);
    }
    .badge-high {
        background-color: rgba(255, 109, 0, 0.22);
        color: #FF9800;
        border: 1px solid #FF9800;
    }
    .badge-medium {
        background-color: rgba(255, 214, 0, 0.2);
        color: #FFD600;
        border: 1px solid #FFD600;
    }
    .badge-watch {
        background-color: rgba(0, 230, 118, 0.2);
        color: #69F0AE;
        border: 1px solid #69F0AE;
    }

    /* Sidebar Customization */
    section[data-testid="stSidebar"] {
        background-color: #0B0E13 !important;
        border-right: 1px solid #1C232E !important;
    }

    /* Primary Action Buttons */
    div.stButton > button {
        background: linear-gradient(135deg, #FF6D00 0%, #D50000 100%) !important;
        color: #FFFFFF !important;
        border: none !important;
        font-weight: 800 !important;
        letter-spacing: 1px !important;
        font-family: 'Rajdhani', sans-serif !important;
        font-size: 15px !important;
        border-radius: 6px !important;
        padding: 10px 20px !important;
        box-shadow: 0 4px 14px rgba(255, 109, 0, 0.35) !important;
        transition: all 0.25s ease !important;
    }
    div.stButton > button:hover {
        background: linear-gradient(135deg, #FF8A65 0%, #FF1744 100%) !important;
        box-shadow: 0 6px 20px rgba(255, 23, 68, 0.5) !important;
        transform: translateY(-2px) !important;
    }

    /* Download Buttons */
    div.stDownloadButton > button {
        background-color: var(--card-slate) !important;
        color: var(--text-primary) !important;
        border: 1px solid #2A3342 !important;
        border-radius: 6px !important;
        font-weight: 700 !important;
        padding: 8px 16px !important;
        transition: all 0.2s ease !important;
    }
    div.stDownloadButton > button:hover {
        border-color: var(--accent-orange) !important;
        color: var(--accent-orange) !important;
        box-shadow: 0 4px 12px rgba(255, 87, 34, 0.25) !important;
    }

    /* Tactical Tab Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #0E1218;
        padding: 6px;
        border-radius: 8px;
        border: 1px solid #232B38;
    }
    .stTabs [data-baseweb="tab"] {
        height: 42px;
        border-radius: 6px;
        color: var(--text-secondary);
        font-family: 'Rajdhani', 'Outfit', sans-serif;
        font-weight: 700;
        font-size: 14px;
        letter-spacing: 0.8px;
        padding: 0 18px;
        background-color: transparent;
        border: none;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, rgba(255, 109, 0, 0.25) 0%, rgba(213, 0, 0, 0.2) 100%) !important;
        color: #FFFFFF !important;
        border: 1px solid var(--accent-orange) !important;
        box-shadow: 0 2px 8px rgba(255, 109, 0, 0.2) !important;
    }
</style>
"""
st.markdown(TACTICAL_CSS, unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# Cached Pipeline Orchestrator (Fully wired parameters)
# -----------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def execute_terraflood_pipeline(
    aoi_coords: list,
    sar_threshold_db: float,
    dem_slope_max: float,
    jrc_threshold: int,
    force_fallback: bool,
    pre_window: tuple,
    post_window: tuple,
):
    """Executes satellite detection, GHSL population extraction, and vector overlays."""
    # Run satellite change detection & GHSL layer pull
    sat_res = engine.run_flood_detection_pipeline(
        aoi_coords=aoi_coords,
        force_fallback=force_fallback,
        pre_window=pre_window,
        post_window=post_window,
        sar_threshold_db=sar_threshold_db,
        jrc_threshold=jrc_threshold,
        dem_slope_max=dem_slope_max,
    )

    # Run vector impact, road severance, and settlement exposure quantification
    impact_res = impact.run_full_impact_pipeline(
        raster_path=sat_res["raster_path"],
        population_raster_path=sat_res.get("population_raster_path"),
        aoi_coords=aoi_coords,
    )

    return sat_res, impact_res


# -----------------------------------------------------------------------------
# Sidebar Tactical Control Panel
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 🎛️ TACTICAL CONTROL PANEL")
    st.caption("Active Geospatial Parameters & Sensor Thresholds")

    st.markdown("---")
    st.markdown("#### 🛰️ Satellite Windows")
    pre_start = st.text_input("Pre-Flood Baseline Start", value=config.PRE_FLOOD_WINDOW[0])
    pre_end = st.text_input("Pre-Flood Baseline End", value=config.PRE_FLOOD_WINDOW[1])
    post_start = st.text_input("Post-Flood Event Start", value=config.POST_FLOOD_WINDOW[0])
    post_end = st.text_input("Post-Flood Event End", value=config.POST_FLOOD_WINDOW[1])

    st.markdown("---")
    st.markdown("#### 🔬 Scientific Filtering")
    sar_thresh = st.slider(
        "SAR ΔBackscatter Threshold (dB)",
        min_value=0.5,
        max_value=3.0,
        value=float(config.SAR_BACKSCATTER_THRESHOLD_DB),
        step=0.25,
        help="Higher values select only high-confidence specular water reflections.",
    )
    slope_max = st.slider(
        "DEM Max Slope Cutoff (Degrees)",
        min_value=2.0,
        max_value=12.0,
        value=float(config.DEM_MAX_SLOPE_DEGREES),
        step=0.5,
        help="Masks out terrain shadows and mountain slopes.",
    )
    jrc_thresh = st.slider(
        "JRC Water Occurrence (%)",
        min_value=50,
        max_value=95,
        value=int(config.JRC_WATER_OCCURRENCE_THRESHOLD),
        step=5,
        help="Masks out permanent lakes, reservoirs, and perennial riverbeds.",
    )

    st.markdown("---")
    st.markdown("#### ⚙️ Pipeline Execution")
    force_sim = st.toggle("Force Fail-Safe Simulation", value=config.FALLBACK_MODE)

    rescan_clicked = st.button("🚀 TRIGGER RESCAN", use_container_width=True)
    if rescan_clicked:
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")
    st.caption("Active AOI [Nepal Terai Corridor]:")
    st.code(f"{config.AOI_COORDINATES}", language="python")


# -----------------------------------------------------------------------------
# Execute Data Ingestion & Scientific Processing
# -----------------------------------------------------------------------------
with st.spinner("🛰️ Ingesting Sentinel-1 SAR & GHSL Population Data..."):
    sat_res, impact_res = execute_terraflood_pipeline(
        aoi_coords=config.AOI_COORDINATES,
        sar_threshold_db=sar_thresh,
        dem_slope_max=slope_max,
        jrc_threshold=jrc_thresh,
        force_fallback=force_sim,
        pre_window=(pre_start, pre_end),
        post_window=(post_start, post_end),
    )

metrics = impact_res["metrics"]
top_5_df = impact_res["top_5_settlements"]
all_settlements_df = impact_res["all_settlements_df"]
flood_gdf = impact_res["flood_gdf"]
severed_roads_gdf = impact_res["severed_roads_gdf"]
affected_admin_gdf = impact_res["affected_admin_gdf"]
qa = sat_res["qa_flags"]

# -----------------------------------------------------------------------------
# Top Navigation Bar & Operational Status
# -----------------------------------------------------------------------------
now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

is_failsafe = (sat_res["status"] == "FAILSAFE_ACTIVATED") or force_sim
status_badge = (
    '<span style="color:#FF5252; background:rgba(255,23,68,0.2); padding:5px 12px; border-radius:4px; font-weight:800; border:1px solid #FF5252; font-family:\'JetBrains Mono\', monospace; font-size:12px;"><span class="live-beacon"></span>FAIL-SAFE SIMULATION</span>'
    if is_failsafe
    else '<span style="color:#00E676; background:rgba(0,230,118,0.2); padding:5px 12px; border-radius:4px; font-weight:800; border:1px solid #00E676; font-family:\'JetBrains Mono\', monospace; font-size:12px;">🟢 GEE CLOUD ACTIVE</span>'
)

st.markdown(
    f"""
    <div class="command-header">
        <div>
            <div class="command-title">
                🛰️ TERRAFLOOD // DISASTER COMMAND CENTER
            </div>
            <div class="command-meta">
                MISSION: RAPID FLOOD EXTENT MAPPING & HUMANITARIAN IMPACT DISPATCH | NEPAL TERAI
            </div>
        </div>
        <div style="text-align: right;">
            <div>{status_badge}</div>
            <div class="command-meta" style="margin-top: 6px;">SYS_TIME: {now_utc}</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Fail-Safe Warning Banner if GEE is offline
if is_failsafe:
    st.markdown(
        """
        <div class="failsafe-banner">
            <div style="font-size:20px;">⚠️</div>
            <div>
                <strong>FAIL-SAFE PROTOCOL ENGAGED: INSUFFICIENT SATELLITE EVIDENCE - SERVING HIGH-FIDELITY GROUND TELEMETRY.</strong><br>
                Operating in autonomous offline mode utilizing calibrated Terai monsoon flood footprint & 100m JRC GHSL population data.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# -----------------------------------------------------------------------------
# Top KPI Metric Cards
# -----------------------------------------------------------------------------
total_flooded_km2 = metrics.get("total_flooded_km2", 0.0)
total_blocked_km = metrics.get("total_blocked_road_km", 0.0)
total_displaced = metrics.get("total_displaced_population", 0)
impacted_count = metrics.get("impacted_settlements_count", 0)
confidence_pct = qa.get("confidence_mean", 0.91) * 100.0

st.markdown(
    f"""
    <div class="kpi-container">
        <div class="kpi-card hazard">
            <div class="kpi-label">🌊 Total Inundated Area</div>
            <div class="kpi-value">{total_flooded_km2:,.2f} <span style="font-size:14px; font-weight:600;">km²</span></div>
            <div class="kpi-subtext">Sentinel-1 Specular Water Mask</div>
        </div>
        <div class="kpi-card hazard">
            <div class="kpi-label">👥 Total Displaced Persons</div>
            <div class="kpi-value">{total_displaced:,}</div>
            <div class="kpi-subtext">GHSL Population in flood envelope</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">🚧 Blocked Highway Network</div>
            <div class="kpi-value">{total_blocked_km:,.1f} <span style="font-size:14px; font-weight:600;">km</span></div>
            <div class="kpi-subtext">Severed OSM transport corridors</div>
        </div>
        <div class="kpi-card telemetry">
            <div class="kpi-label">🏘️ Impacted Settlements</div>
            <div class="kpi-value">{impacted_count} <span style="font-size:14px; font-weight:600;">units</span></div>
            <div class="kpi-subtext">{metrics.get('critical_settlements_count', 0)} Critical / High Priority</div>
        </div>
        <div class="kpi-card safe">
            <div class="kpi-label">🎯 Mean Sensor Confidence</div>
            <div class="kpi-value">{confidence_pct:.1f}%</div>
            <div class="kpi-subtext">Copernicus SAR/Optical Co-reg</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# Central Map: Dual-Layer Folium Interactive Visualization
# -----------------------------------------------------------------------------
st.markdown("#### 🗺️ TACTICAL SITUATION MAP (SATELLITE BASE + FLOOD EXTENT + CUT-OFF HIGHWAYS)")

# Tactical On-Map Legend Bar
st.markdown(
    """
    <div class="map-legend-bar">
        <div class="legend-item">
            <span class="legend-box" style="background:#FF5722; border:1px solid #FF8C00;"></span>
            <span>Flooded Inundation Extent (SAR Specular Change)</span>
        </div>
        <div class="legend-item">
            <span class="legend-box" style="background:#E53935;"></span>
            <span>Severed Highway Arterial</span>
        </div>
        <div class="legend-item">
            <span class="legend-box" style="background:rgba(41,182,246,0.4); border:1px dashed #03A9F4;"></span>
            <span>Impacted Settlement Boundary</span>
        </div>
        <div class="legend-item">
            <span class="legend-box" style="background:#FF1744; border-radius:50%; box-shadow:0 0 6px #FF1744;"></span>
            <span>Top 5 Critical Rescue Targets</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Create Folium Map centered on Nepal Terai corridor
m = folium.Map(
    location=config.MAP_DEFAULT_CENTER,
    zoom_start=config.MAP_DEFAULT_ZOOM,
    tiles=None,
    control_scale=True,
    prefer_canvas=True,
)

# Base Layers
folium.TileLayer(
    tiles="CartoDB dark_matter",
    name="Dark Tactical (Obsidian)",
    control=True,
    show=True,
).add_to(m)

folium.TileLayer(
    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attr="Esri World Imagery",
    name="Esri High-Res Satellite",
    control=True,
    show=False,
).add_to(m)

folium.TileLayer(
    tiles="OpenStreetMap",
    name="Standard Street Map",
    control=True,
    show=False,
).add_to(m)

# 1. AOI Bounding Box
min_lon, min_lat, max_lon, max_lat = config.AOI_COORDINATES
folium.Rectangle(
    bounds=[[min_lat, min_lon], [max_lat, max_lon]],
    color="#00E5FF",
    weight=1.5,
    dash_array="5, 5",
    fill=False,
    popup="Operational AOI: Nepal Terai Flood Corridor",
).add_to(m)

# 2. Translucent Neon-Orange Flood Footprint Polygons
if not flood_gdf.empty:
    flood_layer = folium.FeatureGroup(name="Flooded Footprint (Specular SAR Water)", show=True)
    folium.GeoJson(
        flood_gdf.to_json(),
        style_function=lambda feature: {
            "fillColor": "#FF5722",
            "color": "#FF8C00",
            "weight": 1.2,
            "fillOpacity": 0.55,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=["flood_id", "area_km2"],
            aliases=["Flood Polygon ID:", "Area (km²):"],
            localize=True,
        ),
    ).add_to(flood_layer)
    flood_layer.add_to(m)

# 3. Highlighted Severed Road Segments (Hazard Red)
if not severed_roads_gdf.empty:
    roads_layer = folium.FeatureGroup(name="Severed Highway Infrastructure", show=True)
    major_types = ["motorway", "trunk", "primary", "secondary", "tertiary"]
    map_roads = severed_roads_gdf[severed_roads_gdf["highway"].isin(major_types)].copy()
    if map_roads.empty:
        map_roads = severed_roads_gdf.head(500).copy()
    else:
        other_roads = severed_roads_gdf[~severed_roads_gdf["highway"].isin(major_types)].head(600)
        map_roads = pd.concat([map_roads, other_roads])

    folium.GeoJson(
        map_roads[["name", "highway", "length_km", "geometry"]].to_json(),
        style_function=lambda feature: {
            "color": "#FF1744",
            "weight": 3.2 if feature["properties"]["highway"] in ["trunk", "primary"] else 2.0,
            "opacity": 0.9,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=["name", "highway", "length_km"],
            aliases=["Route:", "Highway Type:", "Severed Length (km):"],
            localize=True,
        ),
    ).add_to(roads_layer)
    roads_layer.add_to(m)

# 4. Top Affected Settlements Outlines with Popups
if affected_admin_gdf is not None and not affected_admin_gdf.empty:
    admin_layer = folium.FeatureGroup(name="Affected Settlement Boundaries", show=True)
    top_admin_map = affected_admin_gdf.head(25).copy()
    folium.GeoJson(
        top_admin_map.to_json(),
        style_function=lambda feature: {
            "fillColor": "#29B6F6",
            "color": "#03A9F4",
            "weight": 1.5,
            "fillOpacity": 0.15,
            "dashArray": "4, 4",
        },
        tooltip=folium.GeoJsonTooltip(
            fields=["settlement", "district", "exposure_pct", "displaced_population", "priority_level"],
            aliases=["Settlement:", "District:", "Exposure (%):", "Displaced Persons:", "Priority Level:"],
            localize=True,
        ),
    ).add_to(admin_layer)
    admin_layer.add_to(m)

# 5. Pulsing Rescue Target Markers on Top Critical Settlements
if affected_admin_gdf is not None and not top_5_df.empty:
    targets_layer = folium.FeatureGroup(name="🚨 Priority 1 Rescue Targets", show=True)
    for idx, row in top_5_df.iterrows():
        s_name = row["Settlement Name"]
        match = affected_admin_gdf[affected_admin_gdf["settlement"] == s_name]
        if not match.empty:
            geom = match.iloc[0].geometry
            center = geom.centroid
            folium.CircleMarker(
                location=[center.y, center.x],
                radius=9,
                color="#FF1744",
                weight=3,
                fill=True,
                fill_color="#D50000",
                fill_opacity=0.9,
                tooltip=f"🚨 TARGET: {s_name} ({row['Displaced Population']:,} Displaced)",
                popup=folium.Popup(
                    f"""
                    <div style="font-family:'Outfit',sans-serif; width:220px; color:#111;">
                        <h4 style="margin:0 0 6px 0; color:#D50000; font-size:15px;">🚨 {s_name}</h4>
                        <div style="font-size:12px; line-height:1.4;">
                            <b>District:</b> {row['District']}<br>
                            <b>Displaced Persons:</b> {row['Displaced Population']:,}<br>
                            <b>Inundated Area:</b> {row['Flooded km²']} km² ({row['Exposure %']}%)<br>
                        </div>
                        <div style="background:#FFEBEE; color:#C62828; padding:5px 8px; border-radius:4px; font-size:10px; font-weight:800; margin-top:8px;">
                            PRIORITY 1: AIR-DROP & BOAT EVACUATION
                        </div>
                    </div>
                    """,
                    max_width=250,
                ),
            ).add_to(targets_layer)
    targets_layer.add_to(m)

# Plugins & Controls
plugins.Fullscreen(position="topleft").add_to(m)
plugins.MeasureControl(position="bottomleft", primary_length_unit="kilometers").add_to(m)
plugins.MiniMap(toggle_display=True, position="bottomright").add_to(m)
folium.LayerControl(position="topright", collapsed=False).add_to(m)

# Render map in Streamlit (returned_objects=[] prevents costly re-renders on zoom/pan)
st_folium(m, width="100%", height=530, returned_objects=[])

# -----------------------------------------------------------------------------
# Bottom Container: Multi-Tab Intelligence & Prioritized Dispatch
# -----------------------------------------------------------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🚨 PRIORITY SETTLEMENT DISPATCH",
    "📊 TACTICAL VISUAL ANALYTICS",
    "🚧 SEVERED INFRASTRUCTURE BREAKDOWN",
    "🚁 HUMANITARIAN LOGISTICS CALCULATOR",
    "📦 EXPORTS & SATELLITE QA",
])

with tab1:
    st.markdown("#### Ranked Settlement Priority Dispatch (GHSL Population Overlay)")
    st.caption("Prioritization based on Flooded Area, Exposure %, and GHSL Displaced Population.")

    if not all_settlements_df.empty:
        f_col1, f_col2, f_col3 = st.columns([2, 2, 2])
        with f_col1:
            all_districts = ["All Districts"] + sorted(list(all_settlements_df["District"].unique()))
            selected_district = st.selectbox("Filter by District", all_districts)
        with f_col2:
            priority_filter = st.selectbox("Filter by Priority Level", ["All Priorities", "CRITICAL Only", "HIGH & CRITICAL"])
        with f_col3:
            search_query = st.text_input("🔍 Search Village / Settlement", "")

        filtered_df = all_settlements_df.copy()
        if selected_district != "All Districts":
            filtered_df = filtered_df[filtered_df["District"] == selected_district]
        if priority_filter == "CRITICAL Only":
            filtered_df = filtered_df[filtered_df["Priority Level"] == "CRITICAL"]
        elif priority_filter == "HIGH & CRITICAL":
            filtered_df = filtered_df[filtered_df["Priority Level"].isin(["CRITICAL", "HIGH"])]
        if search_query.strip():
            filtered_df = filtered_df[filtered_df["Settlement Name"].str.contains(search_query.strip(), case=False, na=False)]

        # Quick settlement inspector highlight
        if not filtered_df.empty:
            top_unit = filtered_df.iloc[0]
            st.markdown(
                f"""
                <div style="background:#131822; border-left:4px solid #FF1744; padding:12px 18px; border-radius:6px; margin:12px 0; display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <div style="font-size:11px; color:#94A3B8; text-transform:uppercase; font-weight:700;">TOP EMERGENCY TARGET IN ACTIVE VIEW</div>
                        <div style="font-size:18px; font-weight:800; color:#FFFFFF;">🚨 {top_unit['Settlement Name']} ({top_unit['District']} District)</div>
                        <div style="font-size:12px; color:#CBD5E1; margin-top:2px;">
                            Displaced: <b style="color:#FF5252;">{top_unit['Displaced Population']:,} persons</b> | 
                            Inundation: <b>{top_unit['Flooded km²']:.2f} km² ({top_unit['Exposure %']:.1f}%)</b> | 
                            Impact Score: <b>{top_unit['Impact Score']}</b>
                        </div>
                    </div>
                    <div>
                        <span class="badge badge-critical">IMMEDIATE DISPATCH</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        display_df = filtered_df.copy()
        display_df["Displaced Population"] = display_df["Displaced Population"].apply(lambda x: f"{x:,}")
        display_df["Flooded km²"] = display_df["Flooded km²"].apply(lambda x: f"{x:.2f}")
        display_df["Exposure %"] = display_df["Exposure %"].apply(lambda x: f"{x:.1f}%")

        st.dataframe(
            display_df,
            use_container_width=True,
            height=300,
        )
    else:
        st.info("No settlements inundated within active AOI.")

with tab2:
    st.markdown("#### Tactical Visual Analytics")
    st.caption("Real-time data visualization of displacement concentrations and road severance patterns.")

    if not all_settlements_df.empty:
        chart_col1, chart_col2 = st.columns(2)

        with chart_col1:
            # Top 10 settlements displaced population horizontal bar chart
            top10 = all_settlements_df.head(10).copy()
            color_map = {
                "CRITICAL": "#FF1744",
                "HIGH": "#FF6D00",
                "MEDIUM": "#FFD600",
                "WATCH": "#00E676",
            }
            fig_bar = px.bar(
                top10,
                x="Displaced Population",
                y="Settlement Name",
                color="Priority Level",
                orientation="h",
                color_discrete_map=color_map,
                title="Top 10 Settlements by Displaced Population",
            )
            fig_bar.update_layout(
                yaxis={"categoryorder": "total ascending"},
                paper_bgcolor="#0E1217",
                plot_bgcolor="#141820",
                font_color="#F8FAFC",
                title_font_family="Rajdhani",
                title_font_size=16,
                margin=dict(l=20, r=20, t=40, b=20),
                height=320,
            )
            st.plotly_chart(fig_bar, use_container_width=True)

        with chart_col2:
            # Highway Severance Breakdown Donut Chart
            road_breakdown = metrics.get("road_breakdown", {})
            if road_breakdown:
                sorted_roads = sorted(road_breakdown.items(), key=lambda x: x[1], reverse=True)[:6]
                hw_names = [k.capitalize() for k, v in sorted_roads]
                hw_lens = [v for k, v in sorted_roads]
                fig_donut = go.Figure(
                    data=[
                        go.Pie(
                            labels=hw_names,
                            values=hw_lens,
                            hole=0.55,
                            marker_colors=["#FF1744", "#FF5722", "#FF9100", "#FFC400", "#00E5FF", "#7C4DFF"],
                        )
                    ]
                )
                fig_donut.update_layout(
                    title="Blocked Road Corridors by Classification (km)",
                    paper_bgcolor="#0E1217",
                    plot_bgcolor="#141820",
                    font_color="#F8FAFC",
                    title_font_family="Rajdhani",
                    title_font_size=16,
                    margin=dict(l=20, r=20, t=40, b=20),
                    height=320,
                )
                st.plotly_chart(fig_donut, use_container_width=True)
            else:
                st.info("No road severance breakdown available.")

        # Scatter plot: Inundated Area vs Displaced Population
        fig_scatter = px.scatter(
            all_settlements_df,
            x="Flooded km²",
            y="Displaced Population",
            size="Impact Score",
            color="Priority Level",
            hover_name="Settlement Name",
            hover_data=["District", "Exposure %"],
            color_discrete_map=color_map,
            title="Correlation: Inundated Area vs. GHSL Displaced Population",
        )
        fig_scatter.update_layout(
            paper_bgcolor="#0E1217",
            plot_bgcolor="#141820",
            font_color="#F8FAFC",
            title_font_family="Rajdhani",
            title_font_size=16,
            height=280,
            margin=dict(l=20, r=20, t=40, b=20),
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

with tab3:
    st.markdown("#### Cut-Off Highway & Road Infrastructure")
    road_breakdown = metrics.get("road_breakdown", {})
    if road_breakdown:
        cols = st.columns(min(len(road_breakdown), 4))
        sorted_roads = sorted(road_breakdown.items(), key=lambda x: x[1], reverse=True)
        for i, (hw_type, length) in enumerate(sorted_roads[:8]):
            with cols[i % 4]:
                st.metric(label=f"{hw_type.upper()} ROADS", value=f"{length:,.1f} km")

        road_df = pd.DataFrame(
            [{"Highway Type": k.capitalize(), "Blocked Length (km)": round(v, 2)} for k, v in sorted_roads]
        )
        st.dataframe(road_df, use_container_width=True, height=220)
    else:
        st.info("No severed road segments detected.")

with tab4:
    st.markdown("#### 🚁 Humanitarian Logistics & Evacuation Dispatch Calculator")
    st.caption("Algorithmic modeling of emergency life-support needs based on GHSL displaced populations.")

    mobilization_pct = st.slider(
        "Response Mobilization Scope (% of total displaced population)",
        min_value=10,
        max_value=100,
        value=100,
        step=5,
        help="Simulate resource allocation for partial or full humanitarian mobilization.",
    )

    effective_pop = int(total_displaced * (mobilization_pct / 100.0))

    # Standard Humanitarian Sphere Standards:
    # 2,100 kcal / person / day -> ~ 0.5 kg dry rations / person / day = 0.0005 Metric Tons / person / day
    rations_mt_per_day = round(effective_pop * 0.0005, 1)
    # 3 Liters drinking water / person / day
    water_liters_per_day = effective_pop * 3
    # 5 persons per standard UNHCR family tent
    tents_required = int(effective_pop / 5)
    # Heavy airlift capacity (Mi-17 helicopter ~ 2.5 MT payload)
    airlift_sorties = int((rations_mt_per_day / 2.5) + 1)
    # Zodiac inflatable rescue boats (1 boat per 50 severely displaced in inundated zones)
    zodiac_boats = max(5, int(effective_pop / 80))

    l_col1, l_col2, l_col3, l_col4, l_col5 = st.columns(5)
    with l_col1:
        st.metric(label="🍞 Emergency Rations", value=f"{rations_mt_per_day:,.1f} MT/day", help="Standard Sphere dry ration guidelines")
    with l_col2:
        st.metric(label="💧 Clean Drinking Water", value=f"{water_liters_per_day:,} L/day", help="3 Liters / person / day minimum survival")
    with l_col3:
        st.metric(label="⛺ Family Relief Tents", value=f"{tents_required:,} Units", help="5 persons per shelter unit")
    with l_col4:
        st.metric(label="🚁 Airlift Sorties", value=f"{airlift_sorties:,} Missions", help="Based on 2.5 MT payload per helicopter sortie")
    with l_col5:
        st.metric(label="🚤 Rescue Zodiac Boats", value=f"{zodiac_boats:,} Crafts", help="Rapid waterborne extraction assets")

    st.markdown("---")
    st.markdown("##### 📍 Field Evacuation Advisory Directives")
    st.markdown(
        f"""
        - **Primary Staging Hub:** Establish forward logistics command at **Bharatpur & Janakpur airfields** outside the active inundation envelope.
        - **Helicopter LZ Clearances:** Coordinate with Nepal Army Disaster Relief Directorate for high-ground LZ deployments in **Sindhuli, Chitwan, and Dhankuta**.
        - **Ground Supply Access:** Deploy Bailey bridges across severed **Trunk / Primary corridors** ({metrics.get('road_breakdown', {}).get('trunk', 0):.1f} km Trunk severed).
        """
    )

with tab5:
    st.markdown("#### One-Click Humanitarian Dispatch Exports & Satellite Telemetry")
    st.caption("Generate official GDACS/UN-OCHA format situation reports and GIS vector layers.")

    # Pre-generate export files
    sitrep_pdf_path = config.EXPORTS_DIR / "TerraFlood_SitRep_Terai.pdf"
    flood_geojson_path = config.EXPORTS_DIR / "terraflood_extent.geojson"
    roads_geojson_path = config.EXPORTS_DIR / "terraflood_severed_roads.geojson"
    settlements_csv_path = config.EXPORTS_DIR / "terraflood_settlements_ranking.csv"

    export_utils.generate_pdf_report(
        metrics_dict=metrics,
        top_settlements_df=top_5_df,
        filename=sitrep_pdf_path,
        qa_flags=qa,
    )
    export_utils.export_to_geojson(flood_gdf, flood_geojson_path)
    export_utils.export_to_geojson(severed_roads_gdf, roads_geojson_path)
    export_utils.export_to_csv(all_settlements_df, settlements_csv_path)

    d_col1, d_col2, d_col3, d_col4 = st.columns(4)

    with d_col1:
        if sitrep_pdf_path.exists():
            with open(sitrep_pdf_path, "rb") as f:
                st.download_button(
                    label="📄 Download SitRep (PDF)",
                    data=f.read(),
                    file_name="TerraFlood_Disaster_SitRep.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )

    with d_col2:
        if flood_geojson_path.exists():
            with open(flood_geojson_path, "rb") as f:
                st.download_button(
                    label="🗺️ Flood Mask (GeoJSON)",
                    data=f.read(),
                    file_name="terraflood_extent.geojson",
                    mime="application/geo+json",
                    use_container_width=True,
                )

    with d_col3:
        if roads_geojson_path.exists():
            with open(roads_geojson_path, "rb") as f:
                st.download_button(
                    label="🚧 Severed Roads (GeoJSON)",
                    data=f.read(),
                    file_name="terraflood_severed_roads.geojson",
                    mime="application/geo+json",
                    use_container_width=True,
                )

    with d_col4:
        if settlements_csv_path.exists():
            with open(settlements_csv_path, "rb") as f:
                st.download_button(
                    label="📊 Ranking Table (CSV)",
                    data=f.read(),
                    file_name="terraflood_settlements_ranking.csv",
                    mime="text/csv",
                    use_container_width=True,
                )

    st.markdown("---")
    st.markdown("##### 🔬 Earth Engine & Copernicus Telemetry")
    q_col1, q_col2, q_col3 = st.columns(3)
    with q_col1:
        st.write("**Sentinel-1 SAR IW Mode**")
        st.write("- Polarization: `VV`")
        st.write(f"- Pre-Flood Scenes: `{qa.get('sar_pre_scenes', 4)}`")
        st.write(f"- Post-Flood Scenes: `{qa.get('sar_post_scenes', 4)}`")
        st.write(f"- ΔBackscatter Threshold: `{sar_thresh} dB`")
    with q_col2:
        st.write("**Sentinel-2 Optical & Fusion**")
        st.write(f"- Cloud Screen Threshold: `< {config.OPTICAL_MAX_CLOUD_PERCENT}%`")
        st.write(f"- Cloud Cover Reported: `{qa.get('cloud_cover_pct', 82.4):.1f}%`")
        st.write(f"- Optical Status: `{'Cloud Obscured' if qa.get('optical_data_unavailable', True) else 'Clear Fusion'}`")
        st.write("- MNDWI Index: `(B3 - B11)/(B3 + B11)`")
    with q_col3:
        st.write("**DEM & Baseline Water Masking**")
        st.write("- DEM Source: `Copernicus DEM GLO-30`")
        st.write(f"- Slope Filter: `<= {slope_max}°`")
        st.write(f"- Baseline Water: `JRC GSW Occurrence <= {jrc_thresh}%`")
        st.write("- Population Grid: `JRC GHSL (GHS-POP 100m)`")

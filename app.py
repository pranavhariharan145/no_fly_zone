import streamlit as st
from shapely.geometry import LineString, shape
import geopandas as gpd
import folium
from streamlit_folium import folium_static

st.set_page_config(page_title="No-Fly Zone Enforcement System", layout="wide")

st.title("✈️ No-Fly Zone Enforcement System")

# --- Coordinate Input ---
st.subheader("Enter Drone Flight Path Coordinates")
coords_text = st.text_area(
    "Enter coordinates in the format: lat1,lon1; lat2,lon2; ...",
    "12.9716,77.5946; 13.0352,77.5970"
)

def parse_coords(text):
    try:
        coord_pairs = text.split(";")
        coords = [(float(c.split(",")[1]), float(c.split(",")[0])) for c in coord_pairs]
        return coords
    except:
        st.error("Invalid format. Use lat,lon; lat,lon")
        return []

coords = parse_coords(coords_text)

# --- Load NFZ Data ---
nfz = gpd.read_file("data/airbases.geojson")

# --- Create Drone Path ---
if coords:
    drone_path = LineString(coords)

    # --- Check for Intersections ---
    intercepted_zones = []
    for _, row in nfz.iterrows():
        if drone_path.intersects(row.geometry):
            intercepted_zones.append(row.get("name", "Unknown Zone"))

    # --- Show Result ---
    if intercepted_zones:
        st.error(f"❌ Flight path intersects with {len(intercepted_zones)} no-fly zone(s): {', '.join(intercepted_zones)}")
    else:
        st.success("✅ Flight path is safe. No intersections detected.")

    # --- Map Visualization ---
    m = folium.Map(location=[coords[0][1], coords[0][0]], zoom_start=10)

    folium.PolyLine(locations=[(y, x) for x, y in coords], color='blue', weight=4).add_to(m)

    for _, row in nfz.iterrows():
        folium.GeoJson(row.geometry, tooltip=row.get("name", "NFZ"), style_function=lambda x: {
            "fillColor": "red",
            "color": "red",
            "weight": 2,
            "fillOpacity": 0.4
        }).add_to(m)

    folium_static(m)

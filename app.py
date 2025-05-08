import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import folium_static
from shapely.geometry import box, LineString
from math import radians, sin, cos, sqrt, atan2
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut

geolocator = Nominatim(user_agent="no_fly_zone_app")

def get_place_name(lat, lon):
    try:
        location = geolocator.reverse((lat, lon), timeout=10)
        return location.address if location else "Unknown Location"
    except GeocoderTimedOut:
        return "Geocoder Timeout"


# --- Initialize Session State ---
if 'flight_path' not in st.session_state:
    st.session_state.flight_path = None

# --- Utility Functions ---
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in km
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c

def intersects_restricted_zones(flight_line, nfz):
    buffered_path = flight_line.buffer(0.01)
    intersecting_zones = nfz[nfz.geometry.intersects(buffered_path)]

    if not intersecting_zones.empty:
        conflict_points = []
        for _, zone in intersecting_zones.iterrows():
            intersection = flight_line.intersection(zone.geometry)
            if not intersection.is_empty:
                if intersection.geom_type == 'Point':
                    conflict_points.append((intersection.x, intersection.y))
                elif intersection.geom_type in ['MultiPoint', 'MultiLineString', 'GeometryCollection']:
                    for geom in intersection.geoms:
                        if geom.geom_type == 'Point':
                            conflict_points.append((geom.x, geom.y))
                        elif geom.geom_type == 'LineString':
                            midpoint = geom.interpolate(0.5, normalized=True)
                            conflict_points.append((midpoint.x, midpoint.y))
                elif intersection.geom_type == 'LineString':
                    midpoint = intersection.interpolate(0.5, normalized=True)
                    conflict_points.append((midpoint.x, midpoint.y))
                else:
                    centroid = intersection.centroid
                    conflict_points.append((centroid.x, centroid.y))

        return True, intersecting_zones, conflict_points

    return False, None, None


# --- Streamlit Setup ---
st.set_page_config(layout="wide")

st.markdown(
    """
    <h1 style='text-align: center; color: white;'>🛫 No-Fly Zone Enforcement System</h1>
    <p style='text-align: center; color: white;'>This tool detects whether a drone's flight path enters any restricted airspace zones.</p>
    """,
    unsafe_allow_html=True
)

# Load restricted zones
nfz = gpd.read_file("data/restricted_airports.geojson")
# Only convert Point geometries to bounding boxes
nfz['geometry'] = nfz.apply(lambda row: box(
    row.geometry.x - 0.1, row.geometry.y - 0.1,
    row.geometry.x + 0.1, row.geometry.y + 0.1
) if row.geometry.geom_type == 'Point' else row.geometry, axis=1)

# Columns: Input and Map
input_col, map_col = st.columns([1, 3], gap="large")

# --- Input Panel ---
with input_col:
    st.markdown("## Enter the Flight Path")
    with st.form("inputs"):
        st.markdown("### Source Coordinates")
        src_lat = st.text_input("Source Latitude:", value="37.8")
        src_lon = st.text_input("Source Longitude:", value="-96.9")

        st.markdown("### Destination Coordinates")
        dest_lat = st.text_input("Destination Latitude:")
        dest_lon = st.text_input("Destination Longitude:")

        submitted = st.form_submit_button("Submit!")
        
        if submitted:
            try:
                start_point = [float(src_lat), float(src_lon)]
                end_point = [float(dest_lat), float(dest_lon)]
                st.session_state.flight_path = [start_point, end_point]
                st.success("Flight path calculated!")
            except ValueError:
                st.error("Please enter valid latitude and longitude")


# --- Map Panel ---
with map_col:
    m = folium.Map(
        location=[37.8, -96.9],
        zoom_start=5,
        tiles="CartoDB positron",
        control_scale=True
    )

    # Add restricted zones
    folium.GeoJson(
        nfz,
        style_function=lambda x: {
            'fillColor': 'red',
            'color': 'red',
            'weight': 1,
            'fillOpacity': 0.4
        }
    ).add_to(m)

    # Initialize conflict tracking
    conflict_details = {
        'has_conflict': False,
        'zones': [],
        'points': []
    }

    # Check for intersections
    if st.session_state.flight_path:
        flight_line = LineString([(lon, lat) for lat, lon in st.session_state.flight_path])
        
        # Draw flight path
        folium.PolyLine(
            locations=st.session_state.flight_path,
            color='blue',
            weight=3,
            opacity=0.8,
            popup="Flight Path"
        ).add_to(m)

        # Add markers
        folium.Marker(
            location=st.session_state.flight_path[0],
            popup="Starting Point",
            icon=folium.Icon(color='green')
        ).add_to(m)

        folium.Marker(
            location=st.session_state.flight_path[1],
            popup="Destination",
            icon=folium.Icon(color='blue')
        ).add_to(m)

        # Check for intersections
        has_conflict, conflict_zones, conflict_points = intersects_restricted_zones(flight_line, nfz)
        conflict_details = {
            'has_conflict': has_conflict,
            'zones': conflict_zones,
            'points': conflict_points
        }
        
        if has_conflict:
            st.error("🚨 DANGER: Flight path enters restricted airspace!")
            
            # Mark conflict points
            for lon, lat in conflict_points:
                folium.Marker(
                    location=[lat, lon],
                    icon=folium.Icon(color='orange', icon='exclamation-triangle', prefix='fa'),
                    tooltip="Conflict Point"
                ).add_to(m)
            
            # Highlight conflict zones
            folium.GeoJson(
                conflict_zones,
                style_function=lambda x: {
                    'fillColor': 'darkred',
                    'color': 'darkred',
                    'weight': 4,
                    'fillOpacity': 0.8,
                    'dashArray': '5, 5'
                },
                name="Danger Zones"
            ).add_to(m)
        else:
            st.success("✅ Flight path is clear of restricted airspace")

        # Calculate bounds to fit flight path with padding
        min_lat = min(st.session_state.flight_path[0][0], st.session_state.flight_path[1][0])
        max_lat = max(st.session_state.flight_path[0][0], st.session_state.flight_path[1][0])
        min_lon = min(st.session_state.flight_path[0][1], st.session_state.flight_path[1][1])
        max_lon = max(st.session_state.flight_path[0][1], st.session_state.flight_path[1][1])
        
        # Add 10% padding around the flight path
        lat_padding = (max_lat - min_lat) * 0.1
        lon_padding = (max_lon - min_lon) * 0.1
        
        bounds = [
            [min_lat - lat_padding, min_lon - lon_padding],
            [max_lat + lat_padding, max_lon + lon_padding]
        ]
        
        # If there are conflicts, include those zones in the bounds
        if has_conflict:
            conflict_bounds = conflict_zones.geometry.total_bounds
            bounds = [
                [
                    min(bounds[0][0], conflict_bounds[1] - 0.1),  # min lat
                    min(bounds[0][1], conflict_bounds[0] - 0.1)   # min lon
                ],
                [
                    max(bounds[1][0], conflict_bounds[3] + 0.1),  # max lat
                    max(bounds[1][1], conflict_bounds[2] + 0.1)   # max lon
                ]
            ]
        
        m.fit_bounds(bounds)

    folium_static(m, width=1400, height=600)

# --- Flight Details Section ---
if submitted and st.session_state.flight_path:
    with st.expander("✈️ Flight Details", expanded=True):
        col1, col2, col3 = st.columns(3)
        lat1, lon1 = st.session_state.flight_path[0]
        lat2, lon2 = st.session_state.flight_path[1]
        distance = calculate_distance(lat1, lon1, lat2, lon2)

        departure_name = get_place_name(lat1, lon1)
        arrival_name = get_place_name(lat2, lon2)

        col1.metric("Departure", departure_name, f"{lat1:.4f}°N, {lon1:.4f}°W")
        col2.metric("Destination", arrival_name, f"{lat2:.4f}°N, {lon2:.4f}°W")
        col3.metric("Distance", f"{distance:.2f} km")

        st.write("### Flight Path Analysis")
        st.write(f"The flight from {departure_name} to {arrival_name} will cover approximately {distance:.2f} kilometers.")

        if conflict_details['has_conflict']:
            st.error("⚠️ CRITICAL WARNING: Flight path enters restricted airspace!")
            st.write("### Restricted Zones Intersected:")
            
            # Grid layout for restricted zones
            restricted_zone_grid = st.container()
            with restricted_zone_grid:
                zone_cols = st.columns(3)  # Create 3 columns for zone details
                for idx, (zone_name, zone) in enumerate(conflict_details['zones'].iterrows()):
                    zone_cols[idx % 3].markdown(f"""
                    <div class="restricted-zone-item" style="background-color: #fae9b1; padding: 10px; border-radius: 8px; margin: 8px">
                    <h5 style="color: black;">{zone.get('name', 'Unknown')}</h5>
                    <p style="color: black;"><strong>Type</strong>: {zone.get('type', 'Unspecified')}</p>
                    <p style="color: black;"><strong>Location</strong>: {zone.geometry.centroid.y:.4f}°N, {zone.geometry.centroid.x:.4f}°W</p>
                    <p style="color: black;"><strong>Distance Into Zone</strong>: {LineString(st.session_state.flight_path).intersection(zone.geometry).length:.2f} km</p>
                </div>

                    """, unsafe_allow_html=True)

            st.write("### Recommended Action:")
            st.error("""
            - Immediately alter flight path to avoid restricted airspace
            - Contact local air traffic control if already in the zone
            """)
        else:
            st.success("✅ This flight path is clear of restricted airspace")
            st.write("### Safety Check:")
            st.info("""
            - No restricted zones detected along this path
            - Maintain standard flight protocols
            - Monitor airspace for changes
            """)


# --- CSS for full-screen layout ---
# [Previous code remains exactly the same until the CSS section]

# --- CSS for full-screen layout ---
# [Previous code remains exactly the same until the CSS section]

# --- Dark Theme CSS ---
# [Keep all your Python code exactly the same until the CSS section]

st.markdown("""
<style>
/* General text */
html, body, [class*="css"] {
    font-family: 'Segoe UI', sans-serif;
    background-color: #0e1117;
    color: #f5f5f5;
}

/* Headers */
h1, h2, h3 {
    color: #4fc3f7;
    font-weight: 700;
}

/* Paragraphs and labels */
p, span, label {
    font-size: 16px;
    color: #dddddd;
}

/* Inputs and textareas */
input, textarea {
    border-radius: 8px;
    border: 1px solid #555;
    padding: 8px;
    font-size: 15px;
    background-color: #1c1f26;
    color: #f5f5f5;
}

/* Buttons */
.stButton > button {
    background-color: #26de81;
    color: white;
    padding: 10px 20px;
    border-radius: 6px;
    border: none;
    font-weight: bold;
    transition: background-color 0.3s ease;
}
.stButton > button:hover {
    background-color: #20bf6b;
}

/* Tables */
table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 10px;
}
table, th, td {
    border: 1px solid #444;
    padding: 8px;
}
th {
    background-color: #37474f;
    color: #ffffff;
}
td {
    background-color: #1e272e;
    color: #f1f2f6;
}

/* Map iframe */
iframe {
    border-radius: 10px;
    border: 1px solid #333;
    margin-top: 10px;
}

/* Alert styles */
.alert-danger {
    background-color: #ff6b6b;
    color: white;
    padding: 10px;
    border-radius: 6px;
}
.alert-success {
    background-color: #1dd1a1;
    color: white;
    padding: 10px;
    border-radius: 6px;
}

/* Map Restricted Zone Fix */
.restricted-zone {
    background-color: rgba(255, 0, 0, 0.6); /* Semi-transparent red */
    border: 2px solid #ff3b30; /* Strong red outline */
    color: #fff;
}
</style>
""", unsafe_allow_html=True)

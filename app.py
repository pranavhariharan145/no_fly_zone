import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import folium_static
from shapely.geometry import box, LineString

# 1. Configure page for full-width layout
st.set_page_config(layout="wide")

# 2. Load and process data
nfz = gpd.read_file("data/restricted_airports.geojson")
nfz['geometry'] = nfz.apply(lambda row: box(
    row.geometry.x - 0.1, row.geometry.y - 0.1,
    row.geometry.x + 0.1, row.geometry.y + 0.1
), axis=1)

# 3. Create two columns (25% for inputs, 75% for map)
input_col, map_col = st.columns([1, 3], gap="large")

# Initialize flight path in session state
if 'flight_path' not in st.session_state:
    st.session_state.flight_path = None

# 4. Input Panel (Left)
with input_col:
    st.markdown("## Enter the Flight")
    with st.form("inputs"):
        lat = st.text_input("Enter Latitude:")
        lon = st.text_input("Enter Longitude:")
        submitted = st.form_submit_button("Submit!")
        
        if submitted:
            try:
                # Create flight path from center of US to entered coordinates
                start_point = [37.8, -96.9]  # Center of US
                end_point = [float(lat), float(lon)]
                st.session_state.flight_path = [start_point, end_point]
                st.success("Flight path calculated!")
            except ValueError:
                st.error("Please enter valid latitude and longitude")

# 5. Full-Screen Map (Right)
with map_col:
    # Create map centered on USA with higher zoom
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
    
    # Draw flight path if it exists
    if st.session_state.flight_path:
        folium.PolyLine(
            locations=st.session_state.flight_path,
            color='blue',
            weight=3,
            opacity=0.8,
            popup="Flight Path"
        ).add_to(m)
        
        # Add markers for start and end points
        folium.Marker(
            location=st.session_state.flight_path[0],
            popup="Starting Point (US Center)",
            icon=folium.Icon(color='green')
        ).add_to(m)
        
        folium.Marker(
            location=st.session_state.flight_path[1],
            popup="Destination",
            icon=folium.Icon(color='blue')
        ).add_to(m)
    
    m.fit_bounds(m.get_bounds())
    folium_static(m, width=1400, height=800)

# 6. CSS remains the same
st.markdown("""
<style>
    /* Remove all default padding/margins */
    .main .block-container {
        padding: 0;
        max-width: 100%;
    }
    
    /* Full-height map container */
    .element-container:has(.folium-map) {
        height: calc(100vh - 50px) !important;
        padding: 0 !important;
        margin: 0 !important;
    }
    
    /* Map itself */
    .folium-map {
        height: 100% !important;
        width: 100% !important;
        min-height: 800px;
        border: none;
    }
    
    /* Right column (map) */
    div[data-testid="column"]:nth-of-type(2) {
        padding: 0 !important;
        margin: 0 !important;
    }
    
    /* Left column (inputs) */
    div[data-testid="column"]:nth-of-type(1) {
        padding: 20px;
    }
</style>
""", unsafe_allow_html=True)
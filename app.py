import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import folium_static
from shapely.geometry import box

# Load GeoJSON
nfz = gpd.read_file("/home/pranav/repos/no_fly_zone/data/restricted_airports.geojson")

# Define buffer size in degrees (~0.1 = ~10km)
buffer_size = 0.1

# Create square boxes around each point
def point_to_square(lat, lon, size):
    return box(lon - size, lat - size, lon + size, lat + size)

# Apply square conversion
nfz['geometry'] = nfz.apply(
    lambda row: point_to_square(row.geometry.y, row.geometry.x, buffer_size),
    axis=1
)

# Initialize Map
m = folium.Map(location=[20, 0], zoom_start=2)

# Show squares on the map
folium.GeoJson(
    nfz,
    name="Restricted Zones",
    tooltip=folium.GeoJsonTooltip(fields=["name", "type"]),
    style_function=lambda x: {
        'fillColor': 'red',
        'color': 'red',
        'weight': 1,
        'fillOpacity': 0.4
    }
).add_to(m)

# Fit to bounds of restricted airspaces (if bounds are available)
m.fit_bounds(m.get_bounds())

# Display the map
folium_static(m)

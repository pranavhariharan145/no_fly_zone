import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

# Load the CSV
df = pd.read_csv("/home/pranav/repos/no_fly_zone/data/airports.csv")

# Filter military or closed airports
restricted_df = df[df['type'].isin(['military', 'closed', 'military_airport'])]

# Drop rows with missing coordinates
restricted_df = restricted_df.dropna(subset=['latitude_deg', 'longitude_deg'])

print(restricted_df[['name', 'latitude_deg', 'longitude_deg', 'type']].head())



# Convert to GeoDataFrame
gdf = gpd.GeoDataFrame(
    restricted_df,
    geometry=[Point(xy) for xy in zip(restricted_df.longitude_deg, restricted_df.latitude_deg)],
    crs="EPSG:4326"
)

# Save as GeoJSON
gdf[['name', 'type', 'geometry']].to_file("data/restricted_airports.geojson", driver="GeoJSON")



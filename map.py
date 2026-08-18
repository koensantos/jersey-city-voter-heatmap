import folium
import geopandas as gpd
import pandas as pd
from pathlib import Path
import re


# Read voter data
data = pd.read_csv("voting_data.csv", header=None)

# Candidate names
candidates = [
    "JOYCE E. WATTERMAN",
    "MUSSAB ALI",
    "KALKI JAYNE-ROSE",
    "JIM McGREEVEY",
    "BILL O'DEA",
    "JAMES SOLOMON",
    "CHRISTINA L. FREEMAN",
    "Write-In Vote"
]

# Actual election data starts on row 3
voter_data = data.iloc[3:].copy()

# Rename first columns
voter_data = voter_data.rename(columns={
    0: "Precinct",
    1: "Registered Voters"
})


# Get the Total Votes column for each candidate
# Each candidate has:
# Election Day, Early Voting, Mail-In, Provisional, Overseas, Total Votes

for i, candidate in enumerate(candidates):

    total_column = 2 + (i * 6) + 5

    voter_data = voter_data.rename(
        columns={total_column: candidate}
    )


# Keep only the columns we need
voter_data = voter_data[
    ["Precinct"] + candidates
].copy()


# Clean precinct names
voter_data["Precinct"] = (
    voter_data["Precinct"]
    .astype(str)
    .str.strip()
)


# Convert candidate votes to numbers
for candidate in candidates:

    voter_data[candidate] = pd.to_numeric(
        voter_data[candidate],
        errors="coerce"
    ).fillna(0)


# Combine districts such as:
# District 32A
# District 32B
#
# into:
# District 32

voter_data["Precinct"] = voter_data["Precinct"].apply(
    lambda x: re.sub(
        r"District (\d+)[A-Z]$",
        r"District \1",
        x
    )
)


# Combine the votes for split districts
voter_data = voter_data.groupby(
    "Precinct",
    as_index=False
)[candidates].sum()


# Find the winner of each district
voter_data["Winner"] = voter_data[
    candidates
].idxmax(axis=1)

voter_data["Winner Votes"] = voter_data[
    candidates
].max(axis=1)


# Candidate colors
colors = {
    "JOYCE E. WATTERMAN": "blue",
    "MUSSAB ALI": "yellow",
    "KALKI JAYNE-ROSE": "green",
    "JIM McGREEVEY": "red",
    "BILL O'DEA": "purple",
    "JAMES SOLOMON": "green",
    "CHRISTINA L. FREEMAN": "pink",
    "Write-In Vote": "gray"
}


# Create OpenStreetMap map
m = folium.Map(
    location=[40.7178, -74.0431],
    zoom_start=13,
    tiles="OpenStreetMap"
)


# Find all district GeoJSON files
district_files = Path("districts").glob("*.geojson")


for filepath in district_files:

    # Read GeoJSON
    gdf = gpd.read_file(filepath)

    # Convert to latitude/longitude
    gdf = gdf.to_crs(epsg=4326)


    # Get filename
    filename = filepath.stem.lower()


    # Extract ward and district number
    match = re.match(
        r"ward([a-z])district0*(\d+)",
        filename
    )

    if not match:
        print("Could not identify district:", filename)
        continue


    ward = match.group(1).upper()
    district = match.group(2)


    # Create name that matches voter_data.csv
    district_name = (
        f"Jersey City Ward {ward} District {int(district)}"
    )


    # Find election results
    result = voter_data[
        voter_data["Precinct"] == district_name
    ]


    # Skip districts that don't have election data
    if result.empty:
        print("No voter data found for:", district_name)
        continue


    # Get the row
    result = result.iloc[0]


    # Get winner
    winner = result["Winner"]
    winner_votes = result["Winner Votes"]


    # Calculate total votes in the district
    total_votes = result[candidates].sum()


    # Calculate how dominant the winner was
    if total_votes > 0:
        opacity = winner_votes / total_votes
    else:
        opacity = 0.3


    # Don't make districts too transparent
    opacity = max(0.3, opacity)


    # Tooltip
    tooltip = (
        f"{district_name}<br>"
        f"Winner: {winner}<br>"
        f"Votes: {int(winner_votes)}<br>"
        f"Vote Share: {winner_votes / total_votes:.1%}"
    )


    # Add district to map
    folium.GeoJson(
        gdf,
        name=district_name,

        style_function=lambda feature,
        color=colors.get(winner, "gray"),
        opacity=opacity: {
            "fillColor": color,
            "color": "black",
            "weight": 1,
            "fillOpacity": opacity
        },

        tooltip=tooltip

    ).add_to(m)


# Add layer controls
folium.LayerControl().add_to(m)


# Save map
m.save("jersey_city_wards.html")


print("Map created successfully!")
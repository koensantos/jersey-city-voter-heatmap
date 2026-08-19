import folium
import geopandas as gpd
import pandas as pd
from pathlib import Path
import re


# Read voter data
data = pd.read_csv("voting_data.csv", header=None)

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

# Election data starts on row 3
voter_data = data.iloc[3:].copy()

voter_data = voter_data.rename(columns={
    0: "Precinct",
    1: "Registered Voters"
})


# Each candidate has 6 columns:
# Election Day, Early Voting, Mail-In, Provisional, Overseas, Total Votes

for i, candidate in enumerate(candidates):

    total_column = 2 + (i * 6) + 5

    voter_data = voter_data.rename(
        columns={total_column: candidate}
    )


# Find the overall Total column
# There are 8 candidates, each with 6 columns
overall_total_column = 2 + (len(candidates) * 6)

voter_data = voter_data.rename(
    columns={overall_total_column: "Total Votes"}
)


# Keep the columns we need
voter_data = voter_data[
    ["Precinct", "Registered Voters", "Total Votes"] + candidates
].copy()


# Clean up the data
voter_data["Precinct"] = (
    voter_data["Precinct"]
    .astype(str)
    .str.strip()
)

voter_data["Registered Voters"] = pd.to_numeric(
    voter_data["Registered Voters"],
    errors="coerce"
).fillna(0)

voter_data["Total Votes"] = pd.to_numeric(
    voter_data["Total Votes"],
    errors="coerce"
).fillna(0)


for candidate in candidates:

    voter_data[candidate] = pd.to_numeric(
        voter_data[candidate],
        errors="coerce"
    ).fillna(0)


# Combine districts like:
# District 32A + District 32B
# into District 32

voter_data["Precinct"] = voter_data["Precinct"].apply(
    lambda x: re.sub(
        r"District (\d+)[A-Z]$",
        r"District \1",
        x
    )
)


# Combine split districts
voter_data = voter_data.groupby(
    "Precinct",
    as_index=False
)[["Registered Voters", "Total Votes"] + candidates].sum()


# Find winner and second place
def get_results(row):

    votes = row[candidates].sort_values(ascending=False)

    winner = votes.index[0]
    winner_votes = votes.iloc[0]

    second_place = votes.index[1]
    second_votes = votes.iloc[1]

    margin = winner_votes - second_votes

    return pd.Series({
        "Winner": winner,
        "Winner Votes": winner_votes,
        "Second Place": second_place,
        "Second Place Votes": second_votes,
        "Margin": margin
    })


results = voter_data.apply(
    get_results,
    axis=1
)

voter_data = pd.concat(
    [voter_data, results],
    axis=1
)


# Candidate colors
colors = {
    "JOYCE E. WATTERMAN": "#377eb8",
    "MUSSAB ALI": "#ff7f00",
    "KALKI JAYNE-ROSE": "#4daf4a",
    "JIM McGREEVEY": "#e41a1c",
    "BILL O'DEA": "#984ea3",
    "JAMES SOLOMON": "#a65628",
    "CHRISTINA L. FREEMAN": "#f781bf",
    "Write-In Vote": "#999999"
}


# Create map
m = folium.Map(
    location=[40.7178, -74.0431],
    zoom_start=13,
    tiles="OpenStreetMap"
)


# Find all district files
district_files = Path("districts").glob("*.geojson")


for filepath in district_files:

    gdf = gpd.read_file(filepath)

    gdf = gdf.to_crs(epsg=4326)

    filename = filepath.stem.lower()

    match = re.match(
        r"ward([a-z])district0*(\d+)",
        filename
    )

    if not match:
        print("Could not identify district:", filename)
        continue

    ward = match.group(1).upper()
    district = int(match.group(2))

    district_name = (
        f"Jersey City Ward {ward} District {district}"
    )


    # Find election results
    result = voter_data[
        voter_data["Precinct"] == district_name
    ]


    if result.empty:

        print("No voter data found for:", district_name)

        folium.GeoJson(
            gdf,
            name=district_name,
            style_function=lambda feature: {
                "fillColor": "gray",
                "color": "black",
                "weight": 1,
                "fillOpacity": 0.25
            },
            tooltip=district_name
        ).add_to(m)

        continue


    result = result.iloc[0]


    # Election information
    winner = result["Winner"]
    winner_votes = result["Winner Votes"]

    second_place = result["Second Place"]
    second_votes = result["Second Place Votes"]

    margin = result["Margin"]

    registered = result["Registered Voters"]
    total_votes = result["Total Votes"]


    # Calculate turnout
    if registered > 0:
        turnout = total_votes / registered
    else:
        turnout = 0


    # Calculate winner's share
    if total_votes > 0:
        winner_share = winner_votes / total_votes
        margin_share = margin / total_votes
    else:
        winner_share = 0
        margin_share = 0


    # Keep the intensity between 0.25 and 0.9
    opacity = 0.25 + (margin_share * 2)

    opacity = min(opacity, 0.9)


    # Get candidate color
    color = colors.get(
        winner,
        "gray"
    )


    # Tooltip
    tooltip = f"""
    <b>{district_name}</b><br><br>

    <b>Winner:</b> {winner}<br>
    <b>Winner votes:</b> {int(winner_votes)}<br>
    <b>Second:</b> {second_place} ({int(second_votes)})<br>
    <b>Margin:</b> {int(margin)} votes<br>
    <b>Winner share:</b> {winner_share:.1%}<br><br>

    <b>Registered voters:</b> {int(registered)}<br>
    <b>Total votes:</b> {int(total_votes)}<br>
    <b>Turnout:</b> {turnout:.1%}
    """


    # Add district
    folium.GeoJson(
        gdf,
        name=district_name,

        style_function=lambda feature,
        color=color,
        opacity=opacity: {
            "fillColor": color,
            "color": "black",
            "weight": 1,
            "fillOpacity": opacity
        },

        tooltip=folium.Tooltip(tooltip)

    ).add_to(m)


# Legend
legend_items = ""

for candidate, color in colors.items():

    legend_items += f"""
    <div style="margin-bottom: 5px;">
        <span style="
            display:inline-block;
            width:15px;
            height:15px;
            background:{color};
            margin-right:6px;
            border:1px solid black;
        "></span>
        {candidate}
    </div>
    """


legend_html = f"""
<div style="
    position: fixed;
    bottom: 30px;
    left: 30px;
    width: 230px;
    background-color: white;
    border: 2px solid black;
    z-index: 9999;
    padding: 10px;
    font-size: 13px;
">

<b>District Winner</b>

<hr>

{legend_items}

<hr>

<b>Color intensity</b><br>
Lighter = closer race<br>
Darker = larger margin

</div>
"""


m.get_root().html.add_child(
    folium.Element(legend_html)
)


# Layer controls
folium.LayerControl().add_to(m)


# Save map
m.save("jersey_city_wards.html")

print("Map created successfully!")
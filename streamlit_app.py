# app.py
import math
import os
import io
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # headless backend
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from matplotlib.collections import PatchCollection
from matplotlib.colors import Normalize
import matplotlib.cm as cm
import streamlit as st

# ---------------------------
# Page config and styles
# ---------------------------
st.set_page_config(layout="wide", page_title="Hex Map India")
st.markdown(
    """
    <style>
    body {background-color: #EDE8D0; font-family: 'Quincy', sans-serif;}
    </style>
    """,
    unsafe_allow_html=True
)

# ---------------------------
# Hex grid helpers
# ---------------------------
def hex_vertices(x, y, r=1, orientation="flat"):
    start_deg = 30 if orientation=="pointy" else 0
    return [(x + r*math.cos(math.radians(start_deg + 60*i)),
             y + r*math.sin(math.radians(start_deg + 60*i))) for i in range(6)]

def make_hex_grid(rows=10, cols=10, r=1, orientation="flat"):
    if orientation == "pointy":
        w = math.sqrt(3)*r
        h = 2*r
        h_spacing = w
        v_spacing = 3/4*h
    else:
        w = 2*r
        h = math.sqrt(3)*r
        h_spacing = 3/4*w
        v_spacing = h

    hexes = []
    for row in range(rows):
        for col in range(cols):
            cx = col*h_spacing
            cy = row*v_spacing + (col%2)*(v_spacing/2) if orientation=="flat" else row*v_spacing
            hexes.append({
                "hex_id": row*cols + col,
                "row": row,
                "col": col,
                "cx": cx,
                "cy": cy,
                "verts": hex_vertices(cx, cy, r, orientation)
            })
    return pd.DataFrame(hexes)

# ---------------------------
# Plotting matched hexes
# ---------------------------
def plot_matched_hexes(hex_grid, merged_df, code_col="code", value_col="value", cmap_name="viridis", hex_size=1, title=None):
    if merged_df.empty:
        fig, ax = plt.subplots(figsize=(6,4))
        ax.text(0.5,0.5,"No matched hexes to plot",ha="center",va="center")
        ax.set_axis_off()
        return fig

    # Prepare colormap
    vals = None
    if value_col in merged_df.columns:
        vals = pd.to_numeric(merged_df[value_col], errors="coerce")
        vmin, vmax = vals.min(), vals.max()
        cmap = plt.colormaps.get(cmap_name)
        norm = Normalize(vmin=vmin, vmax=vmax)
    else:
        cmap, norm = None, None

    # Build polygons
    patches, facecolors = [], []
    for _, row in merged_df.iterrows():
        poly = Polygon(row["verts"], closed=True, edgecolor="black", linewidth=0.5)
        patches.append(poly)
        if value_col in row and pd.notna(row[value_col]) and cmap:
            facecolors.append(cmap(norm(float(row[value_col]))))
        else:
            facecolors.append((0.92,0.92,0.92,1))

    fig, ax = plt.subplots(figsize=(8,8))
    collection = PatchCollection(patches, facecolor=facecolors, match_original=True)
    ax.add_collection(collection)

    # Labels (always code)
    for _, row in merged_df.iterrows():
        label = row.get(code_col, str(int(row["hex_id"])))
        ax.text(row["cx"], row["cy"], label, ha="center", va="center", fontsize=6, fontname="Inter")

    ax.set_aspect("equal")
    ax.autoscale()
    ax.margins(0.05)
    ax.set_axis_off()

    # Title
    if title:
        ax.set_title(title, fontname="Inter")

    # Colorbar
    if vals is not None and not vals.isnull().all():
        from matplotlib.cm import ScalarMappable
        sm = ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array(vals)
        fig.colorbar(sm, ax=ax, fraction=0.046, pad=0.04, label=value_col)

    return fig

# ---------------------------
# Sidebar — download/upload + controls
# ---------------------------
st.sidebar.title("Hex Map India")

# Step 1: Download template
st.sidebar.markdown("### Step 1 — Download Template")
TEMPLATE_CODES = [
    "AN","AP","AR","AS","BR","CH","CG","DL","DH","GA","GJ","HR","HP",
    "JK","JH","KA","KL","LA","LD","MP","MH","MN","ML","MZ","NL","OD",
    "PY","PB","RJ","SK","TN","TS","TR","UP","UK","WB"
]
TEMPLATE_STATES = [
    "Andaman and Nicobar Islands","Andhra Pradesh","Arunachal Pradesh",
    "Assam","Bihar","Chandigarh","Chhattisgarh","Delhi",
    "Dadra and Nagar Haveli and Daman and Diu","Goa","Gujarat",
    "Haryana","Himachal Pradesh","Jammu and Kashmir","Jharkhand",
    "Karnataka","Kerala","Ladakh","Lakshadweep","Madhya Pradesh",
    "Maharashtra","Manipur","Meghalaya","Mizoram","Nagaland","Odisha",
    "Puducherry","Punjab","Rajasthan","Sikkim","Tamil Nadu","Telangana",
    "Tripura","Uttar Pradesh","Uttarakhand","West Bengal"
]

# Map title row (single cell)
map_title_row = pd.DataFrame({
    "map_title": ["Hex Map India"],
    "code": [""],
    "state": [""],
    "value": [""]
})
# Main table
template_table = pd.DataFrame({
    "code": TEMPLATE_CODES,
    "state": TEMPLATE_STATES,
    "value": ["" for _ in TEMPLATE_CODES]
})
# Combine
template_df = pd.concat([map_title_row, template_table], ignore_index=True)

st.sidebar.download_button(
    "Download Template CSV",
    data=template_df.to_csv(index=False),
    file_name="hex_map_template.csv",
    mime="text/csv"
)

# Step 2: Upload file
uploaded = st.sidebar.file_uploader("### Step 2 — Upload Edited CSV", type=["csv"])

# Colormap selector
cmap = st.sidebar.selectbox("Colormap", options=sorted(plt.colormaps()), index=plt.colormaps().index("viridis"))

# Hex size
hex_size = st.sidebar.slider("Hex Size", min_value=0.5, max_value=2.0, value=1.0, step=0.1)

# ---------------------------
# Build hex grid
# ---------------------------
hex_grid = make_hex_grid(rows=10, cols=10, r=hex_size, orientation="flat")

# ---------------------------
# Show map before upload (gray)
# ---------------------------
st.write("## Hex Map Preview (before upload)")
preview_df = hex_grid.copy()
preview_df["code"] = None
preview_df["value"] = None
fig = plot_matched_hexes(hex_grid, preview_df, code_col="code", value_col="value", hex_size=hex_size)
st.pyplot(fig)
st.caption("Made with Hex Map India")

# ---------------------------
# Process uploaded CSV
# ---------------------------
map_title = "Hex Map India"  # default

if uploaded is not None:
    try:
        user_df = pd.read_csv(uploaded)
    except Exception as e:
        st.error(f"Could not read uploaded CSV: {e}")
        st.stop()

    # Standardize columns
    rename_map = {}
    for c in user_df.columns:
        lc = c.lower()
        if lc == "state":
            rename_map[c] = "state"
        elif lc == "code":
            rename_map[c] = "code"
        elif lc == "value":
            rename_map[c] = "value"
        elif lc == "hex_id":
            rename_map[c] = "hex_id"
        elif lc == "map_title":
            rename_map[c] = "map_title"
    user_df = user_df.rename(columns=rename_map)

    # Map title from first row
    if "map_title" in user_df.columns:
        first_title = str(user_df.loc[0, "map_title"])
        if first_title.strip():
            map_title = first_title

    # Merge user values with hex grid on 'code'
    if "code" in user_df.columns:
        merged_df = hex_grid.merge(user_df, on="code", how="left")
        st.write(f"## {map_title}")
        fig = plot_matched_hexes(hex_grid, merged_df, code_col="code", value_col="value",
                                 cmap_name=cmap, hex_size=hex_size, title=None)
        st.pyplot(fig)
        st.caption("Made with Hex Map India")
    else:
        st.warning("Uploaded CSV must contain a 'code' column.")

# app.py
import math
import io
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # headless backend for Streamlit Cloud
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from matplotlib.collections import PatchCollection
from matplotlib.colors import Normalize
import streamlit as st

# --- Page setup ---
st.set_page_config(layout="wide", page_title="Hex Map India")

# --- Global style ---
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');
    body, .stApp {
        background-color: #EDE8D0;
        font-family: "Inter", "Inter UI", sans-serif;
    }
    .main .block-container {
        padding-top: 1rem;
        padding-bottom: 1.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)
plt.rcParams["font.family"] = "Inter"

# --- Create hex grid ---
def hex_vertices(x, y, r=1, orientation="flat"):
    start_deg = 30 if orientation == "pointy" else 0
    return [
        (x + r * math.cos(math.radians(start_deg + 60 * i)),
         y + r * math.sin(math.radians(start_deg + 60 * i)))
        for i in range(6)
    ]

def make_hex_grid(rows=10, cols=10, r=1, orientation="flat"):
    if orientation == "pointy":
        w, h = math.sqrt(3)*r, 2*r
        h_spacing, v_spacing = w, 3/4*h
    else:
        w, h = 2*r, math.sqrt(3)*r
        h_spacing, v_spacing = 3/4*w, h
    hexes = []
    for row in range(rows):
        for col in range(cols):
            if orientation == "pointy":
                cx = col*h_spacing + (row % 2)*(h_spacing/2)
                cy = row*v_spacing
            else:
                cx = col*h_spacing
                cy = row*v_spacing + (col % 2)*(v_spacing/2)
            hexes.append({
                "hex_id": row*cols + col,
                "cx": cx,
                "cy": cy,
                "verts": hex_vertices(cx, cy, r, orientation)
            })
    return pd.DataFrame(hexes)

# --- Plot helper ---
def plot_matched_hexes(merged_df, cmap_name="viridis"):
    if merged_df.empty:
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.text(0.5, 0.5, "No matched hexes found", ha="center", va="center")
        ax.axis("off")
        return fig

    vals = pd.to_numeric(merged_df["value"], errors="coerce")
    cmap = matplotlib.colormaps.get(cmap_name)
    norm = Normalize(vmin=vals.min(), vmax=vals.max())

    patches, facecolors = [], []
    for _, row in merged_df.iterrows():
        poly = Polygon(row["verts"], closed=True, edgecolor="black", linewidth=0.5)
        patches.append(poly)
        val = row["value"]
        if pd.isna(val):
            facecolors.append((1, 1, 1, 1))
        else:
            facecolors.append(cmap(norm(float(val))))

    fig, ax = plt.subplots(figsize=(8, 8))
    ax.add_collection(PatchCollection(patches, facecolor=facecolors, match_original=True))

    for _, row in merged_df.iterrows():
        label = str(row["code"])
        ax.text(row["cx"], row["cy"], label, ha="center", va="center", fontsize=8)

    ax.set_aspect("equal")
    ax.autoscale()
    ax.margins(0.05)
    ax.axis("off")

    from matplotlib.cm import ScalarMappable
    sm = ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array(vals)
    fig.colorbar(sm, ax=ax, fraction=0.046, pad=0.04, label="Value")
    return fig

# --- Sidebar setup ---
# --- Sidebar: Step 1 — Download template ---
st.sidebar.markdown("## Step 1 — Download template")

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

# 1️⃣ Main table
template_table = pd.DataFrame({
    "code": TEMPLATE_CODES,
    "state": TEMPLATE_STATES,
    "value": ["" for _ in TEMPLATE_CODES]
})

# 2️⃣ Single-row map title at top
map_title_row = pd.DataFrame({
    "map_title": ["Hex Map India"],  # only one cell
    "code": [""],
    "state": [""],
    "value": [""]
})

# 3️⃣ Combine top title + table
final_template = pd.concat([map_title_row, template_table], ignore_index=True)

# 4️⃣ Download button
st.sidebar.download_button(
    "Download template CSV",
    data=final_template.to_csv(index=False),
    file_name="hex_map_template.csv",
    mime="text/csv"
)

st.sidebar.markdown("---")
st.sidebar.markdown("## Step 2 — Upload your file")
uploaded = st.sidebar.file_uploader("Upload CSV (code,state,value,map_title)", type=["csv"])

st.sidebar.markdown("---")
cmap_name = st.sidebar.selectbox("Colormap", options=sorted(matplotlib.colormaps), index=sorted(matplotlib.colormaps).index("viridis"))
hex_radius = st.sidebar.slider("Hex size", 0.4, 2.0, 1.0, 0.1)
st.sidebar.markdown("---")

# Colorbar preview
st.sidebar.write("Colorbar preview:")
cb_fig, cb_ax = plt.subplots(figsize=(2.2, 0.5))
cb_ax.set_axis_off()
cmap_obj = matplotlib.colormaps.get(cmap_name)
norm = Normalize(vmin=0, vmax=100)
from matplotlib.cm import ScalarMappable
sm = ScalarMappable(cmap=cmap_obj, norm=norm)
sm.set_array([])
cb_fig.colorbar(sm, ax=cb_ax, orientation="horizontal", fraction=0.9, pad=0.1)
st.sidebar.pyplot(cb_fig)
plt.close(cb_fig)

# --- Main content ---
if uploaded is None:
    st.info("⬅️ Upload a CSV file to visualize matched hexes.")
    st.stop()

try:
    df = pd.read_csv(uploaded)
except Exception as e:
    st.error(f"Error reading CSV: {e}")
    st.stop()

# Normalize column names
df.columns = [c.lower() for c in df.columns]

for col in ["code", "value"]:
    if col not in df.columns:
        st.error(f"Your CSV must include '{col}' column.")
        st.stop()

# --- Determine map title ---
map_title = "Hex Map India"  # default
if "map_title" in df.columns:
    titles = df["map_title"].dropna().unique()
    if len(titles) > 0:
        map_title = str(titles[0])
st.subheader(map_title)

# --- Generate hex map ---
hex_grid = make_hex_grid(rows=10, cols=10, r=hex_radius)
hex_grid["code"] = TEMPLATE_CODES  # assume mapping 1:1 for demo
merged = pd.merge(df, hex_grid, on="code", how="inner")

if merged.empty:
    st.warning("No matching codes found. Ensure your 'code' values match template (e.g., 'AP', 'MH').")
    st.stop()

fig = plot_matched_hexes(merged, cmap_name=cmap_name)
st.pyplot(fig)

# --- Download PNG ---
buf = io.BytesIO()
fig.savefig(buf, dpi=150, bbox_inches="tight")
buf.seek(0)
st.download_button("Download Map as PNG", buf, file_name="hex_map.png", mime="image/png")

# --- Preview table ---
st.subheader("Matched Data Preview")
st.dataframe(merged[["code", "state", "value"]].head(50))

st.markdown("---")
st.markdown("<div style='text-align:center;font-size:12px;'>Made with ❤️ using Streamlit</div>", unsafe_allow_html=True)

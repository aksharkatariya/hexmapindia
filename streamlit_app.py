# app.py
import math
import io
import os
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # headless backend for Streamlit Cloud
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from matplotlib.collections import PatchCollection
import matplotlib.cm as cm
from matplotlib.colors import Normalize
import streamlit as st

# Page config
st.set_page_config(layout="wide", page_title="Hex Map India")

# Inject styles: background color and fonts (best-effort)
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');
    body, .css-18e3th9, .stApp {
        background-color: #EDE8D0;
        font-family: "Quincy", "Inter", system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial;
    }
    .css-1d391kg { max-width: 320px; }
    .main .block-container{
        padding-top: 1rem;
        padding-bottom: 1.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Matplotlib font preference for plots (best-effort)
plt.rcParams["font.family"] = "Inter"

# -----------------------
# Small fixed hex grid (10x10, flat)
# -----------------------
def hex_vertices(x, y, r=1, orientation="flat"):
    start_deg = 30 if orientation == "pointy" else 0
    return [
        (x + r * math.cos(math.radians(start_deg + 60 * i)),
         y + r * math.sin(math.radians(start_deg + 60 * i)))
        for i in range(6)
    ]

def make_hex_grid(rows=10, cols=10, r=1, orientation="flat"):
    if orientation == "pointy":
        w = math.sqrt(3) * r
        h = 2 * r
        h_spacing = w
        v_spacing = 3/4 * h
    else:
        w = 2 * r
        h = math.sqrt(3) * r
        h_spacing = 3/4 * w
        v_spacing = h

    hexes = []
    for row in range(rows):
        for col in range(cols):
            if orientation == "pointy":
                cx = col * h_spacing + (row % 2) * (h_spacing / 2)
                cy = row * v_spacing
            else:
                cx = col * h_spacing
                cy = row * v_spacing + (col % 2) * (v_spacing / 2)
            hexes.append({
                "hex_id": int(row * cols + col),
                "row": int(row),
                "col": int(col),
                "cx": float(cx),
                "cy": float(cy),
                "verts": hex_vertices(cx, cy, r, orientation)
            })
    return pd.DataFrame(hexes)

# -----------------------
# Local mapping loader (optional)
# -----------------------
LOCAL_MAPPING_FILENAME = "state_hex_key.csv"

def load_local_mapping(path):
    try:
        df = pd.read_csv(path)
        cols_lower = [c.lower() for c in df.columns]
        if "hex_id" in cols_lower and "code" in cols_lower:
            df = df.rename(columns={df.columns[cols_lower.index("hex_id")]: "hex_id",
                                    df.columns[cols_lower.index("code")]: "code"})
        else:
            if len(df.columns) >= 2:
                df = df.rename(columns={df.columns[0]: "hex_id", df.columns[1]: "code"})
        df = df[["hex_id", "code"]].copy()
        df["hex_id"] = pd.to_numeric(df["hex_id"], errors="coerce").astype("Int64")
        df["code"] = df["code"].astype(str).str.replace("[^A-Za-z]", "", regex=True).str.upper().str[-2:]
        return df.dropna(subset=["hex_id"]).reset_index(drop=True)
    except Exception:
        return None

# -----------------------
# Plotting helper — only matched hexes displayed
# -----------------------
def plot_matched_hexes(hex_grid, merged_df, code_col="code", value_col="value", cmap_name="viridis"):
    """
    Plot merged_df (which should include hex_grid geometry via merge).
    Returns (fig, ax, vals) where vals is the numeric array used for colorbar (or None).
    """
    if merged_df is None or merged_df.empty:
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.text(0.5, 0.5, "No matched hexes to plot", ha="center", va="center")
        ax.set_axis_off()
        return fig, ax, None

    # Prepare color mapping
    vals = None
    cmap_obj = None
    norm = None
    if value_col in merged_df.columns:
        vals = pd.to_numeric(merged_df[value_col], errors="coerce")
        vmin, vmax = vals.min(), vals.max()
        cmap_obj = matplotlib.colormaps.get(cmap_name)
        norm = Normalize(vmin=vmin, vmax=vmax)

    patches, facecolors = [], []
    for _, row in merged_df.iterrows():
        poly = Polygon(row["verts"], closed=True, edgecolor="black", linewidth=0.5)
        patches.append(poly)
        if value_col in row.index and cmap_obj is not None:
            val = row[value_col]
            if pd.isna(val):
                facecolors.append((1, 1, 1, 1))
            else:
                facecolors.append(cmap_obj(norm(float(val))))
        else:
            facecolors.append((0.92, 0.92, 0.92, 1))

    fig, ax = plt.subplots(figsize=(8, 8))
    collection = PatchCollection(patches, facecolor=facecolors, match_original=True)
    ax.add_collection(collection)

    # labels: always show code (fallback to hex_id)
    for _, row in merged_df.iterrows():
        if pd.notna(row.get(code_col)):
            label = row.get(code_col)
        else:
            label = str(int(row["hex_id"]))
        ax.text(row["cx"], row["cy"], label, ha="center", va="center", fontsize=8)

    ax.set_aspect("equal")
    ax.autoscale()
    ax.margins(0.05)
    ax.set_axis_off()

    # return fig and vals for later colorbar handling
    return fig, ax, vals

# -----------------------
# Template data (provided list)
# -----------------------
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

template_df = pd.DataFrame({
    "code": TEMPLATE_CODES,
    "state": TEMPLATE_STATES,
    "value": ["" for _ in TEMPLATE_CODES]
})

# -----------------------
# Sidebar: Step 1 download, Step 2 upload, colormap + hex size, colorbar preview
# -----------------------
st.sidebar.markdown("## Step 1 — Download template")
st.sidebar.write("Download the pre-filled template, add `value` for the codes you want to plot, then re-upload.")
st.sidebar.download_button(
    "Download template (code,state,value)",
    data=template_df.to_csv(index=False),
    file_name="hex_map_template.csv",
    mime="text/csv"
)

st.sidebar.markdown("---")
st.sidebar.markdown("## Step 2 — Upload edited file")
uploaded = st.sidebar.file_uploader("Upload CSV (code,state,value). Optionally include hex_id to place directly.", type=["csv"])

col1, col2 = st.sidebar.columns([2, 1])
with col1:
    cmap_name = st.selectbox("Colormap", options=sorted(m for m in plt.colormaps()), index=plt.colormaps().index("viridis"))
with col2:
    hex_radius = st.slider("Hex size", min_value=0.4, max_value=2.0, value=1.0, step=0.1)

st.sidebar.markdown("---")
st.sidebar.write("Colorbar preview:")

# small colorbar preview in sidebar
cb_fig, cb_ax = plt.subplots(figsize=(2.2, 0.5))
cb_ax.set_axis_off()
cmap_obj_preview = matplotlib.colormaps.get(cmap_name)
norm_preview = Normalize(vmin=0, vmax=100)
from matplotlib.cm import ScalarMappable
sm_preview = ScalarMappable(cmap=cmap_obj_preview, norm=norm_preview)
sm_preview.set_array([])  # required
cb_fig.colorbar(sm_preview, ax=cb_ax, orientation="horizontal", fraction=0.9, pad=0.1)
st.sidebar.pyplot(cb_fig)
plt.close(cb_fig)

st.sidebar.markdown("---")

# -----------------------
# Main title
# -----------------------
st.markdown("# Hex Map India")

# -----------------------
# Build grid and load mapping if present
# -----------------------
hex_grid = make_hex_grid(rows=10, cols=10, r=hex_radius, orientation="flat")
local_mapping = None
if os.path.exists(LOCAL_MAPPING_FILENAME):
    local_mapping = load_local_mapping(LOCAL_MAPPING_FILENAME)
    if local_mapping is not None:
        st.info("Loaded local mapping file: `state_hex_key.csv` — showing matched hexes from mapping (before upload).")
    else:
        st.warning("Found `state_hex_key.csv` but couldn't parse it. To use mapping ensure it contains `hex_id,code`.")

# -----------------------
# Pre-upload preview area (show codes from mapping if available)
# We'll create a single plot area and reuse it after upload.
# -----------------------
plot_col, _ = st.columns([3, 1])
with plot_col:
    if local_mapping is not None:
        # merge mapping with geometry
        preview_merged = local_mapping.merge(hex_grid, on="hex_id", how="inner")
        # initial plot (no values)
        fig, ax, vals = plot_matched_hexes(hex_grid, preview_merged, code_col="code", value_col=None, cmap_name=cmap_name)
        st.pyplot(fig)
        # keep a reference to the merged dataframe to recolor later
        current_merged = preview_merged.copy()
        current_fig = fig
        current_ax = ax
        current_vals = vals
    else:
        st.info("No local mapping found. Upload a file with a `hex_id` column to place hexes directly.")
        current_merged = pd.DataFrame()  # empty
        current_fig = None
        current_ax = None
        current_vals = None

# -----------------------
# Handle upload: recolor/update the same map (do not create a separate map)
# -----------------------
if uploaded is not None:
    try:
        user_df = pd.read_csv(uploaded)
    except Exception as e:
        st.error(f"Could not read uploaded CSV: {e}")
        st.stop()

    # normalize column names
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
    user_df = user_df.rename(columns=rename_map)

    # determine merged result depending on mapping availability or hex_id in upload
    if "code" in user_df.columns and local_mapping is not None:
        merged = local_mapping.merge(user_df, on="code", how="inner")
        merged = merged.merge(hex_grid, on="hex_id", how="left")
        if merged.empty:
            st.warning("No matching codes found between your upload and local mapping.")
        else:
            st.success(f"Matched {len(merged)} rows by code. Recoloring existing map.")
            # recolor: replace current_merged with merged and redraw in same area
            current_merged = merged.copy()
            fig, ax, vals = plot_matched_hexes(hex_grid, current_merged, code_col="code", value_col="value", cmap_name=cmap_name)
            st.pyplot(fig)
            current_fig = fig
            current_ax = ax
            current_vals = vals

    elif "hex_id" in user_df.columns:
        user_df["hex_id"] = pd.to_numeric(user_df["hex_id"], errors="coerce").astype("Int64")
        merged = hex_grid.merge(user_df, on="hex_id", how="inner")
        if merged.empty:
            st.warning("No rows matched by `hex_id`. Check that hex_id values are integers between 0 and 99 (10x10 grid).")
        else:
            st.success(f"Matched {len(merged)} rows by hex_id. Recoloring existing map.")
            current_merged = merged.copy()
            fig, ax, vals = plot_matched_hexes(hex_grid, current_merged, code_col="code", value_col="value", cmap_name=cmap_name)
            st.pyplot(fig)
            current_fig = fig
            current_ax = ax
            current_vals = vals
    else:
        st.warning("Upload does not include 'hex_id', and no local mapping file is present. To plot, either include a `hex_id` column (0..99) or add `state_hex_key.csv` to the repo.")
        st.stop()

    # After recolor, present a small preview table (no download)
    if not current_merged.empty:
        preview = current_merged.drop(columns=["verts"]) if "verts" in current_merged.columns else current_merged.copy()
        st.subheader("Matched rows (preview)")
        st.dataframe(preview.head(200))

        # allow download of the PNG of the recolored figure
        buf = io.BytesIO()
        try:
            fig.savefig(buf, dpi=150, bbox_inches="tight")
            buf.seek(0)
            st.download_button("Download as PNG", data=buf, file_name="hex_map.png", mime="image/png")
        except Exception:
            st.info("Figure PNG download not available.")
else:
    # no upload: still show the caption
    st.markdown("<br>", unsafe_allow_html=True)

# Footer caption
st.markdown("---")
st.markdown("<div style='text-align:center; font-size:12px;'>Made with Hex Map India</div>", unsafe_allow_html=True)

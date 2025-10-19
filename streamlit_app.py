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

st.set_page_config(layout="wide", page_title="Hex Map — Matched Only")

# -----------------------
# Small fixed hex grid (10x10, flat) — no controls
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
# Attempt to load a local mapping file if present
# (expected to map hex_id -> code). This is optional;
# if absent, the app can match on uploaded 'hex_id' column.
# -----------------------
LOCAL_MAPPING_FILENAME = "state_hex_key.csv"

def load_local_mapping(path):
    try:
        df = pd.read_csv(path)
        # Heuristic: If it contains hex_id and code use them; else try second column as code
        cols_lower = [c.lower() for c in df.columns]
        if "hex_id" in cols_lower and "code" in cols_lower:
            df = df.rename(columns={df.columns[cols_lower.index("hex_id")]: "hex_id",
                                    df.columns[cols_lower.index("code")]: "code"})
        else:
            if len(df.columns) >= 2:
                df = df.rename(columns={df.columns[0]: "hex_id", df.columns[1]: "code"})
        df = df[["hex_id", "code"]].copy()
        df["hex_id"] = pd.to_numeric(df["hex_id"], errors="coerce").astype("Int64")
        # clean codes (same logic as earlier)
        df["code"] = df["code"].astype(str).str.replace("[^A-Za-z]", "", regex=True).str.upper().str[-2:]
        return df.dropna(subset=["hex_id"]).reset_index(drop=True)
    except Exception:
        return None

# -----------------------
# Plotting helper — ALWAYS shows only matched hexes
# -----------------------
def plot_matched_hexes(hex_grid, merged_df, code_col="code", value_col="value", cmap_name="viridis", title=None):
    """
    hex_grid: dataframe with hex positions and verts
    merged_df: hex_grid merged with uploaded data; should contain only matched rows
    """
    if merged_df.empty:
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.text(0.5, 0.5, "No matched hexes to plot", ha="center", va="center")
        ax.set_axis_off()
        return fig

    # colors
    patches, facecolors = [], []
    vals = None
    if value_col in merged_df.columns:
        vals = pd.to_numeric(merged_df[value_col], errors="coerce")
        vmin, vmax = vals.min(), vals.max()
        cmap = cm.get_cmap(cmap_name)
        norm = Normalize(vmin=vmin, vmax=vmax)
    else:
        cmap = None
        norm = None

    for _, row in merged_df.iterrows():
        poly = Polygon(row["verts"], closed=True, edgecolor="black", linewidth=0.5)
        patches.append(poly)
        if value_col in row.index:
            val = row[value_col]
            if pd.isna(val):
                facecolors.append((1, 1, 1, 1))
            else:
                facecolors.append(cmap(norm(float(val))))
        else:
            facecolors.append((0.92, 0.92, 0.92, 1))

    fig, ax = plt.subplots(figsize=(8, 8))
    collection = PatchCollection(patches, facecolor=facecolors, match_original=True)
    ax.add_collection(collection)

    # labels (use state name if provided, else code)
    for _, row in merged_df.iterrows():
        label = None
        if "state" in row.index and pd.notna(row["state"]):
            label = row["state"]
        elif pd.notna(row.get(code_col)):
            label = row.get(code_col)
        else:
            label = str(int(row["hex_id"]))
        ax.text(row["cx"], row["cy"], label, ha="center", va="center", fontsize=6)

    ax.set_aspect("equal")
    ax.autoscale()
    ax.margins(0.05)
    ax.set_axis_off()
    if title:
        ax.set_title(title)

    if vals is not None and not vals.isnull().all():
        from matplotlib.cm import ScalarMappable
        sm = ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array(vals)
        fig.colorbar(sm, ax=ax, fraction=0.046, pad=0.04, label=value_col)

    return fig

# -----------------------
# UI
# -----------------------
st.title("Hex Map — Matched Hexes Only")
st.markdown("Upload a CSV with columns `state, code, value` (example template available below). The app will display only hexes that match the uploaded rows. If the app repository contains `state_hex_key.csv` (mapping `hex_id` → `code`), that mapping will be used to place state codes on the grid; otherwise your upload must include `hex_id` column to place hexes correctly.")

# Colormap selector (the only control)
cmap = st.selectbox("Colormap", options=sorted(m for m in plt.colormaps()), index=plt.colormaps().index("viridis"))

# Template download: a small example CSV with the required columns
template_df = pd.DataFrame({
    "state": ["Example State A", "Example State B", "Example State C"],
    "code": ["EX", "EB", "EC"],
    "value": [10.0, 5.0, 7.2]
})
template_buf = io.StringIO()
template_df.to_csv(template_buf, index=False)
template_bytes = template_buf.getvalue().encode("utf-8")
st.download_button("Download upload template (state,code,value)", data=template_bytes, file_name="hex_upload_template.csv", mime="text/csv")

st.markdown("---")
uploaded = st.file_uploader("Upload CSV (state, code, value) — file must contain 'code' column. Optionally include 'hex_id' to place directly.", type=["csv"])

# Build the fixed grid and optionally load local mapping
hex_grid = make_hex_grid(rows=10, cols=10, r=1, orientation="flat")
local_mapping = None
if os.path.exists(LOCAL_MAPPING_FILENAME):
    local_mapping = load_local_mapping(LOCAL_MAPPING_FILENAME)
    if local_mapping is not None:
        st.info("Loaded local mapping file: `state_hex_key.csv` — app will match by `code` using that file.")
    else:
        st.warning("Found `state_hex_key.csv` but couldn't parse it. If you want to use a mapping file, ensure it contains `hex_id` and `code` columns.")

# Process upload
if uploaded is not None:
    try:
        user_df = pd.read_csv(uploaded)
    except Exception as e:
        st.error(f"Could not read uploaded CSV: {e}")
        st.stop()

    # Normalize column names
    user_cols = [c.lower() for c in user_df.columns]
    # Accept 'state','code','value' (case-insensitive) — rename to standard
    rename_map = {}
    for i, c in enumerate(user_df.columns):
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

    # If codes present and local mapping exists: merge on code
    if "code" in user_df.columns and local_mapping is not None:
        # merge user's data (state, code, value) with local mapping on code
        merged = local_mapping.merge(user_df, on="code", how="inner")
        # attach geometry from hex_grid by hex_id
        merged = merged.merge(hex_grid, on="hex_id", how="left")
        matched_count = len(merged)
        if matched_count == 0:
            st.warning("No matching codes found between your upload and local mapping.")
        else:
            st.success(f"Matched {matched_count} rows by code using `state_hex_key.csv`.")
            fig = plot_matched_hexes(hex_grid, merged, code_col="code", value_col="value", cmap_name=cmap, title="Matched hexes (by code)")
            st.pyplot(fig)

    # Else if upload includes hex_id, merge directly
    elif "hex_id" in user_df.columns:
        # ensure hex_id numeric
        user_df["hex_id"] = pd.to_numeric(user_df["hex_id"], errors="coerce").astype("Int64")
        merged = hex_grid.merge(user_df, on="hex_id", how="inner")
        if merged.empty:
            st.warning("No rows matched by `hex_id`. Check that hex_id values are integers between 0 and 99 (10x10 grid).")
        else:
            st.success(f"Matched {len(merged)} rows by hex_id.")
            fig = plot_matched_hexes(hex_grid, merged, code_col="code", value_col="value", cmap_name=cmap, title="Matched hexes (by hex_id)")
            st.pyplot(fig)

    else:
        st.warning("Upload does not include 'hex_id', and no local mapping file is present. To plot, either:\n\n"
                   "- Include a `hex_id` column in your upload (integers 0..99 for the 10x10 grid), or\n"
                   "- Add a `state_hex_key.csv` file to the app folder that maps `hex_id` -> `code` and then upload a file with `code,value`.\n\n"
                   "Use the template download as a starting point (you can add a `hex_id` column if you prefer).")
        st.stop()

    # Data preview + download of merged used rows
    if 'merged' in locals() and not merged.empty:
        preview = merged.drop(columns=["verts"]) if "verts" in merged.columns else merged.copy()
        st.subheader("Matched rows (preview)")
        st.dataframe(preview.head(200))

        csv_buf = preview.to_csv(index=False).encode("utf-8")
        st.download_button("Download matched rows as CSV", data=csv_buf, file_name="matched_hex_rows.csv", mime="text/csv")
else:
    st.info("Upload your CSV (state, code, value). Use the template above for formatting. The app will show only matched hexes.")

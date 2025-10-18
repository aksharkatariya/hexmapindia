import math
import io
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from matplotlib.collections import PatchCollection
import matplotlib.cm as cm
from matplotlib.colors import Normalize
import streamlit as st

st.set_page_config(layout="wide", page_title="Hex Grid Map")

# -----------------------
# Helper functions
# -----------------------
def hex_vertices(x, y, r=1, orientation="pointy"):
    """Return 6 vertices of a hexagon around (x, y)."""
    start_deg = 30 if orientation == "pointy" else 0
    return [
        (x + r * math.cos(math.radians(start_deg + 60 * i)),
         y + r * math.sin(math.radians(start_deg + 60 * i)))
        for i in range(6)
    ]

def make_hex_grid(rows, cols, r=1, orientation="pointy"):
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
                "hex_id": row * cols + col,
                "row": row,
                "col": col,
                "cx": cx,
                "cy": cy,
                "verts": hex_vertices(cx, cy, r, orientation)
            })
    return pd.DataFrame(hexes)

def plot_hex_dataframe(plot_df, code_col="code", value_col=None, cmap_name="viridis", title=None):
    """Return (fig, plot_df) where fig is a matplotlib figure."""
    patches, facecolors = [], []
    vals = None
    if value_col is not None:
        vals = plot_df[value_col].astype(float)
        vmin, vmax = vals.min(), vals.max()
        cmap = cm.get_cmap(cmap_name)
        norm = Normalize(vmin=vmin, vmax=vmax)
    for _, row in plot_df.iterrows():
        poly = Polygon(row["verts"], closed=True, edgecolor="black", linewidth=0.4)
        patches.append(poly)
        if value_col is not None:
            # if value is NaN, paint white
            try:
                val = float(row[value_col])
                facecolors.append(cmap(norm(val)))
            except Exception:
                facecolors.append((1,1,1,1))
        else:
            facecolors.append((0.9, 0.9, 0.9, 1))

    fig, ax = plt.subplots(figsize=(8, 8))
    collection = PatchCollection(patches, facecolor=facecolors, match_original=True)
    ax.add_collection(collection)

    # Labels
    for _, row in plot_df.iterrows():
        label = row.get(code_col) if pd.notna(row.get(code_col)) else str(int(row["hex_id"]))
        ax.text(row["cx"], row["cy"], label, ha="center", va="center", fontsize=6)

    ax.set_aspect("equal")
    ax.autoscale()
    ax.margins(0.05)
    ax.set_axis_off()
    if title:
        ax.set_title(title)

    # colorbar
    if value_col is not None and vals is not None and not vals.isnull().all():
        from matplotlib.cm import ScalarMappable
        sm = ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array(vals)
        fig.colorbar(sm, ax=ax, fraction=0.046, pad=0.04, label=value_col)
    return fig

# -----------------------
# Sidebar: controls
# -----------------------
st.sidebar.header("Grid & Plot controls")
orientation = st.sidebar.selectbox("Orientation", options=["flat", "pointy"], index=0)
rows = st.sidebar.number_input("Rows", min_value=2, max_value=40, value=10)
cols = st.sidebar.number_input("Cols", min_value=2, max_value=40, value=10)
radius = st.sidebar.number_input("Hex radius (r)", min_value=0.1, max_value=5.0, value=1.0, step=0.1)
cmap_name = st.sidebar.selectbox("Colormap", options=sorted(m for m in plt.colormaps()), index=plt.colormaps().index("viridis"))
show_mode = st.sidebar.radio("Show", options=["Full grid (all hexes)", "Only hexes with code", "Choropleth (value)"], index=2)

st.sidebar.markdown("---")
st.sidebar.markdown("Upload files:")
mapping_file = st.sidebar.file_uploader("Mapping CSV (`hex_id` and/or `code`) (optional)", type=["csv"])
values_file = st.sidebar.file_uploader("Values CSV (`code` and `value`) or (`hex_id` and `value`) (optional)", type=["csv"])

# -----------------------
# Make grid and read mapping
# -----------------------
hex_grid = make_hex_grid(rows=rows, cols=cols, r=radius, orientation=orientation)

# default mapping: none
mapping_df = None
if mapping_file is not None:
    try:
        mapping_df = pd.read_csv(mapping_file)
        # Normalize: accept hex_id & code, or second column as code like in your original
        if "hex_id" not in mapping_df.columns and "code" in mapping_df.columns:
            # try to keep second column as code if first col is hex_id-like
            pass
        # coerce expected column names
        if "hex_id" in mapping_df.columns and "code" not in mapping_df.columns:
            # maybe second column is code (like in your CSV)
            other_cols = [c for c in mapping_df.columns if c != "hex_id"]
            if other_cols:
                mapping_df = mapping_df.rename(columns={other_cols[0]: "code"})
        if "code" in mapping_df.columns and "hex_id" not in mapping_df.columns:
            # maybe the file is just codes in order aligned to hex_id
            # if length matches, assume hex_id is index
            if len(mapping_df) == len(hex_grid):
                mapping_df = mapping_df.copy()
                mapping_df["hex_id"] = mapping_df.index
            else:
                # attempt to extract code from second column if present
                pass
        # keep only hex_id, code
        if "hex_id" in mapping_df.columns and "code" in mapping_df.columns:
            mapping_df = mapping_df[["hex_id", "code"]]
            # clean code: remove non-letters, uppercase, take last 2 chars (your original logic)
            mapping_df["code"] = mapping_df["code"].astype(str).str.replace("[^A-Za-z]", "", regex=True).str.upper().str[-2:]
        else:
            st.sidebar.warning("Mapping file provided but couldn't find clear 'hex_id' and 'code' columns. App will try best-effort merges.")
    except Exception as e:
        st.sidebar.error(f"Error reading mapping file: {e}")
        mapping_df = None

# merge mapping if available
if mapping_df is not None:
    merged = hex_grid.merge(mapping_df, on="hex_id", how="left")
else:
    merged = hex_grid.copy()
    merged["code"] = pd.NA

# -----------------------
# Read values (if any)
# -----------------------
values_df = None
value_col_name = None
if values_file is not None:
    try:
        values_df = pd.read_csv(values_file)
        # heuristics for column names
        candidates = [c.lower() for c in values_df.columns]
        # find 'value' column
        if "value" in candidates:
            value_col_name = values_df.columns[candidates.index("value")]
        else:
            # if second column exists, assume that's the value
            if len(values_df.columns) >= 2:
                value_col_name = values_df.columns[1]
        # find code or hex_id column
        if "code" in candidates:
            code_col_name = values_df.columns[candidates.index("code")]
            # merge on code
            merged = merged.merge(values_df[[code_col_name, value_col_name]].rename(columns={code_col_name: "code", value_col_name: "value"}), on="code", how="left")
        elif "hex_id" in candidates:
            hex_col_name = values_df.columns[candidates.index("hex_id")]
            merged = merged.merge(values_df[[hex_col_name, value_col_name]].rename(columns={hex_col_name: "hex_id", value_col_name: "value"}), on="hex_id", how="left")
        else:
            # maybe values_df has only code and value but headers are different; attempt best-effort
            if len(values_df.columns) >= 2:
                merged = merged.merge(values_df.rename(columns={values_df.columns[0]: "code", values_df.columns[1]: "value"}), on="code", how="left")
            else:
                st.sidebar.warning("Values file present but couldn't identify columns. Expected [code,value] or [hex_id,value].")
    except Exception as e:
        st.sidebar.error(f"Error reading values file: {e}")
        values_df = None

# -----------------------
# Display options and run plotting
# -----------------------
st.title("Hex Grid Explorer")

st.markdown("Controls: change orientation, grid size, upload mapping and values. The app will try best-effort merges: values can be matched by `code` or `hex_id`.")

# Choose plotting subset
if show_mode == "Full grid (all hexes)":
    to_plot = merged.copy()
    fig = plot_hex_dataframe(to_plot, code_col="code", value_col=None, title="Full grid (all hexes)")
    st.pyplot(fig)
elif show_mode == "Only hexes with code":
    to_plot = merged[merged["code"].notna()].copy()
    if to_plot.empty:
        st.info("No hexes have a `code` in the mapping. Upload a mapping CSV or switch to Full grid.")
    else:
        fig = plot_hex_dataframe(to_plot, code_col="code", value_col=None, title="Only hexes with codes")
        st.pyplot(fig)
else:  # Choropleth
    if "value" not in merged.columns:
        st.info("No values found to plot. Upload a values CSV (columns: code,value) or (hex_id,value).")
        # show the grid greyscale
        fig = plot_hex_dataframe(merged, code_col="code", value_col=None, title="Grid (no values)")
        st.pyplot(fig)
    else:
        # Option: handle log scaling? keep simple
        to_plot = merged.copy()
        # show blank if all values missing
        if to_plot["value"].isnull().all():
            st.info("Uploaded values exist but no matches found with mapping. Check your `code` or `hex_id` columns.")
        fig = plot_hex_dataframe(to_plot, code_col="code", value_col="value", cmap_name=cmap_name, title="Choropleth (value)")
        st.pyplot(fig)

# -----------------------
# Data and download
# -----------------------
st.subheader("Merged data preview")
st.dataframe(merged.drop(columns=["verts"]).head(200))

# allow download of merged data
csv_buf = merged.drop(columns=["verts"]).to_csv(index=False).encode("utf-8")
st.download_button("Download merged CSV", data=csv_buf, file_name="merged_hex_data.csv", mime="text/csv")

# allow download of PNG of last figure
buf = io.BytesIO()
try:
    fig.savefig(buf, dpi=150, bbox_inches="tight")
    buf.seek(0)
    st.download_button("Download last figure (PNG)", data=buf, file_name="hex_map.png", mime="image/png")
except Exception:
    st.info("Figure PNG download not available here.")

# -----------------------
# Example / help
# -----------------------

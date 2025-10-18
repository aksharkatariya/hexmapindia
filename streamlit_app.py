# app.py
import math
import io
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # IMPORTANT for headless servers (Streamlit Cloud)
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from matplotlib.collections import PatchCollection
import matplotlib.cm as cm
from matplotlib.colors import Normalize
import streamlit as st

st.set_page_config(layout="wide", page_title="Hex Grid Map")

# -----------------------
# Helpers
# -----------------------
def hex_vertices(x, y, r=1, orientation="pointy"):
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
                "hex_id": int(row * cols + col),
                "row": int(row),
                "col": int(col),
                "cx": float(cx),
                "cy": float(cy),
                "verts": hex_vertices(cx, cy, r, orientation)
            })
    return pd.DataFrame(hexes)

def plot_hex_dataframe(plot_df, code_col="code", value_col=None, cmap_name="viridis", title=None, show_only_matched=False):
    """
    Plot hexes; if show_only_matched=True, filter out rows without a match (value present
    or code present depending on value_col).
    Returns (fig, plot_df_used)
    """
    df = plot_df.copy()

    # Determine matching criterion
    if show_only_matched:
        if value_col is not None and value_col in df.columns:
            df = df[df[value_col].notna()].copy()
        elif code_col in df.columns:
            # matched if code is present (non-null)
            df = df[df[code_col].notna()].copy()

    if df.empty:
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.text(0.5, 0.5, "No matched hexes to plot", ha="center", va="center")
        ax.set_axis_off()
        return fig, df

    # Prepare colors
    patches, facecolors = [], []
    vals = None
    if value_col is not None and value_col in df.columns:
        vals = pd.to_numeric(df[value_col], errors="coerce")
        vmin, vmax = vals.min(), vals.max()
        cmap = cm.get_cmap(cmap_name)
        norm = Normalize(vmin=vmin, vmax=vmax)
    else:
        cmap = None
        norm = None

    for _, row in df.iterrows():
        poly = Polygon(row["verts"], closed=True, edgecolor="black", linewidth=0.4)
        patches.append(poly)
        if value_col is not None and value_col in row.index:
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

    for _, row in df.iterrows():
        label = row.get(code_col) if pd.notna(row.get(code_col)) else str(int(row["hex_id"]))
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

    return fig, df

# -----------------------
# Sidebar controls
# -----------------------
st.sidebar.header("Grid & Plot controls")
orientation = st.sidebar.selectbox("Orientation", options=["flat", "pointy"], index=0)
rows = st.sidebar.number_input("Rows", min_value=2, max_value=40, value=10)
cols = st.sidebar.number_input("Cols", min_value=2, max_value=40, value=10)
radius = st.sidebar.number_input("Hex radius (r)", min_value=0.1, max_value=5.0, value=1.0, step=0.1)
cmap_name = st.sidebar.selectbox("Colormap", options=sorted(m for m in plt.colormaps()), index=plt.colormaps().index("viridis"))
show_mode = st.sidebar.radio("Show", options=["Full grid (all hexes)", "Only hexes with code", "Choropleth (value)"], index=2)
show_only_matched = st.sidebar.checkbox("Only show matched hexes", value=True)

st.sidebar.markdown("---")
st.sidebar.markdown("Upload files:")
mapping_file = st.sidebar.file_uploader("Mapping CSV (`hex_id` and/or `code`) (optional)", type=["csv"])
values_file = st.sidebar.file_uploader("Values CSV (`code` and `value`) or (`hex_id` and `value`) (optional)", type=["csv"])

# -----------------------
# Build grid & ingest files
# -----------------------
hex_grid = make_hex_grid(rows=rows, cols=cols, r=radius, orientation=orientation)

mapping_df = None
if mapping_file is not None:
    try:
        mapping_df = pd.read_csv(mapping_file)
        cols_lower = [c.lower() for c in mapping_df.columns]
        if "hex_id" in cols_lower and "code" in cols_lower:
            # map to standard names
            mapping_df = mapping_df.rename(columns={mapping_df.columns[cols_lower.index("hex_id")]: "hex_id",
                                                    mapping_df.columns[cols_lower.index("code")]: "code"})
        else:
            if len(mapping_df.columns) >= 2:
                mapping_df = mapping_df.rename(columns={mapping_df.columns[0]: "hex_id", mapping_df.columns[1]: "code"})
        if "code" in mapping_df.columns:
            mapping_df["code"] = mapping_df["code"].astype(str).str.replace("[^A-Za-z]", "", regex=True).str.upper().str[-2:]
        mapping_df = mapping_df[["hex_id", "code"]].copy()
        mapping_df["hex_id"] = pd.to_numeric(mapping_df["hex_id"], errors="coerce").astype("Int64")
    except Exception as e:
        st.sidebar.error(f"Error reading mapping file: {e}")
        mapping_df = None

if mapping_df is not None:
    merged = hex_grid.merge(mapping_df, on="hex_id", how="left")
else:
    merged = hex_grid.copy()
    merged["code"] = pd.NA

# Values ingestion
if values_file is not None:
    try:
        values_df = pd.read_csv(values_file)
        cols_lower = [c.lower() for c in values_df.columns]
        if "value" in cols_lower:
            value_col = values_df.columns[cols_lower.index("value")]
        elif len(values_df.columns) >= 2:
            value_col = values_df.columns[1]
        else:
            value_col = values_df.columns[0]

        if "code" in cols_lower:
            code_col = values_df.columns[cols_lower.index("code")]
            values_df = values_df[[code_col, value_col]].rename(columns={code_col: "code", value_col: "value"})
            merged = merged.merge(values_df, on="code", how="left")
        elif "hex_id" in cols_lower:
            hex_col = values_df.columns[cols_lower.index("hex_id")]
            values_df = values_df[[hex_col, value_col]].rename(columns={hex_col: "hex_id", value_col: "value"})
            merged = merged.merge(values_df, on="hex_id", how="left")
        else:
            if len(values_df.columns) >= 2:
                values_df = values_df.rename(columns={values_df.columns[0]: "code", values_df.columns[1]: "value"})
                merged = merged.merge(values_df, on="code", how="left")
            else:
                st.sidebar.warning("Values file present but couldn't identify columns.")
    except Exception as e:
        st.sidebar.error(f"Error reading values file: {e}")

# -----------------------
# Plot selection & display
# -----------------------
st.title("Hex Grid Explorer")
st.markdown("Upload mapping CSV (`hex_id,code`) and values CSV (`code,value`) to color hexes. Toggle 'Only show matched hexes' to hide unmatched cells.")

if show_mode == "Full grid (all hexes)":
    fig, used_df = plot_hex_dataframe(merged, code_col="code", value_col=None, title="Full grid (all hexes)", show_only_matched=show_only_matched)
    st.pyplot(fig)
elif show_mode == "Only hexes with code":
    to_plot = merged[merged["code"].notna()].copy()
    fig, used_df = plot_hex_dataframe(to_plot, code_col="code", value_col=None, title="Only hexes with codes", show_only_matched=show_only_matched)
    st.pyplot(fig)
else:
    if "value" not in merged.columns:
        st.info("No values found to plot. Upload a values CSV (columns: code,value) or (hex_id,value).")
        fig, used_df = plot_hex_dataframe(merged, code_col="code", value_col=None, title="Grid (no values)", show_only_matched=show_only_matched)
        st.pyplot(fig)
    else:
        fig, used_df = plot_hex_dataframe(merged, code_col="code", value_col="value", cmap_name=cmap_name, title="Choropleth (value)", show_only_matched=show_only_matched)
        st.pyplot(fig)

# -----------------------
# Data preview & downloads
# -----------------------
st.subheader("Merged data preview (first 200 rows)")
preview = merged.drop(columns=["verts"]).copy()
st.dataframe(preview.head(200))

csv_buf = preview.to_csv(index=False).encode("utf-8")
st.download_button("Download merged CSV", data=csv_buf, file_name="merged_hex_data.csv", mime="text/csv")

# Download last figure as PNG
buf = io.BytesIO()
try:
    fig.savefig(buf, dpi=150, bbox_inches="tight")
    buf.seek(0)
    st.download_button("Download last figure (PNG)", data=buf, file_name="hex_map.png", mime="image/png")
except Exception:
    st.info("Figure PNG download not available.")

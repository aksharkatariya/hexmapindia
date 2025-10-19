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

# --- Template data ---
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

# --- Create hex grid ---
def hex_vertices(x, y, r=1, orientation="flat"):
    """Generate the 6 corner points of a hexagon"""
    start_deg = 30 if orientation == "pointy" else 0
    return [
        (x + r * math.cos(math.radians(start_deg + 60 * i)),
         y + r * math.sin(math.radians(start_deg + 60 * i)))
        for i in range(6)
    ]

def make_hex_grid(rows=10, cols=10, r=1, orientation="flat"):
    """Create a grid of hexagons with specified rows and columns"""
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
def plot_matched_hexes(merged_df, cmap_name="viridis", title="Hex Map India"):
    """Create a hex map visualization with colors based on values"""
    if merged_df.empty:
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.text(0.5, 0.5, "No matched hexes found", ha="center", va="center")
        ax.axis("off")
        return fig
    
    # Convert values to numeric
    vals = pd.to_numeric(merged_df["value"], errors="coerce")
    
    # Get colormap
    cmap = matplotlib.colormaps.get(cmap_name)
    norm = Normalize(vmin=vals.min(), vmax=vals.max())
    
    # Build patches and colors
    patches = []
    facecolors = []
    for _, row in merged_df.iterrows():
        poly = Polygon(row["verts"], closed=True, edgecolor="black", linewidth=0.5)
        patches.append(poly)
        
        val = row["value"]
        if pd.isna(val):
            facecolors.append((1, 1, 1, 1))  # white for missing values
        else:
            facecolors.append(cmap(norm(float(val))))
    
    # Create the figure
    fig, ax = plt.subplots(figsize=(10, 10))
    ax.add_collection(PatchCollection(patches, facecolor=facecolors, match_original=True))
    
    # Add labels
    for _, row in merged_df.iterrows():
        label = str(row["code"])
        ax.text(row["cx"], row["cy"], label, ha="center", va="center", 
                fontsize=9, fontweight="bold")
    
    ax.set_aspect("equal")
    ax.autoscale()
    ax.margins(0.05)
    ax.axis("off")
    ax.set_title(title, fontsize=18, fontweight="bold", pad=20)
    
    # Add colorbar
    from matplotlib.cm import ScalarMappable
    sm = ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array(vals)
    fig.colorbar(sm, ax=ax, fraction=0.046, pad=0.04, label="Value")
    
    return fig

def plot_empty_hex_grid(hex_grid, codes):
    """Create an empty hex map showing all state codes"""
    fig, ax = plt.subplots(figsize=(10, 10))
    
    patches = []
    for _, row in hex_grid.iterrows():
        poly = Polygon(row["verts"], closed=True, edgecolor="black", 
                      linewidth=0.5, facecolor='lightgray')
        patches.append(poly)
    
    ax.add_collection(PatchCollection(patches, match_original=True))
    
    # Add labels
    for idx, row in hex_grid.iterrows():
        if idx < len(codes):
            ax.text(row["cx"], row["cy"], codes[idx], ha="center", va="center", 
                    fontsize=9, fontweight="bold")
    
    ax.set_aspect("equal")
    ax.autoscale()
    ax.margins(0.05)
    ax.axis("off")
    ax.set_title("India Hex Map - Upload data to visualize", 
                fontsize=18, fontweight="bold", pad=20)
    
    return fig

# --- Sidebar setup ---
st.sidebar.markdown("## 📥 Step 1 — Download Template")

# Create template with map_title row
map_title_row = pd.DataFrame({
    "map_title": ["Hex Map India"],
    "code": [""],
    "state": [""],
    "value": [""]
})

template_table = pd.DataFrame({
    "map_title": [""] * len(TEMPLATE_CODES),
    "code": TEMPLATE_CODES,
    "state": TEMPLATE_STATES,
    "value": [""] * len(TEMPLATE_CODES)
})

final_template = pd.concat([map_title_row, template_table], ignore_index=True)

st.sidebar.download_button(
    "⬇️ Download CSV Template",
    data=final_template.to_csv(index=False),
    file_name="hex_map_template.csv",
    mime="text/csv"
)
st.sidebar.markdown("*Fill the 'value' column and optionally edit 'map_title'*")

st.sidebar.markdown("---")

# --- Step 2: Upload ---
st.sidebar.markdown("## 📤 Step 2 — Upload Your Data")
uploaded = st.sidebar.file_uploader(
    "Upload filled CSV file", 
    type=["csv"],
    help="Upload the template after filling in your data"
)

st.sidebar.markdown("---")

# --- Step 3: Customize ---
st.sidebar.markdown("## 🎨 Step 3 — Customize")

cmap_name = st.sidebar.selectbox(
    "Color Scheme", 
    options=['viridis', 'plasma', 'inferno', 'magma', 'cividis',
             'Blues', 'Reds', 'Greens', 'Oranges', 'Purples',
             'YlOrRd', 'YlGnBu', 'RdYlGn', 'RdYlBu', 'Spectral'],
    index=0
)

hex_radius = st.sidebar.slider("Hex Size", 0.4, 2.0, 1.0, 0.1)

# Colorbar preview
st.sidebar.write("Color Preview:")
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
st.title("🗺️ India Hex Map Visualizer")
st.markdown("Create beautiful hex map visualizations for Indian states and territories")

# Generate hex grid
hex_grid = make_hex_grid(rows=6, cols=6, r=hex_radius)
hex_grid["code"] = TEMPLATE_CODES

if uploaded is None:
    st.info("👈 Follow the steps in the sidebar to create your visualization")
    
    # Show empty hex map
    fig = plot_empty_hex_grid(hex_grid, TEMPLATE_CODES)
    st.pyplot(fig)
    plt.close(fig)
    
    # Show instructions
    st.markdown("### How to use:")
    st.markdown("1. **Download** the CSV template from the sidebar")
    st.markdown("2. **Fill in** the 'value' column with your data")
    st.markdown("3. **Upload** the filled CSV file")
    st.markdown("4. **Customize** colors and size as needed")
    st.markdown("5. **Download** your map as PNG")
    
else:
    try:
        df = pd.read_csv(uploaded)
    except Exception as e:
        st.error(f"❌ Error reading CSV: {e}")
        st.stop()
    
    # Normalize column names
    df.columns = [c.lower().strip() for c in df.columns]
    
    # Check required columns
    for col in ["code", "value"]:
        if col not in df.columns:
            st.error(f"❌ Your CSV must include '{col}' column.")
            st.stop()
    
    # Determine map title
    map_title = "Hex Map India"
    if "map_title" in df.columns:
        titles = df["map_title"].dropna().unique()
        if len(titles) > 0:
            map_title = str(titles[0])
    
    # Merge with hex grid
    merged = pd.merge(df, hex_grid, on="code", how="inner")
    
    if merged.empty:
        st.warning("⚠️ No matching codes found. Ensure your 'code' values match the template (e.g., 'AP', 'MH').")
        st.stop()
    
    # Create visualization
    fig = plot_matched_hexes(merged, cmap_name=cmap_name, title=map_title)
    st.pyplot(fig)
    
    # Download PNG button
    st.sidebar.markdown("---")
    st.sidebar.markdown("## 💾 Step 4 — Download Map")
    buf = io.BytesIO()
    fig.savefig(buf, dpi=300, bbox_inches="tight")
    buf.seek(0)
    
    st.sidebar.download_button(
        "⬇️ Download Map as PNG",
        buf,
        file_name=f"{map_title.replace(' ', '_')}.png",
        mime="image/png"
    )
    
    # Show statistics
    st.sidebar.markdown("### 📊 Statistics")
    valid_values = pd.to_numeric(merged["value"], errors="coerce").dropna()
    if len(valid_values) > 0:
        st.sidebar.metric("Min Value", f"{valid_values.min():.2f}")
        st.sidebar.metric("Max Value", f"{valid_values.max():.2f}")
        st.sidebar.metric("Average", f"{valid_values.mean():.2f}")
        st.sidebar.metric("States", len(valid_values))
    
    plt.close(fig)
    
    # Preview table
    st.markdown("---")
    st.subheader("📋 Data Preview")
    display_cols = ["code", "state", "value"] if "state" in merged.columns else ["code", "value"]
    st.dataframe(merged[display_cols].head(50), use_container_width=True)

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align:center;font-size:12px;color:#666;'>Made with ❤️ using Streamlit</div>", 
    unsafe_allow_html=True
)

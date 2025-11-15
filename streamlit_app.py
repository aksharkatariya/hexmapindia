import streamlit as st
import math
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from matplotlib.collections import PatchCollection
import matplotlib.cm as cm
from matplotlib.colors import Normalize
from io import BytesIO

# Page config
st.set_page_config(page_title="India Hex Map Visualizer", layout="wide")

# Hex map configuration - embedded directly
HEX_MAP_KEY = """hex_id,code
14,AN
32,AP
68,AR
57,AS
64,BR
,,CH
52,GG
62,DL
98,DD
41,GA
60,GJ
72,HR
82,HP
81,JK
53,JH
31,KA
21,KL
92,LA
1,LD
51,MP
50,MH
48,MN
47,ML
37,MZ
58,NL
43,OD
88,PB
71,PY
61,RJ
66,SK
22,TN
65,TS
42,TR
46,UK
63,UP
73,UT
,,WB
"""

def hex_vertices(x, y, r=1):
    """Return 6 vertices of a flat-top hexagon."""
    return [(x + r * math.cos(math.radians(60 * i)), 
             y + r * math.sin(math.radians(60 * i))) 
            for i in range(6)]

def create_hex_grid(rows=10, cols=10, r=1):
    """Create flat-top hex grid."""
    w = 2 * r
    h = math.sqrt(3) * r
    h_spacing = 3/4 * w
    v_spacing = h
    
    hexes = []
    for row in range(rows):
        for col in range(cols):
            cx = col * h_spacing
            cy = row * v_spacing + (col % 2) * (v_spacing / 2)
            hexes.append({
                "hex_id": row * cols + col,
                "cx": cx,
                "cy": cy,
                "verts": hex_vertices(cx, cy, r)
            })
    
    return pd.DataFrame(hexes)

def load_hex_mapping():
    """Load embedded hex mapping."""
    return pd.read_csv(BytesIO(HEX_MAP_KEY.encode()))

def create_template():
    """Create template CSV with state codes."""
    mapping = load_hex_mapping()
    template = mapping[["code"]].sort_values("code").reset_index(drop=True)
    template["state"] = ""
    template["value"] = ""
    return template[["state", "code", "value"]]

def plot_hex_map(data_df, cmap_name="plasma"):
    """Plot hexagons colored by values."""
    # Prepare hex grid with codes
    hex_grid = create_hex_grid()
    mapping = load_hex_mapping()
    hex_data = hex_grid.merge(mapping, on="hex_id").merge(data_df, on="code", how="left")
    
    # Setup colormap
    valid_vals = hex_data["value"].dropna()
    if len(valid_vals) == 0:
        st.error("No valid numeric values found!")
        return None
    
    vmin, vmax = valid_vals.min(), valid_vals.max()
    cmap = cm.get_cmap(cmap_name)
    norm = Normalize(vmin=vmin, vmax=vmax)
    
    # Create patches
    patches = []
    colors = []
    for _, row in hex_data.iterrows():
        poly = Polygon(row["verts"], closed=True, edgecolor="black", linewidth=0.5)
        patches.append(poly)
        
        if pd.notna(row["value"]):
            colors.append(cmap(norm(row["value"])))
        else:
            colors.append("lightgrey")
    
    # Plot
    fig, ax = plt.subplots(figsize=(12, 10))
    collection = PatchCollection(patches, facecolor=colors, match_original=True)
    ax.add_collection(collection)
    
    # Add state code labels
    for _, row in hex_data.iterrows():
        if pd.notna(row["code"]):
            ax.text(row["cx"], row["cy"], row["code"], 
                   ha="center", va="center", fontsize=9, weight='bold')
    
    ax.set_aspect("equal")
    ax.autoscale()
    ax.margins(0.05)
    ax.axis("off")
    ax.set_title("India Hex Map", fontsize=18, pad=20, weight='bold')
    
    # Colorbar
    sm = cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array(valid_vals)
    cbar = fig.colorbar(sm, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("Value", fontsize=12)
    
    return fig

# Main app
st.title("🗺️ India Hex Map Visualizer")
st.markdown("Create hexagonal choropleth maps for Indian states in 2 simple steps")

# Sidebar for settings
with st.sidebar:
    st.header("⚙️ Settings")
    cmap_options = ["viridis", "plasma", "inferno", "magma", "cividis", 
                   "Blues", "Reds", "Greens", "YlOrRd", "RdYlGn", "Spectral"]
    cmap = st.selectbox("Color scheme", cmap_options, index=1)
    
    st.markdown("---")
    st.subheader("Available State Codes")
    mapping = load_hex_mapping()
    codes = sorted(mapping["code"].unique())
    
    # Display in 2 columns
    col1, col2 = st.columns(2)
    mid = len(codes) // 2
    with col1:
        for code in codes[:mid]:
            st.text(f"• {code}")
    with col2:
        for code in codes[mid:]:
            st.text(f"• {code}")

# Main content
st.markdown("### Step 1: Download Template")
template = create_template()
csv_buffer = BytesIO()
template.to_csv(csv_buffer, index=False)
csv_buffer.seek(0)

col1, col2 = st.columns([1, 2])
with col1:
    st.download_button(
        label="📥 Download Template CSV",
        data=csv_buffer,
        file_name="india_hex_map_template.csv",
        mime="text/csv",
        use_container_width=True
    )
with col2:
    st.info("Fill in the 'state' and 'value' columns, keeping the 'code' column unchanged")

st.markdown("---")
st.markdown("### Step 2: Upload Your Data")

data_file = st.file_uploader(
    "Upload your completed CSV file",
    type=["csv"],
    help="Upload the template with your state names and numeric values filled in"
)

if data_file:
    try:
        data_df = pd.read_csv(data_file)
        
        # Validate
        if "code" not in data_df.columns or "value" not in data_df.columns:
            st.error("CSV must contain 'code' and 'value' columns")
        else:
            # Clean data
            data_df["value"] = pd.to_numeric(data_df["value"], errors="coerce")
            data_df = data_df[data_df["value"].notna()]
            
            if len(data_df) == 0:
                st.error("No valid numeric values found in 'value' column")
            else:
                # Show preview
                with st.expander("📊 Data Preview", expanded=True):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("States", len(data_df))
                    with col2:
                        st.metric("Min", f"{data_df['value'].min():.2f}")
                    with col3:
                        st.metric("Max", f"{data_df['value'].max():.2f}")
                    
                    st.dataframe(data_df, use_container_width=True, height=200)
                
                # Plot
                st.markdown("---")
                fig = plot_hex_map(data_df, cmap_name=cmap)
                
                if fig:
                    st.pyplot(fig)
                    
                    # Download
                    img_buffer = BytesIO()
                    fig.savefig(img_buffer, format='png', dpi=300, bbox_inches='tight')
                    img_buffer.seek(0)
                    
                    st.download_button(
                        label="📥 Download Map (PNG)",
                        data=img_buffer,
                        file_name="india_hex_map.png",
                        mime="image/png",
                        use_container_width=True
                    )
                    
    except Exception as e:
        st.error(f"Error: {str(e)}")

# Footer
st.markdown("---")
st.caption("Made with ❤️ using Streamlit")

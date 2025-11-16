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
HEX_MAP_KEY = """hex_id,code,state
4,AN,Andaman and Nicobar Islands
32,AP,Andhra Pradesh
68,AR,Arunachal Pradesh
57,AS,Assam
64,BR,Bihar
87,CH,Chandigarh
52,GG,Chhattisgarh
62,DL,Delhi
98,DD,Daman and Diu
41,GA,Goa
60,GJ,Gujarat
72,HR,Haryana
82,HP,Himachal Pradesh
81,JK,Jammu and Kashmir
53,JH,Jharkhand
31,KA,Karnataka
21,KL,Kerala
92,LA,Ladakh
0,LD,Lakshadweep
51,MP,Madhya Pradesh
50,MH,Maharashtra
48,MN,Manipur
47,ML,Meghalaya
37,MZ,Mizoram
58,NL,Nagaland
43,OD,Odisha
88,PB,Puducherry
71,PY,Punjab
61,RJ,Rajasthan
66,SK,Sikkim
22,TN,Tamil Nadu
65,TS,Telangana
42,TR,Tripura
46,UK,Uttarakhand
63,UP,Uttar Pradesh
73,UT,West Bengal
55,WB,West Bengal
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
    template = mapping[["state", "code"]].sort_values("code").reset_index(drop=True)
    template["value"] = ""
    return template

def plot_hex_map(data_df, cmap_name="plasma", map_title="India Hex Map", author_name="", fig_size=(12, 10)):
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
    fig, ax = plt.subplots(figsize=fig_size)
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
    ax.set_title(map_title, fontsize=18, pad=20, weight='bold')
    
    # Colorbar
    sm = cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array(valid_vals)
    cbar = fig.colorbar(sm, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("Value", fontsize=12)
    
    # Add caption
    caption = f"Made by {author_name} | Created with Love by HexMapIndia" if author_name else "Created with Love by HexMapIndia"
    fig.text(0.5, 0.02, caption, ha='center', fontsize=10, style='italic', color='gray')
    
    return fig

# Main app
st.title("India Hex Map Visualizer")
st.markdown("Create hexagonal choropleth maps for Indian states in 2 simple steps")

# Sidebar for settings
with st.sidebar:
    st.header("Settings")
    cmap_options = ["viridis", "plasma", "inferno", "magma", "cividis", 
                   "Blues", "Reds", "Greens", "YlOrRd", "RdYlGn", "Spectral"]
    cmap = st.selectbox("Color scheme", cmap_options, index=1)
    
    map_title = st.text_input("Map title", value="India Hex Map")
    author_name = st.text_input("Author name", value="")
    
    st.markdown("---")
    map_size = st.radio("Map size", ["Small (10x8)", "Medium (12x10)", "Large (16x12)"], index=1)
    
    # Convert size selection to dimensions
    size_map = {
        "Small (10x8)": (10, 8),
        "Medium (12x10)": (12, 10),
        "Large (16x12)": (16, 12)
    }
    fig_size = size_map[map_size]

# Main content
st.markdown("### Step 1: Download Template")
template = create_template()
csv_buffer = BytesIO()
template.to_csv(csv_buffer, index=False)
csv_buffer.seek(0)

col1, col2 = st.columns([1, 2])
with col1:
    st.download_button(
        label="Download Template CSV",
        data=csv_buffer,
        file_name="india_hex_map_template.csv",
        mime="text/csv",
        use_container_width=True
    )
with col2:
    st.info("Fill in the 'value' column with your data, keeping 'state' and 'code' unchanged")

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
                # Show statistics
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("States", len(data_df))
                with col2:
                    st.metric("Min", f"{data_df['value'].min():.2f}")
                with col3:
                    st.metric("Max", f"{data_df['value'].max():.2f}")
                
                # Plot
                st.markdown("---")
                fig = plot_hex_map(data_df, cmap_name=cmap, map_title=map_title, author_name=author_name, fig_size=fig_size)
                
                if fig:
                    st.pyplot(fig)
                    
                    # Download
                    img_buffer = BytesIO()
                    fig.savefig(img_buffer, format='png', dpi=300, bbox_inches='tight')
                    img_buffer.seek(0)
                    
                    st.download_button(
                        label="Download Map (PNG)",
                        data=img_buffer,
                        file_name="india_hex_map.png",
                        mime="image/png",
                        use_container_width=True
                    )
                    
    except Exception as e:
        st.error(f"Error: {str(e)}")

# Footer
st.markdown("---")

import streamlit as st
import math
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from matplotlib.collections import PatchCollection
import matplotlib.cm as cm
from matplotlib.colors import Normalize
from io import BytesIO
import os
import json

# Page config
st.set_page_config(page_title="India Hex Map Visualizer", layout="wide")

# Counter file path
COUNTER_FILE = "map_counter.json"

def get_counter():
    """Get current map counter."""
    try:
        if os.path.exists(COUNTER_FILE):
            with open(COUNTER_FILE, 'r') as f:
                data = json.load(f)
                return data.get('count', 0)
    except:
        pass
    return 0

def increment_counter():
    """Increment the global map counter."""
    try:
        count = get_counter()
        count += 1
        with open(COUNTER_FILE, 'w') as f:
            json.dump({'count': count}, f)
        return count
    except:
        return None

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
42,TS,Telangana
46,TR,Tripura
73,UK,Uttarakhand
63,UP,Uttar Pradesh
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

def plot_hex_map(data_df, cmap_name="plasma", map_title="India Hex Map", author_name=""):
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
    cmap = plt.get_cmap(cmap_name)
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
    ax.set_title(map_title, fontsize=18, pad=20, weight='bold')
    
    # Colorbar
    sm = cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array(valid_vals)
    cbar = fig.colorbar(sm, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("Value", fontsize=12)
    
    # Add caption
    caption = f"Made with Love by {author_name} | Created with HexMapIndia" if author_name else "Created with HexMapIndia"
    fig.text(0.5, 0.02, caption, ha='center', fontsize=10, style='italic', color='gray')
    
    return fig

# Main app
st.title("🗺️ India Hex Map Visualizer")
st.markdown("Create beautiful hexagonal choropleth maps for Indian states in 2 simple steps • [Made by Akshar Katariya](https://aksharkatariya.github.io)")

# Sidebar for settings
with st.sidebar:
    st.header("⚙️ Customization")
    
    cmap_options = ["viridis", "plasma", "inferno", "magma", "cividis", 
                   "Blues", "Reds", "Greens", "YlOrRd", "RdYlGn", "Spectral"]
    cmap = st.selectbox(
        "Color scheme",
        cmap_options,
        index=1,
        help="Choose a color palette for your map"
    )
    
    map_title = st.text_input(
        "Map title",
        value="India Hex Map",
        help="Enter a custom title for your map"
    )
    
    author_name = st.text_input(
        "Author name (optional)",
        value="",
        help="Your name will appear in the map caption"
    )
    
    # Display counter
    st.markdown("---")
    counter = get_counter()
    st.metric("🌍 Maps Created Worldwide", f"{counter:,}")
    
   # Support section in sidebar
    st.markdown("---")
    st.markdown("### ☕ Support This Project")
    st.markdown(
        '<a href="https://www.buymeacoffee.com/aksharkatariya" target="_blank" '
        'style="font-size: 16px; text-decoration: none; color: #FFDD00; font-weight: bold;">'
        'Buy Me a Coffee</a>',
        unsafe_allow_html=True
    )


# Main content - Step 1
with st.container():
    st.markdown("### 📥 Step 1: Download Template")
    
    template = create_template()
    csv_buffer = BytesIO()
    template.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.download_button(
            label="📄 Download Template CSV",
            data=csv_buffer,
            file_name="india_hex_map_template.csv",
            mime="text/csv",
            use_container_width=True,
            help="Download the template CSV file to fill in your data"
        )
    with col2:
        st.info("💡 **Instructions:** Fill in the 'value' column with your numeric data. Keep 'state' and 'code' columns unchanged.")

st.markdown("")

# Main content - Step 2
with st.container():
    st.markdown("### 📤 Step 2: Upload Your Data")
    
    data_file = st.file_uploader(
        "Choose your completed CSV file",
        type=["csv"],
        help="Upload the template file after filling in the 'value' column with your data"
    )

    if data_file:
        try:
            data_df = pd.read_csv(data_file)
            
            # Validate
            if "code" not in data_df.columns or "value" not in data_df.columns:
                st.error("❌ CSV must contain 'code' and 'value' columns")
            else:
                # Clean data
                data_df["value"] = pd.to_numeric(data_df["value"], errors="coerce")
                data_df = data_df[data_df["value"].notna()]
                
                if len(data_df) == 0:
                    st.error("❌ No valid numeric values found in 'value' column")
                else:
                    # Show statistics
                    st.markdown("#### 📊 Data Summary")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("States/UTs", len(data_df))
                    with col2:
                        st.metric("Minimum Value", f"{data_df['value'].min():.2f}")
                    with col3:
                        st.metric("Maximum Value", f"{data_df['value'].max():.2f}")
                    
                    # Plot
                    st.markdown("---")
                    st.markdown("#### 🗺️ Your Map")
                    
                    with st.spinner("Generating your map..."):
                        fig = plot_hex_map(data_df, cmap_name=cmap, map_title=map_title, author_name=author_name)
                    
                    if fig:
                        # Increment counter when map is successfully generated
                        increment_counter()
                        
                        st.pyplot(fig)
                        
                        # Download
                        img_buffer = BytesIO()
                        fig.savefig(img_buffer, format='png', dpi=300, bbox_inches='tight')
                        img_buffer.seek(0)
                        
                        st.download_button(
                            label="💾 Download Map (High Resolution PNG)",
                            data=img_buffer,
                            file_name="india_hex_map.png",
                            mime="image/png",
                            use_container_width=True,
                            help="Download your map as a high-resolution PNG image (300 DPI)"
                        )
                        
                        st.success("✅ Map generated successfully!")
                        
        except Exception as e:
            st.error(f"❌ Error processing file: {str(e)}")

# Footer
st.markdown("---")
st.caption("Made with ❤️ using Streamlit | HexMapIndia")

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

# Helper functions
def hex_vertices(x, y, r=1, orientation="pointy"):
    """Return 6 vertices of a hexagon around (x, y)."""
    start_deg = 30 if orientation == "pointy" else 0
    return [
        (x + r * math.cos(math.radians(start_deg + 60 * i)),
         y + r * math.sin(math.radians(start_deg + 60 * i)))
        for i in range(6)
    ]

@st.cache_data
def create_hex_grid(rows=10, cols=10, r=1, orientation="flat"):
    """Create hex grid with specified parameters."""
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
                "cx": cx,
                "cy": cy,
                "verts": hex_vertices(cx, cy, r, orientation)
            })
    
    return pd.DataFrame(hexes)

@st.cache_data
def load_state_mapping(uploaded_file):
    """Load and process state hex key mapping."""
    df = pd.read_csv(uploaded_file)
    
    # Clean code column (assuming 2nd column)
    df["code"] = (
        df.iloc[:, 1]
        .astype(str)
        .str.replace("[^A-Za-z]", "", regex=True)
        .str.upper()
        .str[-2:]
    )
    
    return df[["hex_id", "code"]]

def create_template_csv(state_mapping):
    """Create a template CSV with state codes."""
    template = state_mapping[["code"]].drop_duplicates().sort_values("code")
    template["state"] = ""
    template["value"] = ""
    template = template[["state", "code", "value"]]
    return template

def plot_hex_map(hex_grid, df_values, code_col="code", value_col="value", cmap_name="viridis"):
    """Plot hexagons colored by numeric values."""
    plot_df = hex_grid.merge(df_values, on=code_col, how="left")
    
    # Prepare colormap
    vals = plot_df[value_col].dropna()
    if len(vals) == 0:
        st.error("No valid numeric values found in the data!")
        return None
    
    vmin, vmax = vals.min(), vals.max()
    cmap = cm.get_cmap(cmap_name)
    norm = Normalize(vmin=vmin, vmax=vmax)
    
    # Build patches and colors
    patches, facecolors = [], []
    for _, row in plot_df.iterrows():
        poly = Polygon(row["verts"], closed=True, edgecolor="black", linewidth=0.5)
        patches.append(poly)
        if pd.notna(row[value_col]):
            facecolors.append(cmap(norm(row[value_col])))
        else:
            facecolors.append("lightgrey")
    
    # Plot
    fig, ax = plt.subplots(figsize=(10, 10))
    collection = PatchCollection(patches, facecolor=facecolors, match_original=True)
    ax.add_collection(collection)
    
    # Labels
    for _, row in plot_df.iterrows():
        ax.text(row["cx"], row["cy"], row[code_col], ha="center", va="center", fontsize=8, weight='bold')
    
    ax.set_aspect("equal")
    ax.autoscale()
    ax.margins(0.05)
    ax.set_axis_off()
    ax.set_title("India Hex Map", fontsize=16, pad=20)
    
    # Add colorbar
    from matplotlib.cm import ScalarMappable
    sm = ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array(vals)
    fig.colorbar(sm, ax=ax, fraction=0.046, pad=0.04, label=value_col)
    
    return fig, plot_df

# Main app
st.title("🗺️ India Hex Map Visualizer")
st.markdown("Create beautiful hexagonal choropleth maps for Indian states")

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    
    # Upload state mapping file
    st.subheader("1. Upload State Mapping")
    state_key_file = st.file_uploader(
        "Upload state_hex_key.csv",
        type=["csv"],
        help="Upload your state_hex_key.csv file that maps states to hex grid positions"
    )
    
    if state_key_file:
        state_mapping = load_state_mapping(state_key_file)
        hex_grid = create_hex_grid()
        hexes_with_code = hex_grid.merge(state_mapping, on="hex_id", how="left")
        hexes_with_code = hexes_with_code[hexes_with_code["code"].notna()]
        
        st.success(f"✓ Loaded {len(hexes_with_code)} states")
        
        # Colormap selection
        st.subheader("2. Visualization Settings")
        cmap_options = ["viridis", "plasma", "inferno", "magma", "cividis", 
                       "Blues", "Reds", "Greens", "YlOrRd", "RdYlGn"]
        cmap = st.selectbox("Color scheme", cmap_options, index=1)

# Main content
if not state_key_file:
    st.info("👈 Please upload your state_hex_key.csv file in the sidebar to get started")
    st.markdown("""
    ### How to use this app:
    1. Upload your `state_hex_key.csv` file in the sidebar
    2. Download the template CSV file
    3. Fill in the template with your data (state names and values)
    4. Upload the completed file to visualize your data
    """)
else:
    tab1, tab2 = st.tabs(["📊 Visualize Data", "📋 Template"])
    
    with tab1:
        st.subheader("Upload Your Data")
        
        # Template download
        template = create_template_csv(state_mapping)
        csv_buffer = BytesIO()
        template.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)
        
        col1, col2 = st.columns([1, 3])
        with col1:
            st.download_button(
                label="📥 Download Template CSV",
                data=csv_buffer,
                file_name="india_hex_map_template.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        # Data upload
        st.markdown("---")
        data_file = st.file_uploader(
            "Upload your completed CSV file",
            type=["csv"],
            help="Upload a CSV with columns: state, code, value"
        )
        
        if data_file:
            try:
                data_df = pd.read_csv(data_file)
                
                # Validate columns
                required_cols = ["code", "value"]
                if not all(col in data_df.columns for col in required_cols):
                    st.error(f"CSV must contain columns: {', '.join(required_cols)}")
                else:
                    # Convert value to numeric
                    data_df["value"] = pd.to_numeric(data_df["value"], errors="coerce")
                    
                    # Show data preview
                    st.subheader("Data Preview")
                    st.dataframe(data_df.head(10), use_container_width=True)
                    
                    # Plot
                    st.subheader("Hex Map Visualization")
                    fig, plot_df = plot_hex_map(hexes_with_code, data_df, cmap_name=cmap)
                    
                    if fig:
                        st.pyplot(fig)
                        
                        # Download plot
                        img_buffer = BytesIO()
                        fig.savefig(img_buffer, format='png', dpi=300, bbox_inches='tight')
                        img_buffer.seek(0)
                        
                        st.download_button(
                            label="📥 Download Map (PNG)",
                            data=img_buffer,
                            file_name="india_hex_map.png",
                            mime="image/png"
                        )
                        
                        # Show statistics
                        with st.expander("📊 Data Statistics"):
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("States with data", data_df["code"].notna().sum())
                            with col2:
                                st.metric("Min value", f"{data_df['value'].min():.2f}")
                            with col3:
                                st.metric("Max value", f"{data_df['value'].max():.2f}")
                    
            except Exception as e:
                st.error(f"Error processing file: {str(e)}")
    
    with tab2:
        st.subheader("Available State Codes")
        st.markdown("Use these codes when filling out your template:")
        
        # Display state codes in columns
        codes_df = state_mapping[["code"]].drop_duplicates().sort_values("code").reset_index(drop=True)
        
        # Split into columns for better display
        n_cols = 4
        cols = st.columns(n_cols)
        codes_per_col = len(codes_df) // n_cols + 1
        
        for i, col in enumerate(cols):
            start_idx = i * codes_per_col
            end_idx = min((i + 1) * codes_per_col, len(codes_df))
            with col:
                for code in codes_df.iloc[start_idx:end_idx]["code"]:
                    st.text(f"• {code}")

# Footer
st.markdown("---")
st.markdown("Made with ❤️ using Streamlit | Upload your data to create stunning hex maps")

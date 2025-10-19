import streamlit as st
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from matplotlib.collections import PatchCollection
import matplotlib.cm as cm
from matplotlib.colors import Normalize
import pandas as pd
import io

# Template data for the CSV download
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

# Function to create template CSV
def create_template_csv():
    """Creates a template CSV file with state codes and empty values"""
    template_df = pd.DataFrame({
        'state': TEMPLATE_STATES,
        'code': TEMPLATE_CODES,
        'value': [0] * len(TEMPLATE_CODES)  # Empty values for user to fill
    })
    return template_df

# Function to plot hex map
def plot_hex_values(df_values, hex_grid, code_col="code", value_col="value", 
                    cmap_name="viridis", plot_title="India Hex Map"):
    """
    Plots hexagons colored by numeric values.
    
    Parameters:
    df_values : pd.DataFrame - DataFrame with code and value columns
    hex_grid : pd.DataFrame - Hex dataframe with 'code', 'verts', 'cx', 'cy' columns
    code_col : str - Column name for codes
    value_col : str - Column name for numeric values
    cmap_name : str - Matplotlib colormap name
    plot_title : str - Title for the plot
    """
    # Merge input values with hex grid
    plot_df = hex_grid.merge(df_values, on=code_col, how="left")
    
    # Prepare colormap
    vals = plot_df[value_col]
    vmin, vmax = vals.min(), vals.max()
    cmap = cm.get_cmap(cmap_name)
    norm = Normalize(vmin=vmin, vmax=vmax)
    
    # Build patches and colors
    patches = []
    facecolors = []
    for index, row in plot_df.iterrows():
        poly = Polygon(row["verts"], closed=True, edgecolor="black", linewidth=0.5)
        patches.append(poly)
        facecolors.append(cmap(norm(row[value_col])))
    
    # Create the plot
    fig, ax = plt.subplots(figsize=(10, 10))
    collection = PatchCollection(patches, facecolor=facecolors, match_original=True)
    ax.add_collection(collection)
    
    # Add labels to hexagons
    for index, row in plot_df.iterrows():
        ax.text(row["cx"], row["cy"], row[code_col], 
                ha="center", va="center", fontsize=8, fontweight='bold')
    
    ax.set_aspect("equal")
    ax.autoscale()
    ax.margins(0.05)
    ax.set_axis_off()
    ax.set_title(plot_title, fontsize=16, fontweight='bold', pad=20)
    
    # Add colorbar
    from matplotlib.cm import ScalarMappable
    sm = ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array(vals)
    fig.colorbar(sm, ax=ax, fraction=0.046, pad=0.04, label=value_col)
    
    return fig, plot_df

# Function to plot empty hex map
def plot_empty_hex_map(hex_grid):
    """Plots hexagons without any color values"""
    fig, ax = plt.subplots(figsize=(10, 10))
    
    patches = []
    for index, row in hex_grid.iterrows():
        poly = Polygon(row["verts"], closed=True, edgecolor="black", 
                      linewidth=0.5, facecolor='lightgray')
        patches.append(poly)
    
    collection = PatchCollection(patches, match_original=True)
    ax.add_collection(collection)
    
    # Add labels
    for index, row in hex_grid.iterrows():
        ax.text(row["cx"], row["cy"], row[code_col], 
                ha="center", va="center", fontsize=8, fontweight='bold')
    
    ax.set_aspect("equal")
    ax.autoscale()
    ax.margins(0.05)
    ax.set_axis_off()
    ax.set_title("India Hex Map (Upload data to visualize)", 
                fontsize=16, fontweight='bold', pad=20)
    
    return fig

# Streamlit App
def main():
    st.set_page_config(page_title="India Hex Map Visualizer", layout="wide")
    
    st.title("🗺️ India Hex Map Visualizer")
    st.markdown("Create beautiful hex map visualizations for Indian states and territories")
    
    # Sidebar
    st.sidebar.header("📁 Data Upload & Download")
    
    # Download template button
    st.sidebar.subheader("1. Download Template")
    template_df = create_template_csv()
    csv_template = template_df.to_csv(index=False)
    st.sidebar.download_button(
        label="⬇️ Download CSV Template",
        data=csv_template,
        file_name="india_hex_map_template.csv",
        mime="text/csv"
    )
    st.sidebar.markdown("*Fill in the 'value' column with your data*")
    
    # Upload file
    st.sidebar.subheader("2. Upload Your Data")
    uploaded_file = st.sidebar.file_uploader(
        "Upload filled CSV file", 
        type=['csv'],
        help="Upload the template CSV after filling in your values"
    )
    
    # Color scheme selector
    st.sidebar.subheader("3. Customize Visualization")
    colormap_options = [
        'viridis', 'plasma', 'inferno', 'magma', 'cividis',
        'Blues', 'Reds', 'Greens', 'Oranges', 'Purples',
        'YlOrRd', 'YlGnBu', 'RdYlGn', 'RdYlBu', 'Spectral'
    ]
    selected_colormap = st.sidebar.selectbox(
        "Select Color Scheme",
        colormap_options,
        index=0
    )
    
    # Plot title input
    plot_title = st.sidebar.text_input(
        "Enter Plot Title",
        value="India Hex Map"
    )
    
    # Load hex grid data (you need to load your hex_map_key.csv here)
    try:
        hex_grid = pd.read_csv('hex_map_key.csv')
    except:
        st.error("⚠️ Error: 'hex_map_key.csv' not found. Please ensure the file is in the same directory.")
        st.stop()
    
    # Main content area
    if uploaded_file is None:
        # Show empty map
        st.info("👆 Upload a CSV file from the sidebar to visualize your data")
        fig = plot_empty_hex_map(hex_grid)
        st.pyplot(fig)
        
    else:
        # Read uploaded file
        try:
            user_data = pd.read_csv(uploaded_file)
            
            # Validate the uploaded file
            if 'code' not in user_data.columns or 'value' not in user_data.columns:
                st.error("❌ Error: CSV must contain 'code' and 'value' columns")
                st.stop()
            
            # Show data preview
            with st.expander("📊 Preview Uploaded Data"):
                st.dataframe(user_data)
            
            # Create visualization
            fig, plot_df = plot_hex_values(
                user_data, 
                hex_grid, 
                code_col="code", 
                value_col="value",
                cmap_name=selected_colormap,
                plot_title=plot_title
            )
            
            # Display the map
            st.pyplot(fig)
            
            # Download button for the map
            st.sidebar.subheader("4. Download Map")
            buffer = io.BytesIO()
            fig.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
            buffer.seek(0)
            
            st.sidebar.download_button(
                label="⬇️ Download Map as PNG",
                data=buffer,
                file_name=f"{plot_title.replace(' ', '_')}.png",
                mime="image/png"
            )
            
            # Show statistics
            st.sidebar.subheader("📈 Statistics")
            st.sidebar.metric("Minimum Value", f"{user_data['value'].min():.2f}")
            st.sidebar.metric("Maximum Value", f"{user_data['value'].max():.2f}")
            st.sidebar.metric("Average Value", f"{user_data['value'].mean():.2f}")
            
        except Exception as e:
            st.error(f"❌ Error processing file: {str(e)}")
            st.stop()

if __name__ == "__main__":
    main()

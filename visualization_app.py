# Streamlit app to inspect and visualize data of GeoDataFrames created from user-uploaded WGS84 (EPSG:4326) GeoJSON files

import os
from datetime import datetime
import geopandas as gpd
import streamlit as st
import streamlit.components.v1 as components

# Used for creating visualizations
from visualization_tool import (
    VisualizationTool,
    Scheme,
    Numeric,
    Categorical,
    create_map,
    clear_map_html
)

# Data loading
def load_data(uploaded_file):
    """Loads a GeoJSON file into a GeoDataFrame and stores it in session state to keep it persistent between reruns"""
    try:
        ext = os.path.splitext(uploaded_file.name)[1][1:].lower()
        if ext == "geojson":
            gdf = gpd.read_file(uploaded_file, encoding="utf-8")
            gdf = gdf.to_crs(epsg=25832)
            
            env = st.session_state["geodataframes"]
            gdfs_num = len([obj for obj in env.values() if isinstance(obj, gpd.GeoDataFrame)])
            gdf_name = f"gdf_{gdfs_num}"
            env[gdf_name] = gdf
            
            return gdf_name
        else:
            st.error(f"Unsupported file format: {ext}")
            return None
    except Exception as e:
        st.error(f"Error loading file: {e}")
        return None

# Streamlit app logic
def main():
    st.set_page_config(
        page_title="Visualization app",
        page_icon="🗺️",
        layout="wide"
    )
    
    # Custom CSS to adjust sidebar width and padding
    st.markdown("""
    <style>
        [data-testid="stSidebar"] {
            width: 350px !important;
        }
        .block-container {
            padding: 28px !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Initialize session states to store objects persistently between reruns
    if "geodataframes" not in st.session_state:
        st.session_state["geodataframes"] = {}
    if "map" not in st.session_state:
        st.session_state["map"] = create_map()
    if "file_uploader_key" not in st.session_state:
        st.session_state["file_uploader_key"] = 0
    
    # Sidebar contains app info, data upload, map export and clear
    with st.sidebar:
        st.title("Visualization app")
        with st.expander("Info", expanded=False):
            st.markdown("""
            This app uses Streamlit and GeoPandas to visualize user-provided WGS84 (EPSG:4326) GeoJSON files.
                        
            ## Features
            - Visualize spatial data
            - Export interactive maps as HTML
            
            ## Supported Formats
            - GeoJSON in EPSG:4326
                        
            ## Visualization Types

            1. Geometrical data  
            - Display points, lines, or polygons

            2. Numeric data 
            - Classifies numeric column values 
            - Selectable classification scheme
            - Adjustable number of classes
            - Choosable matplotlib colormap

            3️. Categorical data  
            - Shows distinct categories from a column
            - Choosable matplotlib colormap

            4. Heatmap  
            - Visualize point density
            """)
        
        st.divider()
        
        # File upload: WGS84 GeoJSON files
        # TODO: Support for other data formats
        st.subheader("Upload Data")
        uploaded_files = st.file_uploader(
            "Upload GeoJSON files in WGS84 (EPSG:4326)",
            type=["geojson"],
            accept_multiple_files=True,
            key=st.session_state["file_uploader_key"],
            help="Upload one or more GeoJSON files in EPSG:4326"
        )
        
        if uploaded_files:
            for file in uploaded_files:
                gdf_name = load_data(file)
                if gdf_name:
                    st.success(f"Loaded: {gdf_name}")
            # Update key to reset uploader
            st.session_state["file_uploader_key"] += 1
            st.rerun()
        
        st.divider()
        
        # Export and clear buttons
        st.subheader("Actions")
        col1, col2 = st.columns(2)
        
        # Map export and clear logic
        with col1:
            # Export interactive map as HTML 
            if st.button("Export", use_container_width=True):
                timestamp = datetime.now().strftime("%d%m%Y_%H%M%S")
                output_path = "./Output/Maps"
                os.makedirs(output_path, exist_ok=True)
                
                cleaned_html = clear_map_html(st.session_state["map"].get_root().render())
                output_file = f"{output_path}/map_{timestamp}.html"
                
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(cleaned_html)
                st.success(f"Map exported!")
        
        with col2:
            # Clear map window and remove GeoDataFrames from session state
            if st.button("Clear", use_container_width=True):
                st.session_state["map"] = create_map()
                st.session_state["geodataframes"] = {}
                st.success("Map cleared!")
                st.rerun()

    # Main area with two columns: left for visualization settings, right for map display
    col1, col2 = st.columns([0.4, 0.6], gap="medium")
    
    # Left column used to inspect data and define visualization parameters
    with col1:
        st.header("Visualization settings")
        
        if not st.session_state["geodataframes"]:
            st.info("Upload GeoJSON files to get started.")
            st.stop()
        
        # Select GeoDataFrame
        gdf_names = list(st.session_state["geodataframes"].keys())
        selected_gdf = st.selectbox(
            "Select GeoDataFrame",
            gdf_names,
            help="Choose the GeoDataFrame to visualize"
        )
        
        if selected_gdf:
            gdf = st.session_state["geodataframes"][selected_gdf]
            
            # Show GeoDataFrame info
            with st.expander("Data", expanded=False):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.metric("Rows", len(gdf))
                    st.metric("Columns", len(gdf.columns))
                with col_b:
                    geom_types = gdf.geometry.type.unique().tolist()
                    st.write("**Geometry types:**")
                    st.write(", ".join(geom_types))
                
                st.dataframe(gdf, use_container_width=True)
            
            st.divider()
            
            # Layer name
            layer_name = st.text_input(
                "Layer name",
                value=f"Layer_{selected_gdf}",
                help="Name for this layer on the map"
            )
            
            # Visualization type
            viz_type = st.radio(
                "Visualization type",
                ["Geometries Only", "Numeric", "Categorical", "Heatmap"],
                help="Choose how to visualize the data"
            )
            
            st.divider()
            
            # Type-specific parameters
            numeric_params = None
            categorical_params = None
            use_heatmap = False
            use_geometries = False
            
            # Visualize numeric data
            if viz_type == "Numeric":
                st.subheader("Numeric parameters")

                # Determine all numeric columns except geometry
                numeric_cols = gdf.select_dtypes(include=['number']).columns.tolist()
        
                numeric_cols = [col for col in numeric_cols if col != 'geometry']
                
                if not numeric_cols:
                    st.warning("No numeric columns found!")
                else:
                    # Select the numeric column to visualize
                    col = st.selectbox("Column to visualize", numeric_cols)
                    
                    col_a, col_b = st.columns(2)
                    with col_a:
                        # Select the classification scheme to use
                        scheme = st.selectbox(
                            "Classification scheme",
                            [s.name for s in Scheme],
                            index=10,  # Default: Quantiles
                            help="Method for classifying numeric data"
                        )
                    with col_b:
                        # Define the number of classes
                        k = st.number_input(
                            "Number of classes",
                            min_value=2,
                            max_value=10,
                            value=5,
                            help="How many classes to divide the data into"
                        )
                    
                    # Optional matplotlib colormap
                    cmap = st.text_input(
                        "Colormap",
                        value="YlOrRd",
                        help="Matplotlib colormap name (e.g., 'Blues', 'Reds', 'viridis')"
                    )
                    
                    # Legend caption
                    caption = st.text_input(
                        "Legend Caption",
                        value=f"{col} classification"
                    )
                    
                    # Create numeric parameters dataclass
                    numeric_params = Numeric(
                        gdf_column=col,
                        k=k,
                        scheme=Scheme[scheme],
                        cmap=cmap,
                        legend_caption=caption
                    )
            
             # Visualize categorical data
            elif viz_type == "Categorical":
                st.subheader("Categorical parameters")
                
                cat_cols = gdf.select_dtypes(include=['object', 'category']).columns.tolist()
                # Remove geometry column if present
                cat_cols = [col for col in cat_cols if col != 'geometry']
                
                if not cat_cols:
                    st.warning("No categorical columns found!")
                else:
                    col = st.selectbox("Column to visualize", cat_cols)
                    unique_vals = gdf[col].unique().tolist()
                    
                    st.info(f"Found {len(unique_vals)} unique values")
                    
                    with st.expander("View unique values"):
                        st.write(unique_vals)
                    
                    cmap = st.text_input(
                        "Colormap",
                        value="Set3",
                        help="Matplotlib colormap for categorical data"
                    )
                    
                    caption = st.text_input(
                        "Legend Caption",
                        value=f"{col} Categories"
                    )
                    
                    categorical_params = Categorical(
                        gdf_column=col,
                        cmap=cmap,
                        legend_caption=caption
                    )
            
             # Visualize point density
            elif viz_type == "Heatmap":
                st.subheader("Heatmap")
                
                # Check if GeoDataFrame has point geometries
                point_count = len(gdf[gdf.geometry.type == 'Point'])
                
                if point_count == 0:
                    st.error(f"No point geometries found. Geometry types: {gdf.geometry.type.unique().tolist()}")
                else:
                    st.success(f"Found {point_count} point geometries")
                    st.info("Heatmap will visualize point density")
                    use_heatmap = True
            
            # Visualize geometries only
            else: 
                st.subheader("Geometries")
                st.info("Basic geometry visualization without classification")
                use_geometries = True
            
            st.divider()
            
            # Visualization button executes visualize method of the VisualizationTool object
            if st.button("Visualize", type="primary", use_container_width=True):
                with st.spinner("Creating visualization..."):
                    viz_tool = VisualizationTool(
                        folium_map=st.session_state["map"],
                        gdf_environment=st.session_state["geodataframes"]
                    )
                    
                    result = viz_tool.visualize(
                        gdf_name=selected_gdf,
                        layer_name=layer_name,
                        numeric=numeric_params,
                        categorical=categorical_params,
                        heatmap=use_heatmap,
                        geometries=use_geometries
                    )
                    if result:
                        st.success(result) 
                    else:
                        st.error(result) # Display error message
                    
                    st.rerun()
    
    # Right column: Map widget
    with col2:
        st.header("Map")
        
        with st.container():
            cleaned_html = clear_map_html(st.session_state["map"].get_root().render())
            components.html(cleaned_html, height=700, scrolling=False)

if __name__ == "__main__":
    main()
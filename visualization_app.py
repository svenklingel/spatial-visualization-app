# Streamlit app to inspect and visualize data of GeoDataFrames created from user-uploaded GeoJSON files

import os
from datetime import datetime
import geopandas as gpd
import streamlit as st
import streamlit.components.v1 as components
import importlib
from datetime import datetime
import matplotlib.pyplot as plt

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
    if "layers" not in st.session_state:
        st.session_state["layers"] = {}

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
            This app uses Streamlit and GeoPandas to visualize user-provided GeoJSON files.
                        
            ## Features
            - Visualize spatial data
            - Export interactive maps as HTML
            - Export layers as PNG images
            
            ## Supported Formats
            - GeoJSON
                        
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
        
        # File upload: GeoJSON files
        st.subheader("Upload Data")
        uploaded_files = st.file_uploader(
            "Upload GeoJSON files",
            type=["geojson"],
            accept_multiple_files=True,
            key=st.session_state["file_uploader_key"],
            help="Upload one or more GeoJSON files."
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

        # Selectbox to select one layer for an image of a layer as PNG
        selected_layer = None
        if st.session_state["layers"]:
            with st.expander("Current Layers", expanded=False):
                selected_layer = st.selectbox("Select a layer", options=list(st.session_state["layers"].keys()))
                st.write(f"Selected layer: {selected_layer}")

        col1, col2 = st.columns(2)
        
        # Map export and clear logic
        with col1:
            # Radio button to choose between exporting map as HTML or layer as PNG
            export_format = st.radio("Export format", options=["Map as HTML", "Layer as PNG"])

            # Export interactive map as HTML or layer as PNG
            if st.button("Export", width="stretch"):
                if export_format == "Layer as PNG":
                    if not selected_layer:
                        st.error("No layer selected for export!")
                    else:
                        try:
                            # Extract layer information from session state
                            layer_info = st.session_state["layers"][selected_layer]
                            vis_type = layer_info["visualization_type"]
                            gdf_name = layer_info["geodataframe"]
                            gdf = st.session_state["geodataframes"][gdf_name]
                            
                            # Get visualization parameters from layer info
                            numeric_params = layer_info.get("numeric_params")
                            categorical_params = layer_info.get("categorical_params")
                            use_heatmap = layer_info.get("heatmap", False)
                            use_geometries = layer_info.get("geometries", False)
                            
                            # Create output directory
                            timestamp = datetime.now().strftime("%d%m%Y_%H%M%S")
                            output_path = "./Output/Images"
                            os.makedirs(output_path, exist_ok=True)
                            output_file = f"{output_path}/{selected_layer}_{timestamp}.png"
                            
                            # Create visualization tool for plot method
                            viz_tool = VisualizationTool(
                                folium_map=st.session_state["map"],
                                gdf_environment=st.session_state["geodataframes"]
                            )
                            
                            # Use plot method to create visualization
                            result = viz_tool.visualize(
                                gdf_name=gdf_name,
                                layer_name=selected_layer,
                                method="plot",
                                numeric=numeric_params,
                                categorical=categorical_params,
                                heatmap=use_heatmap,
                                geometries=use_geometries,
                                figsize=(12, 10)
                            )
                            
                            if result is True:
                                # Save the plot
                                viz_tool.save_plot(output_file, dpi=300)
                                st.success(f"PNG exported to {output_file}")
                                
                                # Display preview
                                with open(output_file, "rb") as f:
                                    st.image(f.read(), use_container_width=True)
                            else:
                                st.error(f"Error creating visualization: {result}")

                        except Exception as e:
                            st.error(f"Error exporting PNG: {e}")

                else:
                    # Export as HTML
                    timestamp = datetime.now().strftime("%d%m%Y_%H%M%S")
                    output_path = "./Output/Maps"
                    os.makedirs(output_path, exist_ok=True)
                    
                    cleaned_html = clear_map_html(st.session_state["map"].get_root().render())
                    output_file = f"{output_path}/map_{timestamp}.html"
                    
                    with open(output_file, "w", encoding="utf-8") as f:
                        f.write(cleaned_html)
                    st.success(f"Map exported as HTML to {output_file}")
        
        with col2:
            # Clear map window and remove GeoDataFrames from session state
            if st.button("Clear", width="stretch"):
                st.session_state["map"] = create_map()
                st.session_state["geodataframes"] = {}
                st.session_state["layers"] = {}
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

        # Show latest GDF by default
        default_index = len(gdf_names) - 1 if gdf_names else 0

        selected_gdf = st.selectbox(
            "Select GeoDataFrame",
            gdf_names,
            index=default_index,
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

                # Display GeoDataFrame with WKT (avoid serialization issues with geometry column)
                gdf["wkt"] = gdf.geometry.astype("string")

                # Use all columns except geometry for display
                cols_without_geometry = [c for c in gdf.columns if c != "geometry"]

                # Show DataFrame without geometry column
                st.dataframe(gdf[cols_without_geometry], use_container_width=True)
                            
            st.divider()
            
            # Layer name
            existing_layers = st.session_state.get("layers", {}).keys()

            base_name = f"Layer_{selected_gdf}"
            layer_name_default = base_name

            # Falls Name schon existiert → durchnummerieren
            i = 1
            while layer_name_default in existing_layers:
                layer_name_default = f"{base_name}_{i}"
                i += 1

            layer_name = st.text_input(
                "Layer name",
                value=layer_name_default,
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
                    
                    # Use explore method for interactive map
                    result = viz_tool.visualize(
                        gdf_name=selected_gdf,
                        layer_name=layer_name,
                        method="explore",
                        numeric=numeric_params,
                        categorical=categorical_params,
                        heatmap=use_heatmap,
                        geometries=use_geometries
                    )

                    # Determine visualization type
                    if numeric_params:
                        vis_type = "numeric"
                    elif categorical_params:
                        vis_type = "categorical"
                    elif use_heatmap:
                        vis_type = "heatmap"
                    else:
                        vis_type = "geometries"

                    if result is True:
                        # Store layer information including all visualization parameters
                        st.session_state["layers"][layer_name] = {
                            "geodataframe": selected_gdf,
                            "visualization_type": vis_type,
                            "numeric_params": numeric_params,
                            "categorical_params": categorical_params,
                            "heatmap": use_heatmap,
                            "geometries": use_geometries
                        }
                        
                        st.success(f"Layer '{layer_name}' created successfully!") 
                    else:
                        st.error(result)  # Display error message
                    
                    st.rerun()
    
    # Right column: Map widget
    with col2:
        st.header("Map")
        
        with st.container():
            cleaned_html = clear_map_html(st.session_state["map"].get_root().render())
            components.html(cleaned_html, height=700, scrolling=False)

if __name__ == "__main__":
    main()
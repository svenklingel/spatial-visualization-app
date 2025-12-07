# Tool to visualize GeoDataFrames using GeoDataFrame.explore() for interactive maps or plot() for static maps.

import re
import geopandas as gpd
import folium as f
import matplotlib.pyplot as plt
from typing import Dict, List, Optional, Literal
from folium.plugins import HeatMap, Draw, Geocoder, MousePosition, Fullscreen, LocateControl, MeasureControl
from enum import Enum
from pydantic import BaseModel, Field
from pyproj import Transformer
import PIL

# Helper functions 
def add_layer_control(map):
    """Add LayerControls to the map"""
    f.LayerControl().add_to(map)

def fit_map(gdf, map):
    """Zoom to the Bbox of the last visualized GeoDataframe"""
    minx, miny, maxx, maxy = gdf.total_bounds
    
    # Transform coordinates from the GeoDataFrame CRS to target EPSG
    transformer = Transformer.from_crs(gdf.crs, "EPSG:4326", always_xy=True)
    minx_t, miny_t = transformer.transform(minx, miny)
    maxx_t, maxy_t = transformer.transform(maxx, maxy)
    
    # Fit map bounds (folium uses [lat, lon])
    map.fit_bounds([[miny_t, minx_t], [maxy_t, maxx_t]])
   
def clear_map_html(html_content):
    """Remove old LayerControls"""
    layer_control_var_pattern = r'var layer_control_[a-f0-9]+_layers = \{[^}]+\};'
    layer_control_creation_pattern = r'let layer_control_[a-f0-9]+ = L\.control\.layers\([^)]+\)\.addTo\(map_[a-f0-9]+\);'
    
    var_matches = list(re.finditer(layer_control_var_pattern, html_content))
    creation_matches = list(re.finditer(layer_control_creation_pattern, html_content))
    
    if len(var_matches) > 1:
        for match in var_matches[:-1]:
            html_content = html_content.replace(match.group(0), '')
    if len(creation_matches) > 1:
        for match in creation_matches[:-1]:
            html_content = html_content.replace(match.group(0), '')
    return html_content

def create_map():
    """Creates an empty Folium map"""
    # Default empty folium.map
    m = f.Map(tiles=None, location=[51.44, 9.83], zoom_start=6)

    # Adds the possiblity to geocode location 
    Geocoder().add_to(m)

    # Adds the possibility to draw geometries which are stored in a FeatureGroup
    draw_feature_group = f.FeatureGroup(name="Geometries")
    draw_feature_group.add_to(m)
    Draw(feature_group=draw_feature_group).add_to(m) 

    # Adds the possibility to see coordinates at the current mouse position
    MousePosition().add_to(m)

    # Adds the possibility to show map in fullscreen
    Fullscreen(
        position="topright",
        title="Expand me",
        title_cancel="Exit me",
        force_separate_button=True,
    ).add_to(m)

    # Adds a control button that when clicked, the user device geolocation is displayed
    LocateControl().add_to(m)

    # Adds the possibility to measure distances
    MeasureControl().add_to(m)

    # Adds two side-by-side layers displaying XYZ-tiles either from OpenTopoMap or Google Satellite Hybrid
    layer_right = f.TileLayer(
        tiles='https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',
        attr='Map data: &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        name='OpenTopoMap',
        control=False
    )
    layer_left = f.TileLayer(
        tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}',
        attr='Imagery @2024 TerraMetrics',
        name='Google Satellite Hybrid',
        control=False
    )
    
    sbs = f.plugins.SideBySideLayers(layer_left, layer_right)
    layer_left.add_to(m)
    layer_right.add_to(m)
    sbs.add_to(m)

    # Adds the possibility to choose the layers to display
    f.LayerControl().add_to(m)

    # Adds a custom CSS style for the popup content
    style = """
    <style>
    .leaflet-popup-content-wrapper {
        overflow: auto !important;
        max-width: 200px !important;
        max-height: 175px !important;
    }
    </style>
    """
    m.get_root().html.add_child(f.Element(style))
    
    # The updated folium.map 
    return m

# Models to define the data structure of numeric and categorical visualizations
class Scheme(Enum):
    """Classification schema"""
    BoxPlot = "BoxPlot"
    EqualInterval = "EqualInterval"
    FisherJenks = "FisherJenks"
    FisherJenksSampled = "FisherJenksSampled"
    HeadTailBreaks = "HeadTailBreaks"
    JenksCaspall = "JenksCaspall"
    JenksCaspallForced = "JenksCaspallForced"
    JenksCaspallSampled = "JenksCaspallSampled"
    MaxP = "MaxP"
    MaximumBreaks = "MaximumBreaks"
    NaturalBreaks = "NaturalBreaks"
    Quantiles = "Quantiles"
    Percentiles = "Percentiles"
    StdMean = "StdMean"

class Numeric(BaseModel):
    """Parameters for numeric visualizations"""
    gdf_column: str = Field(description="Name of the column to visualize")
    k: Optional[int] = Field(default=None, description="Number of classes")
    scheme: Optional[Scheme] = Field(default=None, description="Classification scheme (None = continuous)")
    cmap: str = Field(description="Matplotlib Colormap Name")
    vmin: Optional[float] = Field(default=None, description="Minimum value for color scale")
    vmax: Optional[float] = Field(default=None, description="Maximum value for color scale")
    legend_caption: str = Field(description="Legend title")

class Categorical(BaseModel):
    """Parameters for categorical visualizations"""
    gdf_column: str = Field(description="Name of the column to visualize")
    cmap: str = Field(description="Matplotlib Colormap Name")
    legend_caption: str = Field(description="Legend title")
    # Liste von strings
    categories: Optional[List[str]] = Field(default=None, description="List of categories")

# Used as wrapper for GeoDataFrame.explore() and plot()
class VisualizationTool:
    """
    Tool for visualizing GeoDataFrames based on GeoDataFrame.explore or plot with various options:
    - Numeric data
    - Categorical data
    - Heatmap 
    - Geometries
    """
    
    def __init__(self, folium_map: f.Map, gdf_environment: Dict[str, gpd.GeoDataFrame]):
        """
        Args:
            folium_map: The folium.Map where data will be added
            gdf_environment: Dictionary with GeoDataFrame names as keys and GeoDataFrame objects as values
        """
        self.map = folium_map
        self.env = gdf_environment
        self.current_fig = None
        self.current_ax = None
    
    def visualize(
        self,
        gdf_name: str,
        layer_name: str,
        method: Literal["explore", "plot"] = "explore",
        numeric: Optional[Numeric] = None,
        categorical: Optional[Categorical] = None,
        heatmap: bool = False,
        geometries: bool = False,
        figsize: tuple = (12, 8)
    ) -> str:
        """
        Visualizes a GeoDataFrame on the map or as static plot.

        Args:
            gdf_name: Name of the GeoDataFrame to visualize
            layer_name: Name of the layer on the map / plot title
            method: Visualization method - "explore" (interactive) or "plot" (static)
            numeric: Parameters for numeric visualization
            categorical: Parameters for categorical visualization
            heatmap: Whether to create a heatmap
            geometries: Whether to visualize only geometries
            figsize: Figure size for plot method (width, height)

        Returns:
            True if successful, error message otherwise
        """
        # Validation of the arguments
        if not (gdf_name and layer_name):
            return "GeoDataFrame name and layer name are required."
        
        if not (numeric or categorical or heatmap or geometries):
            return "At least one visualization option must be provided."
        
        # Get GeoDataFrame
        if gdf_name not in self.env:
            return f"{gdf_name} is not a valid GeoDataFrame name. Available: {list(self.env.keys())}"
        
        gdf = self.env[gdf_name]
        if not isinstance(gdf, gpd.GeoDataFrame):
            return f"{gdf_name} is of type {type(gdf)} which is not supported."
        
        # Route to appropriate method
        if method == "explore":
            return self._visualize_explore(gdf, gdf_name, layer_name, numeric, categorical, heatmap, geometries)
        elif method == "plot":
            return self._visualize_plot(gdf, gdf_name, layer_name, numeric, categorical, heatmap, geometries, figsize)
        else:
            return f"Invalid method '{method}'. Use 'explore' or 'plot'."
    
    def _visualize_explore(self, gdf: gpd.GeoDataFrame, gdf_name: str, layer_name: str,
                          numeric, categorical, heatmap, geometries):
        """Handle visualization using explore method"""
        # Remove current LayerControl
        for item in list(self.map._children):
            if item.startswith('layer_control'):
                del self.map._children[item]
        
        # Create visualization based on the selected type
        if numeric:
            return self._visualize_numeric_explore(gdf, gdf_name, layer_name, numeric)
        elif categorical:
            return self._visualize_categorical_explore(gdf, gdf_name, layer_name, categorical)
        elif heatmap:
            return self._visualize_heatmap_explore(gdf, gdf_name, layer_name)
        elif geometries:
            return self._visualize_geometries_explore(gdf, gdf_name, layer_name)
    
    def _visualize_plot(self, gdf: gpd.GeoDataFrame, gdf_name: str, layer_name: str,
                       numeric, categorical, heatmap, geometries, figsize):
        """Handle visualization using plot method"""
        # Create new figure for this visualization
        self.current_fig, self.current_ax = plt.subplots(1, 1, figsize=figsize)
        
        # Create visualization based on the selected type
        if numeric:
            return self._visualize_numeric_plot(gdf, gdf_name, layer_name, numeric)
        elif categorical:
            return self._visualize_categorical_plot(gdf, gdf_name, layer_name, categorical)
        elif heatmap:
            return self._visualize_heatmap_plot(gdf, gdf_name, layer_name)
        elif geometries:
            return self._visualize_geometries_plot(gdf, gdf_name, layer_name)
    
    def _visualize_numeric_explore(self, gdf: gpd.GeoDataFrame, gdf_name: str, 
                           layer_name: str, params: Numeric) -> str:
        """Visualize data of a numeric column using explore"""
        try:
            column = params.gdf_column
            
            if column not in gdf.columns:
                return f"Column '{column}' not found in {gdf_name}. Available columns: {list(gdf.columns)}"
            
            if not gpd.pd.api.types.is_numeric_dtype(gdf[column]):
                return f"Column '{column}' is not numeric. Type: {gdf[column].dtype}"
            
            explore_kwargs = dict(
                popup=True,
                tooltip=column,
                column=column,
                cmap=params.cmap,
                vmin=params.vmin,
                vmax=params.vmax,
                name=layer_name,
                legend=True,
                m=self.map,
                # Show colorbar for continuous scale (no scheme); hide for classified schemes
                legend_kwds={"caption": params.legend_caption, "colorbar": (True if params.scheme is None else False)},
                style_kwds={"fillOpacity": "0.85", "weight": "1.5"}
            )
            if params.k:
                explore_kwargs["k"] = params.k
            if params.scheme:
                explore_kwargs["scheme"] = params.scheme.name

            gdf.explore(**explore_kwargs)
            
            add_layer_control(self.map)
            fit_map(gdf, self.map)
            return True
        except Exception as e:
            add_layer_control(self.map)
            return f"Could not visualize numeric column '{column}' of {gdf_name}. Error: {str(e)}"
    
    def _visualize_numeric_plot(self, gdf: gpd.GeoDataFrame, gdf_name: str,
                               layer_name: str, params: Numeric) -> str:
        """Visualize data of a numeric column using plot"""
        try:
            column = params.gdf_column
            
            if column not in gdf.columns:
                return f"Column '{column}' not found in {gdf_name}. Available columns: {list(gdf.columns)}"
            
            if not gpd.pd.api.types.is_numeric_dtype(gdf[column]):
                return f"Column '{column}' is not numeric. Type: {gdf[column].dtype}"
            
            plot_kwargs = dict(
                column=column,
                ax=self.current_ax,
                legend=True,
                cmap=params.cmap,
                vmin=params.vmin,
                vmax=params.vmax,
                edgecolor='black',
                linewidth=0.5
            )
            if params.k:
                plot_kwargs["k"] = params.k
            if params.scheme:
                plot_kwargs["scheme"] = params.scheme.name

            gdf.plot(**plot_kwargs)
            
            self.current_ax.set_title(layer_name, fontsize=14, fontweight='bold')
            self.current_ax.set_axis_off()
            plt.tight_layout()
            
            return True
        except Exception as e:
            return f"Could not visualize numeric column '{column}' of {gdf_name}. Error: {str(e)}"
    
    def _visualize_categorical_explore(self, gdf: gpd.GeoDataFrame, gdf_name: str,
                              layer_name: str, params: Categorical) -> str:
        """Visualize data of a categorical column using explore"""
        try:
            column = params.gdf_column
            
            if column not in gdf.columns:
                return f"Column '{column}' not found in {gdf_name}. Available columns: {list(gdf.columns)}"
            
            # If categories are provided, only plot those
            if params.categories:
                gdf = gdf[gdf[column].isin(params.categories)]
                
            gdf.explore(
                popup=True,
                tooltip=column,
                column=column,
                cmap=params.cmap,
                name=layer_name,
                legend=True,
                legend_kwds={"caption": params.legend_caption, "colorbar": False},
                categorical=True,
                categories=params.categories,
                m=self.map,
                style_kwds={"fillOpacity": "0.85", "weight": "1.5"}
            )
            
            add_layer_control(self.map)
            fit_map(gdf, self.map)
            
            return True
        except Exception as e:
            add_layer_control(self.map)
            return f"Could not visualize categorical column '{column}' of {gdf_name}. Error: {str(e)}"
    
    def _visualize_categorical_plot(self, gdf: gpd.GeoDataFrame, gdf_name: str,
                                   layer_name: str, params: Categorical) -> str:
        """Visualize data of a categorical column using plot"""
        try:
            column = params.gdf_column
            
            if column not in gdf.columns:
                return f"Column '{column}' not found in {gdf_name}. Available columns: {list(gdf.columns)}"
            
            # If categories are provided, only plot those
            if params.categories:
                gdf = gdf[gdf[column].isin(params.categories)]
            
            gdf.plot(
                column=column,
                ax=self.current_ax,
                legend=True,
                cmap=params.cmap,
                categorical=True,
                categories=params.categories,
                edgecolor='black',
                linewidth=0.5
            )
            
            self.current_ax.set_title(layer_name, fontsize=14, fontweight='bold')
            self.current_ax.set_axis_off()
            plt.tight_layout()
            
            return True
        except Exception as e:
            return f"Could not visualize categorical column '{column}' of {gdf_name}. Error: {str(e)}"
    
    def _visualize_heatmap_explore(self, gdf: gpd.GeoDataFrame, gdf_name: str,
                          layer_name: str) -> str:
        """Visualize the density of points using explore"""
        try:
            point_gdf = gdf[gdf.geometry.type == 'Point']
            
            if len(point_gdf) == 0:
                return f"No point geometries found in {gdf_name}. Geometry types: {gdf.geometry.type.unique().tolist()}"
            
            heat_data = [[point.xy[1][0], point.xy[0][0]] 
                        for point in point_gdf.geometry.to_crs(epsg=4326)]
            
            HeatMap(heat_data).add_to(
                f.FeatureGroup(name=layer_name).add_to(self.map)
            )
            
            add_layer_control(self.map)
            fit_map(gdf, self.map)
            
            return True
        except Exception as e:
            add_layer_control(self.map)
            return f"Could not create heatmap for {gdf_name}. Error: {str(e)}"
    
    def _visualize_heatmap_plot(self, gdf: gpd.GeoDataFrame, gdf_name: str,
                               layer_name: str) -> str:
        """Visualize the density of points using Folium HeatMap converted to image"""
        try:
            import io
            from PIL import Image
            
            point_gdf = gdf[gdf.geometry.type == 'Point']
            
            if len(point_gdf) == 0:
                return f"No point geometries found in {gdf_name}. Geometry types: {gdf.geometry.type.unique().tolist()}"
            
            # Convert to WGS84 for folium
            heat_data = [[point.xy[1][0], point.xy[0][0]] 
                        for point in point_gdf.geometry.to_crs(epsg=4326)]
            
            # Create temporary folium map with HeatMap
            center_lat = point_gdf.geometry.to_crs(epsg=4326).y.mean()
            center_lon = point_gdf.geometry.to_crs(epsg=4326).x.mean()
            
            temp_map = f.Map(location=[center_lat, center_lon], zoom_start=12, tiles='OpenStreetMap')
            HeatMap(heat_data).add_to(temp_map)
            
            # Fit to heatmap data
            fit_map(gdf, temp_map)
            # Convert folium map to PNG
            img_data = temp_map._to_png(5)  # delay in seconds for rendering
            img = Image.open(io.BytesIO(img_data))
            
            # Display image in matplotlib axes
            self.current_ax.imshow(img)
            self.current_ax.set_title(layer_name, fontsize=14, fontweight='bold')
            self.current_ax.set_axis_off()
            plt.tight_layout()
            
            return True
        except Exception as e:
            return f"Could not create heatmap for {gdf_name}. Error: {str(e)}"
    
    def _visualize_geometries_explore(self, gdf: gpd.GeoDataFrame, gdf_name: str,
                             layer_name: str) -> str:
        """Visualize only geometries using explore"""
        try:
            gdf.explore(
                popup=True,
                tooltip=False,
                name=layer_name,
                m=self.map,
                style_kwds={"fillOpacity": "0.85", "weight": "1.5"}
            )
            
            add_layer_control(self.map)
            fit_map(gdf, self.map)
            
            return True
        except Exception as e:
            add_layer_control(self.map)
            return f"Could not visualize geometries of {gdf_name}. Error: {str(e)}"
    
    def _visualize_geometries_plot(self, gdf: gpd.GeoDataFrame, gdf_name: str,
                                  layer_name: str) -> str:
        """Visualize only geometries using plot"""
        try:
            gdf.plot(
                ax=self.current_ax,
                edgecolor='black',
                facecolor='lightblue',
                linewidth=0.5,
                alpha=0.7
            )
            
            self.current_ax.set_title(layer_name, fontsize=14, fontweight='bold')
            self.current_ax.set_axis_off()
            plt.tight_layout()
            
            return True
        except Exception as e:
            return f"Could not visualize geometries of {gdf_name}. Error: {str(e)}"
    
    def show_plot(self):
        """Display the current plot"""
        if self.current_fig:
            plt.show()
        else:
            print("No plot to show. Create a visualization first with method='plot'.")
    
    def save_plot(self, filename: str, dpi: int = 300):
        """Save the current plot to file"""
        if self.current_fig:
            self.current_fig.savefig(filename, dpi=dpi, bbox_inches='tight')
            print(f"Plot saved to {filename}")
        else:
            print("No plot to save. Create a visualization first with method='plot'.")
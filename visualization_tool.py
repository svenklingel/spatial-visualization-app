# Tool to visualize data of GeoDataFrames created from user-uploaded WGS84 (EPSG:4326) GeoJSON files using GeoDataFrame.explore()

import re
import geopandas as gpd
import folium as f
from typing import Dict, Optional
from folium.plugins import HeatMap, Draw, Geocoder, MousePosition, Fullscreen, LocateControl, MeasureControl
from enum import Enum
from pydantic import BaseModel, Field
from pyproj import Transformer

# Helper functions 
def add_layer_control(map):
    """Add LayerControls to the map"""
    f.LayerControl().add_to(map)

def fit_map(gdf, map):
    """Zoom to the Bbox of the last visualized GeoDataframe"""
    minx, miny, maxx, maxy = gdf.total_bounds
    transformer = Transformer.from_crs("EPSG:25832", "EPSG:4326", always_xy=True)
    minx_wgs84, miny_wgs84 = transformer.transform(minx, miny)
    maxx_wgs84, maxy_wgs84 = transformer.transform(maxx, maxy)
    map.fit_bounds([[miny_wgs84, minx_wgs84], [maxy_wgs84, maxx_wgs84]])

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
    scheme: Scheme = Field(description="Classification scheme")
    cmap: str = Field(description="Matplotlib Colormap Name")
    legend_caption: str = Field(description="Legend title")

class Categorical(BaseModel):
    """Parameters for categorical visualizations"""
    gdf_column: str = Field(description="Name of the column to visualize")
    cmap: str = Field(description="Matplotlib Colormap Name")
    legend_caption: str = Field(description="Legend title")

# Used as wrapper for GeoDataFrame.explore()
class VisualizationTool:
    """
    Tool for visualizing GeoDataFrames based on GeoDataFrame.explore with various options:
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
    
    def visualize(
        self,
        gdf_name: str,
        layer_name: str,
        numeric: Optional[Numeric] = None,
        categorical: Optional[Categorical] = None,
        heatmap: bool = False,
        geometries: bool = False
    ) -> str:
        """
        Visualizes a GeoDataFrame on the map.

        Args:
            gdf_name: Name of the GeoDataFrame to visualize
            layer_name: Name of the layer on the map
            numeric: Parameters for numeric visualization
            categorical: Parameters for categorical visualization
            heatmap: Whether to create a heatmap
            geometries: Whether to visualize only geometries

        Returns:
            True if successful, error message otherwise
        """
        # Validation of the arguments
        if not (gdf_name and layer_name):
            return "GeoDataFrame name and layer name are required."
        
        if not (numeric or categorical or heatmap or geometries):
            return "At least one visualization option must be provided."
        
        # GeoDataFrame abrufen
        if gdf_name not in self.env:
            return f"{gdf_name} is not a valid GeoDataFrame name. Available: {list(self.env.keys())}"
        
        gdf = self.env[gdf_name]
        if not isinstance(gdf, gpd.GeoDataFrame):
            return f"{gdf_name} is of type {type(gdf)} which is not supported."
        
        # Its needed to remove the current LayerControl and add the new one later otherwise there will be more than one
        for item in list(self.map._children):
            if item.startswith('layer_control'):
                del self.map._children[item]
        
        # Create visualization based on the selected type
        if numeric:
            return self._visualize_numeric(gdf, gdf_name, layer_name, numeric)
        elif categorical:
            return self._visualize_categorical(gdf, gdf_name, layer_name, categorical)
        elif heatmap:
            return self._visualize_heatmap(gdf, gdf_name, layer_name)
        elif geometries:
            return self._visualize_geometries(gdf, gdf_name, layer_name)
    
    def _visualize_numeric(self, gdf: gpd.GeoDataFrame, gdf_name: str, 
                          layer_name: str, params: Numeric) -> str:
        """Visualize data of a numeric column"""
        try:
            column = params.gdf_column
            
            # Check if selected column is available
            if column not in gdf.columns:
                return f"Column '{column}' not found in {gdf_name}. Available columns: {list(gdf.columns)}"
            
            # Check if column is numeric
            if not gpd.pd.api.types.is_numeric_dtype(gdf[column]):
                return f"Column '{column}' is not numeric. Type: {gdf[column].dtype}"
            
            # Add the new visualization data to the folium.map
            gdf.explore(
                popup=True,
                tooltip=column,
                column=column,
                k=params.k,
                scheme=params.scheme.name,
                cmap=params.cmap,
                name=layer_name,
                legend=True,
                m=self.map,
                legend_kwds={"caption": params.legend_caption, "colorbar": False},
                style_kwds={"fillOpacity": "0.85", "weight": "1.5"}
            )
            
            # Add the new LayerControl
            add_layer_control(self.map)

            # Zoom the map to the Bbox of the last added layer
            fit_map(gdf, self.map)
            return True
        except Exception as e:
            add_layer_control(self.map)
            return f"Could not visualize numeric column '{column}' of {gdf_name}. Error: {str(e)}"
    
    def _visualize_categorical(self, gdf: gpd.GeoDataFrame, gdf_name: str,
                              layer_name: str, params: Categorical) -> str:
        """Visualize data of a categorical column"""
        try:
            column = params.gdf_column
            
            if column not in gdf.columns:
                return f"Column '{column}' not found in {gdf_name}. Available columns: {list(gdf.columns)}"
            
            gdf.explore(
                popup=True,
                tooltip=column,
                column=column,
                cmap=params.cmap,
                name=layer_name,
                legend=True,
                legend_kwds={"caption": params.legend_caption, "colorbar": False},
                categorical=True,
                m=self.map,
                style_kwds={"fillOpacity": "0.85", "weight": "1.5"}
            )
            
            add_layer_control(self.map)
            fit_map(gdf, self.map)
            
            return True
        except Exception as e:
            add_layer_control(self.map)
            return f"Could not visualize categorical column '{column}' of {gdf_name}. Error: {str(e)}"
    
    def _visualize_heatmap(self, gdf: gpd.GeoDataFrame, gdf_name: str,
                          layer_name: str) -> str:
        """Visualize the density of points."""
        try:
            # Only use valid point geoemtries
            point_gdf = gdf[gdf.geometry.type == 'Point']
            
            if len(point_gdf) == 0:
                return f"No point geometries found in {gdf_name}. Geometry types: {gdf.geometry.type.unique().tolist()}"
            
            # Convert to WGS84 and create a list of lists of coordinates value pairs (x,y)
            heat_data = [[point.xy[1][0], point.xy[0][0]] 
                        for point in point_gdf.geometry.to_crs(epsg=4326)]
            
            # Add heatmap layer to the map
            HeatMap(heat_data).add_to(
                f.FeatureGroup(name=layer_name).add_to(self.map)
            )
            
            add_layer_control(self.map)
            fit_map(gdf, self.map)
            
            return True
        except Exception as e:
            add_layer_control(self.map)
            return f"Could not create heatmap for {gdf_name}. Error: {str(e)}"
    
    def _visualize_geometries(self, gdf: gpd.GeoDataFrame, gdf_name: str,
                             layer_name: str) -> str:
        """Visualize only geometries"""
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
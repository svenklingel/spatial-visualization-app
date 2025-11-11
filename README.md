The app uses Streamlit and GeoPandas to visualize user-provided WGS84 (EPSG:4326) GeoJSON files.

## Features
- Visualize spatial data 
- Export interactive maps as HTML

## Supported Formats
- GeoJSON in WGS84 (EPSG:4326)
            
## Visualization Types
1. Geometrical data  
- Display points, lines, or polygons

2. Numeric data 
- Classifies numeric column values
- Selectable classification scheme
- Adjustable number of classes 

3️. Categorical data  
- Shows distinct values from a column 
- Choosable matplotlib colormap

4. Heatmap  
- Visualize point density 

# How to use 
- Install dependencies:
  pip install -r requirements.txt
- Ensure your data is a GeoJSON file with WGS84 coordinates (EPSG:4326)
- Run the app using the following command:
    ```
    streamlit run visualization_app.py
    ```
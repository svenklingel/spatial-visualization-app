This app is developed using the Spiral Model and utilizes Streamlit and GeoPandas to visualize user-provided GeoJSON files using the geopandas.GeoDataFrame.explore method. 

## Features
- Visualize spatial data 
- Export interactive maps as HTML

## Supported Formats
- GeoJSON 
            
## Visualization Types
1. Geometrical data  
- Display points, lines, or polygons

2. Numeric data 
- Classifies numeric column values
- Selectable classification scheme (supported are all schemes provided by mapclassify)
- Adjustable number of classes 

3️. Categorical data  
- Shows distinct values from a column 
- Choosable Matplotlib colormap

4. Heatmap  
- Visualize point density 

# How to use 
- Install dependencies:
    ```
    pip install -r requirements.txt
    ```
- Ensure your data is a GeoJSON file
- Run the app using the following command:
    ```
    streamlit run visualization_app.py
    ```

# Possible features for future iterations
- Support for more file formats
- Export maps as images
- Support for user-defined categories
- Ability to define the minimum and maximum values of the Matplotlib colormap used for numeric visualizations (supported via the `vmin` and `vmax` parameters of `explore()`)
- Support for additional visualization types, including spatio-temporal visualizations
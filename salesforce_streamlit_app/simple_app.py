import streamlit as st
import pandas as pd
import os
import json
import requests
from dotenv import load_dotenv
from simple_salesforce import Salesforce
import logging
from arcgis.gis import GIS
from arcgis.geocoding import geocode
from arcgis.geometry import Point
from arcgis.mapping import WebMap

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("salesforce_arcgis.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Salesforce + ArcGIS Explorer",
    page_icon="🗺️",
    layout="wide"
)

# ArcGIS credentials - Store these in .env file
ARCGIS_USERNAME = os.getenv("ARCGIS_USERNAME", "")
ARCGIS_PASSWORD = os.getenv("ARCGIS_PASSWORD", "")
# For public access without credentials
USE_PUBLIC_ACCESS = True

def create_arcgis_connection():
    """Connect to ArcGIS Online"""
    try:
        if USE_PUBLIC_ACCESS:
            # Connect anonymously to ArcGIS Online
            gis = GIS()
            st.session_state.gis = gis
            logger.info("Connected to ArcGIS Online anonymously")
            return True
        else:
            # Connect with credentials
            gis = GIS("https://www.arcgis.com", ARCGIS_USERNAME, ARCGIS_PASSWORD)
            st.session_state.gis = gis
            logger.info(f"Connected to ArcGIS Online as {ARCGIS_USERNAME}")
            return True
    except Exception as e:
        logger.error(f"ArcGIS connection failed: {str(e)}")
        return False

def geocode_address(address):
    """Geocode an address using ArcGIS geocoding service"""
    try:
        location = geocode(address)[0]
        return {
            'address': location['address'],
            'location': location['location'],
            'score': location['score']
        }
    except Exception as e:
        logger.error(f"Geocoding failed for {address}: {str(e)}")
        return None

def display_arcgis_map(df, location_field='geocoded_location'):
    """Display accounts on an ArcGIS map"""
    try:
        # Create a new map centered on the average of all points
        if df.empty or location_field not in df.columns:
            st.warning("No geocoded data available to display on map")
            return

        # Filter out rows with no location data
        map_df = df.dropna(subset=[location_field])
        
        if map_df.empty:
            st.warning("No valid location data found")
            return

        # Create a feature collection from the dataframe
        features = []
        for _, row in map_df.iterrows():
            if row[location_field] and isinstance(row[location_field], dict):
                point_geom = row[location_field]['location']
                attributes = {k: str(v) for k, v in row.items() if k != location_field}
                attributes['display_name'] = row.get('Name', 'Unknown')
                
                feature = {
                    'geometry': point_geom,
                    'attributes': attributes
                }
                features.append(feature)

        # Create a new WebMap
        wm = WebMap()
        
        # Add the feature collection to the map
        if features:
            # Create a feature collection
            feature_collection = {
                'featureCollection': {
                    'layers': [{
                        'layerDefinition': {
                            'name': 'Accounts',
                            'geometryType': 'esriGeometryPoint'
                        },
                        'featureSet': {
                            'features': features,
                            'geometryType': 'esriGeometryPoint'
                        }
                    }]
                }
            }
            
            # Add the feature collection to the map
            wm.add_layer(feature_collection)
            
            # Get HTML for the map
            map_html = wm._repr_html_()
            
            # Display in Streamlit
            st.components.v1.html(map_html, height=600)
            
            return True
        else:
            st.warning("No features to display on map")
            return False
    except Exception as e:
        logger.error(f"Error displaying map: {str(e)}")
        st.error(f"Error displaying map: {str(e)}")
        return False

# Add this to your existing Streamlit app
def add_arcgis_tab():
    """Add the ArcGIS mapping tab to the app"""
    st.header("🗺️ Account Location Explorer")
    
    # Initialize ArcGIS connection if not already done
    if 'gis' not in st.session_state:
        create_arcgis_connection()
    
    # Fetch Accounts with address information
    if st.button("Fetch Accounts with Location Data"):
        with st.spinner("Fetching account data and geocoding..."):
            try:
                # Query Salesforce for accounts with address information
                query = """
                    SELECT Id, Name, Industry, AnnualRevenue, Phone, Website, 
                           BillingStreet, BillingCity, BillingState, BillingPostalCode, BillingCountry
                    FROM Account 
                    WHERE BillingStreet != NULL OR BillingCity != NULL
                    LIMIT 25
                """
                accounts = run_query(query)
                
                if accounts:
                    # Format the records
                    df = format_records(accounts)
                    
                    # Add a geocoding progress bar
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    # Geocode the addresses
                    df['geocoded_location'] = None
                    df['full_address'] = df.apply(
                        lambda row: ", ".join([
                            str(row.get(f, "")) for f in 
                            ['BillingStreet', 'BillingCity', 'BillingState', 'BillingPostalCode', 'BillingCountry'] 
                            if row.get(f)
                        ]), 
                        axis=1
                    )
                    
                    # Geocode each address
                    for i, (idx, row) in enumerate(df.iterrows()):
                        if row['full_address']:
                            status_text.text(f"Geocoding: {row['Name']}")
                            geo_result = geocode_address(row['full_address'])
                            if geo_result:
                                df.at[idx, 'geocoded_location'] = geo_result
                        
                        # Update progress
                        progress_bar.progress((i + 1) / len(df))
                    
                    status_text.text("Geocoding complete!")
                    progress_bar.progress(100)
                    
                    # Store the geocoded data in session state
                    st.session_state.geocoded_accounts = df
                    
                    # Show data table
                    with st.expander("Account Data"):
                        st.dataframe(df.drop(columns=['geocoded_location']))
                    
                    # Display map
                    st.subheader("Account Locations")
                    display_arcgis_map(df)
                    
                    # Show accounts by region
                    st.subheader("Accounts by Region")
                    
                    # Create a simple choropleth or summary by state/region
                    if 'BillingState' in df.columns:
                        state_counts = df['BillingState'].value_counts()
                        st.bar_chart(state_counts)
                        
                        # Sort by revenue
                        if 'AnnualRevenue' in df.columns:
                            state_revenue = df.groupby('BillingState')['AnnualRevenue'].sum().sort_values(ascending=False)
                            st.subheader("Annual Revenue by State")
                            st.bar_chart(state_revenue)
                    
                    # Option to download the data
                    csv = df.drop(columns=['geocoded_location']).to_csv(index=False)
                    st.download_button("Download Account Location Data", csv, "account_locations.csv", "text/csv")
                else:
                    st.warning("No accounts found with address information.")
            except Exception as e:
                st.error(f"Error loading ArcGIS map: {str(e)}")
                logger.error(f"Error loading ArcGIS map: {str(e)}")

# Add to the main part of your app
def main():
    # Your existing code...
    
    # Main content
    if st.session_state.logged_in:
        # Data Selection Section
        st.header("📊 Data Explorer")
        
        # Add the ArcGIS tab to your existing tabs
        tabs = st.tabs(["View & Edit Data", "Create New Records", "Location Intelligence"])
        
        with tabs[0]:
            # Your existing "View & Edit Data" tab code
            pass
        
        with tabs[1]:
            # Your existing "Create New Records" tab code
            pass
        
        with tabs[2]:
            # This is the new tab for ArcGIS integration
            add_arcgis_tab()
    else:
        st.info("Please log in to Salesforce using the sidebar.")
        
        # Display instructions for first-time users
        with st.expander("How to Get Your Security Token"):
            st.write("""
            1. Log in to Salesforce
            2. Click on your profile picture/name in the top right
            3. Click on 'Settings'
            4. In the left sidebar, click on 'Reset My Security Token'
            5. Click the 'Reset Security Token' button
            6. Check your email for your new security token
            """) 
        
        # Also add instructions for ArcGIS
        with st.expander("Setting Up ArcGIS Integration"):
            st.write("""
            This app uses the ArcGIS Python API to map your Salesforce data. For full functionality:
            
            1. Create a free ArcGIS Developer account at developers.arcgis.com
            2. Add your ArcGIS credentials to your .env file:
               ```
               ARCGIS_USERNAME=your_username
               ARCGIS_PASSWORD=your_password
               ```
            3. Set USE_PUBLIC_ACCESS=False in the code to use your credentials
            
            Note: Basic mapping functionality works without credentials using ArcGIS public access.
            """)

# You would typically add the call to main() at the end of your script
# main()
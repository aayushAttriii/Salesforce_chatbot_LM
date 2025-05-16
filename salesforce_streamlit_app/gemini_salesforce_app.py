import streamlit as st
import requests
import pandas as pd
import altair as alt
import json
import os
from dotenv import load_dotenv
import google.generativeai as genai
import time
from simple_salesforce import Salesforce
import logging
import urllib.parse

# Load environment variables from .env file
load_dotenv('salesforce_arcgis.env')

# Set environment variables directly from .env
os.environ["SF_USERNAME"] = os.getenv("SF_USERNAME")
os.environ["SF_PASSWORD"] = os.getenv("SF_PASSWORD")
os.environ["SF_SECURITY_TOKEN"] = os.getenv("SF_SECURITY_TOKEN")
os.environ["SF_DOMAIN"] = os.getenv("SF_DOMAIN")
os.environ["LOGIN_URL"] = os.getenv("LOGIN_URL")
os.environ["CLIENT_ID"] = os.getenv("CLIENT_ID")
os.environ["CLIENT_SECRET"] = os.getenv("CLIENT_SECRET")
os.environ["REDIRECT_URI"] = os.getenv("REDIRECT_URI")
os.environ["GEMINI_API_KEY"] = os.getenv("GEMINI_API_KEY")

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("salesforce_data.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ENV variables with validation
required_env_vars = {
    "SF_USERNAME": os.getenv("SF_USERNAME"),
    "SF_PASSWORD": os.getenv("SF_PASSWORD"),
    "SF_SECURITY_TOKEN": os.getenv("SF_SECURITY_TOKEN"),
    "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY"),
    "CLIENT_ID": os.getenv("CLIENT_ID"),
    "CLIENT_SECRET": os.getenv("CLIENT_SECRET"),
    "REDIRECT_URI": os.getenv("REDIRECT_URI")
}

# Log all environment variables (safely)
for var_name, var_value in required_env_vars.items():
    if var_value:
        logger.info(f"{var_name} is set")
    else:
        logger.error(f"{var_name} is not set")

# Check for missing environment variables
missing_vars = [var for var, value in required_env_vars.items() if not value]
if missing_vars:
    error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
    logger.error(error_msg)
    st.error(error_msg)
    st.stop()

# Set environment variables
SF_USERNAME = required_env_vars["SF_USERNAME"]
SF_PASSWORD = required_env_vars["SF_PASSWORD"]
SF_SECURITY_TOKEN = required_env_vars["SF_SECURITY_TOKEN"]
SF_DOMAIN = os.getenv("SF_DOMAIN", "login")
LOGIN_URL = os.getenv("LOGIN_URL", "https://login.salesforce.com")
GEMINI_API_KEY = required_env_vars["GEMINI_API_KEY"]
CLIENT_ID = required_env_vars["CLIENT_ID"]
CLIENT_SECRET = required_env_vars["CLIENT_SECRET"]
REDIRECT_URI = required_env_vars["REDIRECT_URI"]

# Print environment variables for debugging (safely)
logger.info("Environment variables loaded successfully")
logger.info(f"SF_USERNAME: {SF_USERNAME}")
logger.info(f"SF_DOMAIN: {SF_DOMAIN}")
logger.info(f"GEMINI_API_KEY: {GEMINI_API_KEY[:10]}...")  # Only print first 10 chars for security

# Auth URLs
TOKEN_URL = f"{LOGIN_URL}/services/oauth2/token"
AUTH_URL = f"{LOGIN_URL}/services/oauth2/authorize"

# Configure Gemini API
try:
    # Try to get package version (without pkg_resources)
    try:
        genai_version = getattr(genai, "__version__", "unknown")
        logger.info(f"Using google-generativeai version: {genai_version}")
    except Exception:
        logger.info("Could not determine google-generativeai version")
    
    # Configure with the API key
    genai.configure(api_key=GEMINI_API_KEY)
    logger.info("Gemini API configured successfully")
    
    # Check if API is accessible and print available models
    try:
        available_models = genai.list_models()
        logger.info(f"Successfully listed {len(available_models)} models")
        model_names = [model.name for model in available_models]
        logger.info(f"Available models: {model_names}")
        
        if not any("gemini" in model.name.lower() for model in available_models):
            logger.warning("No Gemini models found in the available models list")
    except Exception as model_list_error:
        logger.warning(f"Could not list models: {str(model_list_error)}")
        
except Exception as e:
    error_msg = f"Failed to configure Gemini API: {str(e)}"
    logger.error(error_msg)
    st.error(error_msg)
    st.error("Please check your GEMINI_API_KEY in the .env file or create one at https://aistudio.google.com/app/apikey")
    st.stop()

# Print available models at startup
try:
    available_models = genai.list_models()
    print("Available models:")
    for model in available_models:
        print(f"- {model.name}")
except Exception as e:
    print(f"Error listing models: {str(e)}")

# Set page config
st.set_page_config(page_title="Salesforce Gemini Assistant", layout="wide")

# Define the Gemini model - updated to use a supported model
MODEL = "gemini-1.5-pro"  # Changed from gemini-pro to a newer version

def list_available_models():
    """List available Gemini models"""
    try:
        models = genai.list_models()
        model_names = [model.name for model in models]
        logger.info(f"Available models: {model_names}")
        return model_names
    except Exception as e:
        st.error(f"Error listing models: {str(e)}")
        logger.error(f"Error listing models: {str(e)}")
        return []

def setup_gemini_model():
    """Setup and return a Gemini model instance with fallbacks"""
    try:
        # First try listing available models
        available_models = list_available_models()
        logger.info(f"Found {len(available_models)} available models")
        
        for model_name in available_models:
            logger.info(f"Available model: {model_name}")
        
        # Try models in order of preference - using names that are likely to exist in the API
        models_to_try = [
            "gemini-1.5-pro",
            "gemini-1.5-flash",
            "gemini-pro",
            "gemini-1.0-pro",
            "models/gemini-pro",
            "models/gemini-1.5-pro",
            "text-bison"
        ]
        
        # Additional fallback: look for patterns in available models
        for available_model in available_models:
            if "gemini" in available_model.lower() and available_model not in models_to_try:
                models_to_try.insert(0, available_model)  # Add to front of list
                logger.info(f"Added detected Gemini model to try: {available_model}")
        
        # Try each model in sequence
        last_error = None
        for model_name in models_to_try:
            try:
                logger.info(f"Attempting to create model with {model_name}")
                model = genai.GenerativeModel(model_name)
                
                # Test the model with a simple generation
                test_response = model.generate_content("Hello")
                logger.info(f"Successfully created and tested model with {model_name}")
                
                return model
            except Exception as e:
                logger.warning(f"Failed to create/test model {model_name}: {str(e)}")
                last_error = e
                continue
        
        # If we reach here, no models worked
        if last_error:
            logger.error(f"All model attempts failed. Last error: {str(last_error)}")
            raise last_error
        else:
            logger.error("No Gemini models available")
            raise ValueError("No Gemini models available for use")
    except Exception as primary_error:
        logger.error(f"Error setting up Gemini model: {str(primary_error)}")
        raise primary_error

def generate_gemini_response(model, prompt, context=""):
    full_prompt = f"{context}\n\nUser query: {prompt}\n\nPlease analyze this query about Salesforce data and respond with a JSON in this exact format:\n{{\"intent\": \"[one of: top_accounts, recent_opportunities, opportunity_by_stage, contacts, opportunity_stage_chart, opportunity_amount_chart, custom_query, unknown]\", \"query\": \"[the SOQL query to execute or null if unknown]\", \"explanation\": \"[brief explanation of what the query will do]\"}}"
    
    try:
        if model is None:
            return {"intent": "unknown", "query": None, "explanation": "No Gemini model available"}
        
        # Log the prompt for debugging
        logger.info(f"Sending prompt to Gemini: {prompt[:100]}...")
        
        response = model.generate_content(full_prompt)
        return parse_gemini_response(response.text)
    except Exception as e:
        st.error(f"Error with Gemini API: {str(e)}")
        logger.error(f"Error with Gemini API: {str(e)}")
        
        # Fallback to rule-based processing
        return fallback_query_processing(prompt)

def fallback_query_processing(prompt):
    """Process query using rule-based approach when Gemini fails"""
    prompt = prompt.lower()
    logger.info(f"Using fallback processing for query: {prompt}")
    
    # Default to unknown
    result = {"intent": "unknown", "query": None, "explanation": "Using rule-based fallback processing"}
    
    # Simple rule-based detection - expanded for better matching
    account_terms = ["account", "accounts", "customer", "customers", "client", "clients", "top account", "best account", "highest value account"]
    opportunity_terms = ["opportunity", "opportunities", "deal", "deals", "sale", "sales"]
    recent_terms = ["recent", "latest", "new", "newest", "last"]
    stage_terms = ["stage", "status", "phase", "pipeline", "progress"]
    contact_terms = ["contact", "contacts", "people", "person", "employee", "employees"]
    chart_terms = ["chart", "graph", "visual", "visualization", "diagram", "plot"]
    
    # Check for top accounts intent
    if any(term in prompt for term in account_terms) and ("top" in prompt or "best" in prompt or "highest" in prompt or "largest" in prompt):
        result["intent"] = "top_accounts"
        result["query"] = get_default_queries()["top_accounts"]
        result["explanation"] = "Finding the top accounts by opportunity amount"
    
    # Check for recent opportunities intent
    elif any(term in prompt for term in opportunity_terms) and any(term in prompt for term in recent_terms):
        result["intent"] = "recent_opportunities"
        result["query"] = get_default_queries()["recent_opportunities"]
        result["explanation"] = "Listing the most recently created opportunities"
    
    # Check for opportunities by stage intent
    elif any(term in prompt for term in opportunity_terms) and any(term in prompt for term in stage_terms):
        result["intent"] = "opportunity_by_stage"
        result["query"] = get_default_queries()["opportunity_by_stage"]
        result["explanation"] = "Showing opportunities grouped by stage"
    
    # Check for contacts intent
    elif any(term in prompt for term in contact_terms):
        result["intent"] = "contacts"
        result["query"] = get_default_queries()["contacts"]
        result["explanation"] = "Listing contact information"
    
    # Check for chart intents
    elif any(term in prompt for term in chart_terms) or "show me" in prompt:
        if any(term in prompt for term in stage_terms):
            result["intent"] = "opportunity_stage_chart"
            result["query"] = get_default_queries()["opportunity_stage_chart"]
            result["explanation"] = "Creating a chart of opportunities by stage"
        elif any(term in prompt for term in opportunity_terms):
            result["intent"] = "opportunity_amount_chart"
            result["query"] = get_default_queries()["opportunity_amount_chart"]
            result["explanation"] = "Creating a chart of opportunities by amount"
    
    # Check for simple intent patterns
    elif "top" in prompt and any(term in prompt for term in opportunity_terms):
        result["intent"] = "opportunity_amount_chart"
        result["query"] = get_default_queries()["opportunity_amount_chart"]
        result["explanation"] = "Showing top opportunities by amount"
    elif "all" in prompt and any(term in prompt for term in opportunity_terms):
        result["intent"] = "recent_opportunities"
        result["query"] = get_default_queries()["recent_opportunities"]
        result["explanation"] = "Listing opportunities"
    
    # Catch-all for basic terms
    elif any(term in prompt for term in opportunity_terms):
        result["intent"] = "recent_opportunities"
        result["query"] = get_default_queries()["recent_opportunities"]
        result["explanation"] = "Showing recent opportunities"
    elif any(term in prompt for term in account_terms):
        result["intent"] = "top_accounts"
        result["query"] = get_default_queries()["top_accounts"]
        result["explanation"] = "Showing top accounts"
    
    logger.info(f"Fallback processing result: {result['intent']}")
    return result

def parse_gemini_response(response_text):
    try:
        # Find the JSON within the response text
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}') + 1
        
        if start_idx != -1 and end_idx != -1:
            json_str = response_text[start_idx:end_idx]
            response_data = json.loads(json_str)
            
            # Ensure the response has the expected structure
            if "intent" not in response_data or "query" not in response_data:
                default_response = {
                    "intent": "unknown", 
                    "query": None, 
                    "explanation": "I couldn't understand your request."
                }
                return default_response
            
            return response_data
        else:
            return {
                "intent": "unknown", 
                "query": None, 
                "explanation": "I couldn't parse the response properly."
            }
    except Exception as e:
        st.error(f"Error parsing response: {str(e)}")
        return {
            "intent": "unknown", 
            "query": None, 
            "explanation": "I encountered an error processing your request."
        }

def login_salesforce():
    """Connect to Salesforce using SOAP API or OAuth2 as fallback"""
    try:
        # For debugging - print all environment variables
        logger.info("Environment variables for Salesforce login:")
        logger.info(f"SF_USERNAME: {SF_USERNAME}")
        logger.info(f"SF_DOMAIN: {SF_DOMAIN}")
        logger.info(f"LOGIN_URL: {os.getenv('LOGIN_URL')}")
        
        # Use credentials from form if available, otherwise use environment variables
        username = st.session_state.get('username', SF_USERNAME)
        password = st.session_state.get('password', SF_PASSWORD)
        security_token = st.session_state.get('security_token', SF_SECURITY_TOKEN)
        domain = st.session_state.get('domain', SF_DOMAIN)
        
        # For debugging - print session state variables
        logger.info("Session state variables for Salesforce login:")
        logger.info(f"username from session: {st.session_state.get('username')}")
        logger.info(f"domain from session: {st.session_state.get('domain')}")
        
        # Try direct login with simple-salesforce - this is the most reliable method
        try:
            logger.info(f"Attempting direct login with username: {username} and domain: {domain}")
            
            sf = Salesforce(
                username=username,
                password=password,
                security_token=security_token,
                domain=domain
            )
            st.session_state.sf = sf
            logger.info("Successfully connected to Salesforce using username/password")
            return True
        except Exception as inner_e:
            logger.warning(f"First login attempt failed: {str(inner_e)}. Trying alternative methods...")
        
        # Try with SOAP API explicitly (based on successful test)
        try:
            logger.info("Attempting SOAP API login")
            from simple_salesforce.login import SalesforceLogin
            
            session_id, instance = SalesforceLogin(
                username=username,
                password=password,
                security_token=security_token,
                domain=domain
            )
            
            sf = Salesforce(instance=instance, session_id=session_id)
            st.session_state.sf = sf
            logger.info("Successfully connected to Salesforce using SOAP API")
            return True
        except Exception as soap_e:
            logger.warning(f"SOAP API login failed: {str(soap_e)}. Trying OAuth fallback...")
        
        # Only try OAuth2 as a fallback if we have client ID and client secret
        if CLIENT_ID and CLIENT_SECRET:
            # Check if we have an authorization code
            auth_code = st.query_params.get("code", [None])[0]
            
            if auth_code:
                # Exchange authorization code for access token
                token_data = {
                    "grant_type": "authorization_code",
                    "client_id": CLIENT_ID,
                    "client_secret": CLIENT_SECRET,
                    "redirect_uri": REDIRECT_URI,
                    "code": auth_code
                }
                
                response = requests.post(TOKEN_URL, data=token_data)
                if response.status_code == 200:
                    token_info = response.json()
                    sf = Salesforce(
                        instance_url=token_info["instance_url"],
                        session_id=token_info["access_token"]
                    )
                    st.session_state.sf = sf
                    logger.info("Successfully connected to Salesforce using OAuth2")
                    return True
                else:
                    logger.error(f"OAuth2 token exchange failed: {response.text}")
            
            # If no auth code or token exchange failed, redirect to OAuth2 login
            auth_params = {
                "response_type": "code",
                "client_id": CLIENT_ID,
                "redirect_uri": REDIRECT_URI,
                "scope": "api refresh_token"
            }
            auth_url = f"{AUTH_URL}?{urllib.parse.urlencode(auth_params)}"
            st.markdown(f'<a href="{auth_url}" target="_self">Login with Salesforce OAuth2</a>', unsafe_allow_html=True)
            return False
            
    except Exception as e:
        error_message = str(e)
        st.error(f"Login failed: {error_message}")
        logger.error(f"Login failed: {error_message}")
        logger.exception("Detailed exception information:")
        
        # Provide more specific error messages
        if "INVALID_LOGIN" in error_message:
            st.error("Invalid username, password, or security token. Please check your credentials.")
        elif "Failed to establish a new connection" in error_message:
            st.error("Network error. Please check your internet connection.")
        
        return False

def fetch_salesforce_data(query):
    """Run a SOQL query and return the results using simple-salesforce"""
    try:
        if "sf" not in st.session_state:
            st.error("Not connected to Salesforce")
            return None
            
        results = st.session_state.sf.query_all(query)
        logger.info(f"Query executed: {query}")
        logger.info(f"Records returned: {len(results['records'])}")
        return results['records']
    except Exception as e:
        error_msg = f"Query failed: {str(e)}"
        add_message("assistant", error_msg)
        logger.error(error_msg)
        return None

def format_records(records):
    """Format Salesforce records for display in a dataframe"""
    if not records:
        return pd.DataFrame()
    
    # Remove attributes
    formatted_records = []
    for record in records:
        record_copy = {k: v for k, v in record.items() if k != 'attributes'}
        
        # Process nested objects
        for key, value in record_copy.copy().items():
            if isinstance(value, dict) and 'attributes' in value:
                for nested_key, nested_value in value.items():
                    if nested_key != 'attributes':
                        record_copy[f"{key}.{nested_key}"] = nested_value
                del record_copy[key]
        
        formatted_records.append(record_copy)
    
    return pd.DataFrame(formatted_records)

def create_visualization(df, intent):
    """Create visualization based on data and intent"""
    if intent == "opportunity_stage_chart":
        # Create a bar chart for opportunity stages
        chart = alt.Chart(df).mark_bar().encode(
            x=alt.X('StageName:N', sort='-y'),
            y=alt.Y('totalAmount:Q', title='Total Amount ($)'),
            color='StageName:N',
            tooltip=['StageName', 'opportunityCount', 'totalAmount']
        ).properties(
            title='Opportunities by Stage',
            width=600
        )
        return chart
    
    elif intent == "opportunity_amount_chart":
        # Create a horizontal bar chart for opportunity amounts
        chart = alt.Chart(df).mark_bar().encode(
            y=alt.Y('Name:N', sort='-x'),
            x=alt.X('Amount:Q', title='Amount ($)'),
            tooltip=['Name', 'Amount', 'CloseDate']
        ).properties(
            title='Top Opportunities by Amount',
            width=600
        )
        return chart
    
    elif intent == "top_accounts":
        # Create a horizontal bar chart for top accounts
        if 'Account.Name' in df.columns and 'totalAmount' in df.columns:
            chart = alt.Chart(df).mark_bar().encode(
                y=alt.Y('Account.Name:N', sort='-x'),
                x=alt.X('totalAmount:Q', title='Total Amount ($)'),
                tooltip=['Account.Name', 'totalAmount']
            ).properties(
                title='Top Accounts by Total Opportunity Amount',
                width=600
            )
            return chart
    
    return None

def get_default_queries():
    return {
        "top_accounts": """
            SELECT AccountId, Account.Name, SUM(Amount) totalAmount
            FROM Opportunity
            WHERE IsClosed = true
            GROUP BY AccountId, Account.Name
            ORDER BY totalAmount DESC
            LIMIT 5
        """,
        "recent_opportunities": """
            SELECT Id, Name, Amount, StageName, CloseDate, Account.Name
            FROM Opportunity
            ORDER BY CreatedDate DESC
            LIMIT 10
        """,
        "opportunity_by_stage": """
            SELECT StageName, COUNT(Id) opportunityCount, SUM(Amount) totalAmount
            FROM Opportunity
            GROUP BY StageName
            ORDER BY SUM(Amount) DESC
        """,
        "opportunity_stage_chart": """
            SELECT StageName, COUNT(Id) opportunityCount, SUM(Amount) totalAmount
            FROM Opportunity
            GROUP BY StageName
            ORDER BY SUM(Amount) DESC
        """,
        "opportunity_amount_chart": """
            SELECT Name, Amount, CloseDate
            FROM Opportunity
            WHERE Amount != null
            ORDER BY Amount DESC
            LIMIT 10
        """,
        "contacts": """
            SELECT Id, Name, Email, Phone, Account.Name
            FROM Contact
            ORDER BY CreatedDate DESC
            LIMIT 10
        """
    }

def process_chatbot_query(user_query, model):
    if not user_query:
        return
    
    # Determine if we have a Gemini model or need to use fallback
    if model is not None:
        # Get context about Salesforce schema for the model
        salesforce_context = """
        You are an AI assistant specialized in Salesforce data analysis. Your task is to interpret natural language queries and convert them to SOQL (Salesforce Object Query Language) queries.
        
        Common Salesforce objects and their fields:
        - Account: Id, Name, Industry, AnnualRevenue
        - Opportunity: Id, Name, Amount, StageName, CloseDate, AccountId, Account.Name, CreatedDate, IsClosed
        - Contact: Id, Name, Email, Phone, AccountId, Account.Name, CreatedDate
        
        Custom Objects (note the __c suffix):
        - College__c: Id, Name, city__c
        - Student__c: Id, First_Name__c, Last_Name__c
        
        Important rules for custom objects:
        1. Always use the __c suffix for custom object names
        2. Custom fields also use the __c suffix
        3. When querying custom objects, use the exact object name with __c
        
        Common query intents and their SOQL queries:
        - top_accounts: Queries for accounts with highest opportunity amounts
        - recent_opportunities: Lists the most recently created opportunities
        - opportunity_by_stage: Groups opportunities by their stage
        - contacts: Lists contact information
        - opportunity_stage_chart: Similar to opportunity_by_stage but meant for visualization
        - opportunity_amount_chart: Shows opportunities with highest amounts
        - custom_query: Any valid SOQL query provided by the user
        """
        
        # Generate response using Gemini
        response = generate_gemini_response(model, user_query, salesforce_context)
    else:
        # Fallback processing when Gemini is not available
        logger.info("Using fallback query processing (no Gemini model available)")
        
        # Check if the query looks like a SOQL query
        if user_query.strip().upper().startswith("SELECT") and " FROM " in user_query.upper():
            # This is likely a SOQL query
            response = {
                "intent": "custom_query",
                "query": user_query,
                "explanation": "Running your custom SOQL query"
            }
        else:
            # Use rule-based processing
            response = fallback_query_processing(user_query)
            logger.info(f"Fallback processing determined intent: {response['intent']}")
    
    intent = response["intent"]
    query = response["query"]
    explanation = response.get("explanation", "Processing your request...")
    
    if intent == "unknown" or query is None:
        # Use default message for unknown intent
        add_message("assistant", "I couldn't understand your request. Please try one of these queries:\n- Show me top accounts\n- Show recent opportunities\n- Show opportunities by stage\n- List contacts\n- Create a chart of opportunity stages\n- Or write a custom SOQL query")
        return
    
    # If there's no query but we have a recognized intent, use default query
    if query is None and intent in get_default_queries():
        query = get_default_queries()[intent]
    
    # Set title and filename based on intent
    intent_map = {
        "top_accounts": {"title": "Top Accounts by Opportunity Amount", "filename": "top_accounts.csv", "response": "Here are the top accounts by opportunity amount:"},
        "recent_opportunities": {"title": "Recent Opportunities", "filename": "recent_opportunities.csv", "response": "Here are the most recent opportunities:"},
        "opportunity_by_stage": {"title": "Opportunities by Stage", "filename": "opportunities_by_stage.csv", "response": "Here's a breakdown of opportunities by stage:"},
        "opportunity_stage_chart": {"title": "Opportunities by Stage Chart", "filename": "opportunities_by_stage.csv", "response": "Here's a chart showing opportunities by stage:"},
        "opportunity_amount_chart": {"title": "Top Opportunities by Amount", "filename": "top_opportunities.csv", "response": "Here's a chart showing top opportunities by amount:"},
        "contacts": {"title": "Contact Information", "filename": "contacts.csv", "response": "Here are the recent contacts:"},
        "custom_query": {"title": "Custom Query Results", "filename": "query_results.csv", "response": "Here are the results for your custom query:"}
    }
    
    if intent in intent_map:
        title = intent_map[intent]["title"]
        filename = intent_map[intent]["filename"]
        response_text = intent_map[intent]["response"]
    else:
        title = "Query Results"
        filename = "query_results.csv"
        response_text = "Here are the results:"
    
    # Add explanation from Gemini if available
    if explanation and explanation != "Processing your request...":
        response_text = f"{explanation}\n\n{response_text}"
    
    with st.spinner("Fetching data..."):
        results = fetch_salesforce_data(query)
        if results:
            # Add chatbot response message
            add_message("assistant", response_text)
            
            # Create a container for results
            result_container = st.container()
            with result_container:
                df = format_records(results)
                
                # Check if visualization is appropriate for this intent
                chart = create_visualization(df, intent)
                if chart and any(x in intent for x in ["chart", "top_accounts", "opportunity_stage"]):
                    st.altair_chart(chart, use_container_width=True)
                else:
                    st.dataframe(df)
                
                # Add download button
                csv = df.to_csv(index=False)
                st.download_button("Download as CSV", csv, filename, "text/csv")
                
                # Option to view raw JSON
                if st.checkbox("Show Raw JSON"):
                    st.json(results)
        else:
            add_message("assistant", "No results found for your query.")

def add_message(role, content):
    """Add a message to the chat history"""
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    st.session_state.chat_history.append({"role": role, "content": content})

def display_chat_history():
    """Display the chat history"""
    if "chat_history" in st.session_state:
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.write(message["content"])

def main():
    st.title("🔮 Salesforce Gemini Assistant")
    
    # Initialize chat history if not exists
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    # Initialize Gemini model
    gemini_available = False
    if "gemini_model" not in st.session_state:
        try:
            st.session_state.gemini_model = setup_gemini_model()
            gemini_available = True
            st.success("Connected to Gemini AI ✅")
        except Exception as e:
            st.error(f"Failed to initialize Gemini AI: {str(e)}")
            st.info("Switching to simple query mode without AI features.")
            st.session_state.gemini_model = None
            logger.error(f"Gemini initialization failed: {str(e)}")
    else:
        gemini_available = st.session_state.gemini_model is not None
    
    # Check authentication status
    authenticated = "sf" in st.session_state or st.session_state.get("authenticated", False)
    
    if not authenticated:
        # Show a welcome message
        st.markdown("""
        ## Welcome to Salesforce Gemini Assistant
        
        This application combines the power of Google's Gemini AI with your Salesforce data.
        Please authenticate with your Salesforce account to continue.
        """)
        
        # Salesforce login form
        with st.form("login_form"):
            st.session_state.username = st.text_input("Username", SF_USERNAME)
            st.session_state.password = st.text_input("Password", SF_PASSWORD, type="password")
            st.session_state.security_token = st.text_input("Security Token", SF_SECURITY_TOKEN)
            st.session_state.domain = st.selectbox("Domain", ["login", "test"], index=0)
            
            submit = st.form_submit_button("Login")
        
        # Handle login outside the form context
        if submit:
            logger.info("Starting login process")
            with st.spinner("Logging in..."):
                if login_salesforce():
                    logger.info("Login successful, setting authenticated state")
                    st.session_state.authenticated = True  # Store in session state
                    st.success("Login successful!")
                    # Add welcome message to chat history
                    welcome_message = "Hello! I'm your Salesforce assistant. "
                    if gemini_available:
                        welcome_message += "I can help analyze your Salesforce data using natural language."
                    else:
                        welcome_message += "I'm in simple query mode (Gemini AI unavailable). You can use preset queries or SOQL."
                    welcome_message += " What would you like to know?"
                    add_message("assistant", welcome_message)
                    # Force a rerun to update the UI
                    st.rerun()  # Use st.rerun() instead of st.experimental_rerun()
                else:
                    logger.error("Login failed or not authenticated")
                    st.error("Login failed. Please check your credentials and try again.")
        
        # Add a helper section for manual token
        with st.expander("Having trouble logging in? Here's how to get a security token"):
            st.markdown("""
            ### How to get your Salesforce Security Token:
            
            1. Log in to your Salesforce account in your browser
            2. Click on your profile picture in the top-right corner
            3. Click on "Settings"
            4. In the Quick Find box on the left, type "Reset" and click on "Reset My Security Token"
            5. Click the "Reset Security Token" button
            6. Check your email for the new security token
            7. Use this security token along with your password to log in
            """)
            
        # Add a helper section for Gemini API issues
        if not gemini_available:
            with st.expander("How to fix Gemini API issues"):
                st.markdown("""
                ### Fixing Gemini API Key Issues:
                
                1. Visit [Google AI Studio](https://aistudio.google.com/app/apikey) and sign in with your Google account
                2. Create a new API key or view your existing keys
                3. Copy the API key and update the GEMINI_API_KEY value in your salesforce_arcgis.env file
                4. Restart the application
                
                Note: Make sure you're using a supported version of the google-generativeai library (0.3.2 or higher)
                """)
    else:
        # Show connected status
        st.success("Connected to Salesforce ✅")
        if gemini_available:
            st.success("Connected to Gemini AI ✅")
        else:
            st.warning("Gemini AI unavailable - using simple query mode")
        
        # Show examples sidebar
        with st.sidebar:
            st.header("Example Queries")
            
            if gemini_available:
                st.markdown("""
                - Show me the top 5 accounts by opportunity amount
                - What are my recent opportunities?
                - Give me a breakdown of opportunities by stage
                - Show a chart of opportunities by stage value
                - List contacts from our largest accounts
                - How many opportunities are in the 'Closed Won' stage?
                - Which account has the highest revenue?
                - Show me a visualization of my top opportunities
                """)
            else:
                # Show preset query options when Gemini is unavailable
                st.subheader("Preset Queries")
                if st.button("Top Accounts"):
                    preset_query = get_default_queries()["top_accounts"]
                    process_chatbot_query("Show me top accounts", None)
                if st.button("Recent Opportunities"):
                    process_chatbot_query("Show me recent opportunities", None)
                if st.button("Opportunities by Stage"):
                    process_chatbot_query("Show opportunities by stage", None)
                if st.button("Contacts"):
                    process_chatbot_query("List contacts", None)
                
                st.subheader("Custom SOQL Query")
                custom_soql = st.text_area("Enter SOQL Query:")
                if st.button("Run SOQL"):
                    if custom_soql:
                        add_message("user", custom_soql)
                        query_response = {"intent": "custom_query", "query": custom_soql, "explanation": "Running your custom SOQL query"}
                        process_chatbot_query(custom_soql, None)
            
            # Add logout button
            if st.button("Logout"):
                # Clear authentication tokens
                if "sf" in st.session_state:
                    del st.session_state.sf
                st.rerun()
            
            # Add clear chat button
            if st.button("Clear Chat History"):
                st.session_state.chat_history = []
                st.rerun()
        
        # Display chat history
        display_chat_history()
        
        # Chat input
        user_input = st.chat_input("Ask me about your Salesforce data..." if gemini_available else "Enter your query here...")
        
        if user_input:
            # Add user message to chat
            add_message("user", user_input)
            
            # Display the new message
            with st.chat_message("user"):
                st.write(user_input)
            
            # Process the query
            process_chatbot_query(user_input, st.session_state.gemini_model)

if __name__ == "__main__":
    main() 
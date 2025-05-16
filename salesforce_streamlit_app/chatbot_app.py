import streamlit as st
import requests
import pandas as pd
import altair as alt
import re
from urllib.parse import urlencode
import os
from dotenv import load_dotenv

load_dotenv()

# ENV variables
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
LOGIN_URL = os.getenv("LOGIN_URL")

# Auth URL
TOKEN_URL = f"{LOGIN_URL}/services/oauth2/token"

# Set page config
st.set_page_config(page_title="Salesforce AI Assistant", layout="wide")

def authenticate_salesforce():
    with st.spinner("Authenticating with Salesforce..."):
        # Get security token from environment variable
        SECURITY_TOKEN = os.getenv("SECURITY_TOKEN", "")
        # Append security token to password if it exists
        password_with_token = "Sandeep@123@123@123" + SECURITY_TOKEN
        
        # Print debug information (will be visible in terminal)
        print(f"Attempting authentication with:")
        print(f"Username: myselfaayushjain123@gmail.com")
        print(f"Password length: {len(password_with_token)}")
        print(f"Client ID: {CLIENT_ID}")
        print(f"Client Secret: {CLIENT_SECRET[:5]}...")
        
        res = requests.post(TOKEN_URL, data={
            "grant_type": "password",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "username": "myselfaayushjain123@gmail.com",
            "password": password_with_token
        })
        if res.status_code == 200:
            data = res.json()
            st.session_state.access_token = data["access_token"]
            st.session_state.instance_url = data["instance_url"]
            return True
        else:
            st.error(f"Failed to authenticate: {res.text}")
            print(f"Full error response: {res.text}")  # Print full error to terminal
            return False

def fetch_salesforce_data(query, access_token, instance_url):
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    response = requests.get(
        f"{instance_url}/services/data/v60.0/query",
        headers=headers,
        params={"q": query}
    )
    if response.status_code == 200:
        return response.json()["records"]
    else:
        error_msg = f"Error fetching data: {response.text}"
        add_message("assistant", error_msg)
        return None

def detect_intent(query):
    """Detect the intent of the user's query using keyword matching"""
    query = query.lower()
    
    # Account-related queries
    if any(x in query for x in ["top account", "best account", "highest value", "valuable account"]):
        return "top_accounts"
    
    # Opportunity-related queries
    if any(x in query for x in ["recent opportunit", "latest opportunit", "new opportunit", "opportunity list"]):
        return "recent_opportunities"
    
    # Stage-based opportunity queries
    if "opportunit" in query and any(x in query for x in ["stage", "closed", "won", "lost", "pipeline"]):
        return "opportunity_by_stage"
    
    # Contact-related queries
    if any(x in query for x in ["contact", "people", "person", "employee", "staff"]):
        return "contacts"
    
    # Custom SOQL query detection
    if "select" in query and "from" in query:
        return "custom_query"
    
    # Visualization requests
    if any(x in query for x in ["chart", "graph", "plot", "visual", "dashboard"]):
        if "opportunit" in query and "stage" in query:
            return "opportunity_stage_chart"
        elif "amount" in query or "value" in query:
            return "opportunity_amount_chart"
    
    # Fallback for unrecognized queries
    return "unknown"

def generate_query(intent, user_query):
    """Generate SOQL query based on detected intent"""
    if intent == "top_accounts":
        return """
            SELECT AccountId, Account.Name, SUM(Amount) totalAmount
            FROM Opportunity
            WHERE IsClosed = true
            GROUP BY AccountId, Account.Name
            ORDER BY totalAmount DESC
            LIMIT 5
        """
    
    elif intent == "recent_opportunities":
        return """
            SELECT Id, Name, Amount, StageName, CloseDate, Account.Name
            FROM Opportunity
            ORDER BY CreatedDate DESC
            LIMIT 10
        """
    
    elif intent == "opportunity_by_stage":
        return """
            SELECT StageName, COUNT(Id) opportunityCount, SUM(Amount) totalAmount
            FROM Opportunity
            GROUP BY StageName
            ORDER BY SUM(Amount) DESC
        """
    
    elif intent == "opportunity_stage_chart":
        return """
            SELECT StageName, COUNT(Id) opportunityCount, SUM(Amount) totalAmount
            FROM Opportunity
            GROUP BY StageName
            ORDER BY SUM(Amount) DESC
        """
    
    elif intent == "opportunity_amount_chart":
        return """
            SELECT Name, Amount, CloseDate
            FROM Opportunity
            WHERE Amount != null
            ORDER BY Amount DESC
            LIMIT 10
        """
    
    elif intent == "contacts":
        return """
            SELECT Id, Name, Email, Phone, Account.Name
            FROM Contact
            ORDER BY CreatedDate DESC
            LIMIT 10
        """
    
    elif intent == "custom_query":
        # Extract SOQL query from user input
        match = re.search(r'select.+?from.+?(?=where|limit|group by|order by|$)', user_query, re.IGNORECASE)
        if match:
            return user_query
        else:
            return None
    
    return None

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

def process_chatbot_query(user_query):
    if not user_query:
        return
    
    # Detect intent from user query
    intent = detect_intent(user_query)
    
    # Get appropriate SOQL query based on intent
    query = generate_query(intent, user_query)
    
    if intent == "unknown" or query is None:
        add_message("assistant", "I couldn't understand your request. Please try one of these queries:\n- Show me top accounts\n- Show recent opportunities\n- Show opportunities by stage\n- List contacts\n- Create a chart of opportunity stages\n- Or write a custom SOQL query")
        return
    
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
    
    title = intent_map[intent]["title"]
    filename = intent_map[intent]["filename"]
    response_text = intent_map[intent]["response"]
    
    with st.spinner("Fetching data..."):
        results = fetch_salesforce_data(query, st.session_state.access_token, st.session_state.instance_url)
        if results:
            # Add chatbot response message
            add_message("assistant", response_text)
            
            # Create a container for results
            result_container = st.container()
            with result_container:
                df = pd.DataFrame(results)
                
                # Check if visualization is appropriate for this intent
                chart = create_visualization(df, intent)
                if chart and any(x in intent for x in ["chart", "top_accounts", "opportunity_stage"]):
                    st.altair_chart(chart, use_container_width=True)
                else:
                    st.dataframe(df)
                
                # Add download button
                csv = df.to_csv(index=False)
                st.download_button("Download as CSV", csv, filename, "text/csv")
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
    st.title("🔮 Salesforce AI Assistant")
    
    # Initialize chat history if not exists
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    # Auto-login on startup
    if "access_token" not in st.session_state:
        if authenticate_salesforce():
            st.success("Authenticated with Salesforce ✅")
            # Add welcome message
            add_message("assistant", "Hello! I'm your Salesforce data assistant. What information would you like to see today?")
            st.experimental_rerun()
    else:
        # Chat interface
        st.write("Connected to Salesforce ✅")
        
        # Show examples sidebar
        with st.sidebar:
            st.header("Example Queries")
            st.markdown("""
            - Show me the top accounts by opportunity amount
            - Get recent opportunities
            - Show opportunities by stage
            - Show me a chart of opportunities by stage
            - List contacts
            - SELECT Id, Name FROM Account LIMIT 5
            """)
            
            # Add clear chat button
            if st.button("Clear Chat History"):
                st.session_state.chat_history = []
                st.experimental_rerun()
        
        # Display chat history
        display_chat_history()
        
        # Chat input
        user_input = st.chat_input("Ask me about your Salesforce data...")
        
        if user_input:
            # Add user message to chat
            add_message("user", user_input)
            
            # Display the new message
            with st.chat_message("user"):
                st.write(user_input)
            
            # Process the query
            process_chatbot_query(user_input)

if __name__ == "__main__":
    main() 
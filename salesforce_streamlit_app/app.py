import streamlit as st
import requests
import pandas as pd
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
        st.error(f"Error fetching data: {response.text}")
        return None

st.title("🔗 Salesforce Data Explorer")

# Authentication Section
if "access_token" not in st.session_state:
    if authenticate_salesforce():
        st.success("Authenticated with Salesforce ✅")
        st.experimental_rerun()
else:
    st.success("Authenticated with Salesforce ✅")
    
    # Data Selection Section
    st.header("📊 Data Explorer")
    data_option = st.selectbox(
        "Select Data to View",
        [
            "Top Accounts by Opportunity Amount",
            "Recent Opportunities",
            "Contacts by Account",
            "Custom Query"
        ]
    )

    if data_option == "Top Accounts by Opportunity Amount":
        if st.button("Fetch Top 5 Accounts"):
            with st.spinner("Fetching data..."):
                query = """
                    SELECT AccountId, SUM(Amount) totalAmount
                    FROM Opportunity
                    WHERE IsClosed = true
                    GROUP BY AccountId
                    ORDER BY totalAmount DESC
                    LIMIT 5
                """
                top_accounts = fetch_salesforce_data(query, st.session_state.access_token, st.session_state.instance_url)
                
                if top_accounts:
                    account_ids = [acc["AccountId"] for acc in top_accounts]
                    ids_str = ",".join([f"'{id}'" for id in account_ids])
                    account_query = f"SELECT Id, Name, Industry, AnnualRevenue FROM Account WHERE Id IN ({ids_str})"
                    
                    account_data = fetch_salesforce_data(account_query, st.session_state.access_token, st.session_state.instance_url)
                    if account_data:
                        df = pd.DataFrame(account_data)
                        st.dataframe(df)
                        csv = df.to_csv(index=False)
                        st.download_button("Download as CSV", csv, "top_accounts.csv", "text/csv")

    elif data_option == "Recent Opportunities":
        if st.button("Fetch Recent Opportunities"):
            with st.spinner("Fetching data..."):
                query = """
                    SELECT Id, Name, Amount, StageName, CloseDate, Account.Name
                    FROM Opportunity
                    ORDER BY CreatedDate DESC
                    LIMIT 10
                """
                opportunities = fetch_salesforce_data(query, st.session_state.access_token, st.session_state.instance_url)
                if opportunities:
                    df = pd.DataFrame(opportunities)
                    st.dataframe(df)
                    csv = df.to_csv(index=False)
                    st.download_button("Download as CSV", csv, "recent_opportunities.csv", "text/csv")

    elif data_option == "Contacts by Account":
        if st.button("Fetch Contacts"):
            with st.spinner("Fetching data..."):
                query = """
                    SELECT Id, Name, Email, Phone, Account.Name
                    FROM Contact
                    ORDER BY CreatedDate DESC
                    LIMIT 10
                """
                contacts = fetch_salesforce_data(query, st.session_state.access_token, st.session_state.instance_url)
                if contacts:
                    df = pd.DataFrame(contacts)
                    st.dataframe(df)
                    csv = df.to_csv(index=False)
                    st.download_button("Download as CSV", csv, "contacts.csv", "text/csv")

    elif data_option == "Custom Query":
        custom_query = st.text_area("Enter your SOQL query:")
        if st.button("Execute Query"):
            with st.spinner("Executing query..."):
                results = fetch_salesforce_data(custom_query, st.session_state.access_token, st.session_state.instance_url)
                if results:
                    df = pd.DataFrame(results)
                    st.dataframe(df)
                    csv = df.to_csv(index=False)
                    st.download_button("Download as CSV", csv, "query_results.csv", "text/csv")

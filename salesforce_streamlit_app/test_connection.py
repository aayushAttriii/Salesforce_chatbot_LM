import requests
import os
from dotenv import load_dotenv
import webbrowser
from urllib.parse import urlencode

def test_salesforce_connection():
    # Load environment variables
    load_dotenv()
    
    # Get credentials from .env
    CLIENT_ID = os.getenv("CLIENT_ID")
    CLIENT_SECRET = os.getenv("CLIENT_SECRET")
    LOGIN_URL = os.getenv("LOGIN_URL")
    REDIRECT_URI = os.getenv("REDIRECT_URI")
    
    # Authentication URLs
    AUTH_URL = f"{LOGIN_URL}/services/oauth2/authorize"
    TOKEN_URL = f"{LOGIN_URL}/services/oauth2/token"
    
    # Print debug info
    print("Setting up Salesforce connection...")
    print(f"Login URL: {LOGIN_URL}")
    print(f"Client ID: {CLIENT_ID}")
    print(f"Client Secret: {CLIENT_SECRET[:5]}...")
    
    # Step 1: Get authorization code
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": "full refresh_token offline_access"
    }
    
    auth_url = f"{AUTH_URL}?{urlencode(params)}"
    print("\nPlease open this URL in your browser and authorize the app:")
    print(auth_url)
    
    # Open the URL in browser
    webbrowser.open(auth_url)
    
    # Step 2: Get the authorization code from the redirect URL
    print("\nAfter authorizing, please enter the code from the URL:")
    auth_code = input("Enter the authorization code: ")
    
    # Step 3: Exchange code for access token
    try:
        response = requests.post(TOKEN_URL, data={
            "grant_type": "authorization_code",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "redirect_uri": REDIRECT_URI,
            "code": auth_code
        })
        
        print("\nResponse Status Code:", response.status_code)
        print("Response Content:", response.text)
        
        if response.status_code == 200:
            print("\nSuccess! Connected to Salesforce")
            data = response.json()
            print(f"Instance URL: {data.get('instance_url')}")
            print(f"Access Token received: {data.get('access_token')[:10]}...")
            return True
        else:
            print("\nFailed to connect to Salesforce")
            return False
            
    except Exception as e:
        print(f"\nError occurred: {str(e)}")
        return False

if __name__ == "__main__":
    test_salesforce_connection()
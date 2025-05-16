import requests
import os
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv('salesforce_arcgis.env')

# Get credentials from environment variables
SF_USERNAME = os.getenv("SF_USERNAME")
SF_PASSWORD = os.getenv("SF_PASSWORD")
SF_SECURITY_TOKEN = os.getenv("SF_SECURITY_TOKEN")
SF_DOMAIN = os.getenv("SF_DOMAIN", "login.salesforce.com")
LOGIN_URL = os.getenv("LOGIN_URL", "https://login.salesforce.com")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

print("=== Salesforce Connection Test ===")
print(f"Username: {SF_USERNAME}")
print(f"Password: {'*' * len(SF_PASSWORD)}")
print(f"Security Token: {SF_SECURITY_TOKEN[:4]}..." if SF_SECURITY_TOKEN else "Security Token: Not set")
print(f"Domain: {SF_DOMAIN}")
print(f"Login URL: {LOGIN_URL}")
print(f"Client ID: {CLIENT_ID[:10]}..." if CLIENT_ID else "Client ID: Not set")
print(f"Client Secret: {CLIENT_SECRET[:5]}..." if CLIENT_SECRET else "Client Secret: Not set")

print("\n=== Testing Salesforce API Connectivity ===")

# Test 1: Check if Salesforce domains are reachable
print("\nTest 1: Checking if Salesforce domains are reachable...")
domains_to_check = [
    "login.salesforce.com",
    "test.salesforce.com",
    SF_DOMAIN
]

for domain in domains_to_check:
    try:
        url = f"https://{domain}"
        print(f"Testing connection to {url}...")
        response = requests.get(url, timeout=10)
        print(f"  Status: {response.status_code}")
        print(f"  Response size: {len(response.content)} bytes")
        print(f"  Reachable: Yes")
    except requests.exceptions.RequestException as e:
        print(f"  Error: {str(e)}")
        print(f"  Reachable: No")

# Test 2: Try SOAP API login
print("\nTest 2: Testing SOAP API login...")
soap_url = f"https://{SF_DOMAIN}/services/Soap/u/59.0"
soap_headers = {
    "Content-Type": "text/xml",
    "SOAPAction": "login"
}
soap_body = f"""<?xml version="1.0" encoding="utf-8" ?>
<env:Envelope xmlns:xsd="http://www.w3.org/2001/XMLSchema"
    xmlns:env="http://schemas.xmlsoap.org/soap/envelope/"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
    <env:Body>
        <n1:login xmlns:n1="urn:partner.soap.sforce.com">
            <n1:username>{SF_USERNAME}</n1:username>
            <n1:password>{SF_PASSWORD}{SF_SECURITY_TOKEN}</n1:password>
        </n1:login>
    </env:Body>
</env:Envelope>"""

try:
    response = requests.post(soap_url, headers=soap_headers, data=soap_body, timeout=30)
    print(f"  Status Code: {response.status_code}")
    print(f"  Response: {response.text[:500]}...")
except requests.exceptions.RequestException as e:
    print(f"  Error: {str(e)}")

# Test 3: Try OAuth Username-Password Flow
print("\nTest 3: Testing OAuth Username-Password Flow...")
oauth_url = f"{LOGIN_URL}/services/oauth2/token"
oauth_data = {
    "grant_type": "password",
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "username": SF_USERNAME,
    "password": f"{SF_PASSWORD}{SF_SECURITY_TOKEN}"
}

try:
    response = requests.post(oauth_url, data=oauth_data, timeout=30)
    print(f"  Status Code: {response.status_code}")
    print(f"  Response: {response.text[:500]}...")
except requests.exceptions.RequestException as e:
    print(f"  Error: {str(e)}")

# Test 4: Try OAuth Web Server Flow (authorization URL)
print("\nTest 4: Testing OAuth Web Server Authorization URL...")
auth_url = f"{LOGIN_URL}/services/oauth2/authorize"
auth_params = {
    "response_type": "code",
    "client_id": CLIENT_ID,
    "redirect_uri": "http://localhost:8501",
    "scope": "api refresh_token"
}

auth_url_with_params = auth_url + "?" + "&".join([f"{k}={v}" for k, v in auth_params.items()])
print(f"  Authorization URL: {auth_url_with_params}")

try:
    response = requests.get(auth_url_with_params, timeout=10, allow_redirects=False)
    print(f"  Status Code: {response.status_code}")
    print(f"  Redirect: {'Yes' if response.status_code in [301, 302, 307, 308] else 'No'}")
    if 'Location' in response.headers:
        print(f"  Redirect URL: {response.headers['Location']}")
except requests.exceptions.RequestException as e:
    print(f"  Error: {str(e)}")

print("\n=== Connection Test Complete ===")
print("If all tests failed, there might be network connectivity issues or incorrect credentials.")
print("If some tests passed but others failed, check the specific error messages.") 
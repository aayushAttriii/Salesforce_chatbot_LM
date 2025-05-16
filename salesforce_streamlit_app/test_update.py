from simple_salesforce import Salesforce
import logging
import os
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("test_update.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def main():
    # Connect to Salesforce
    username = os.getenv("SF_USERNAME", "myselfaayushjain123@gmail.com")
    password = os.getenv("SF_PASSWORD", "Sandeep@123@123@123")
    security_token = os.getenv("SF_SECURITY_TOKEN", "67soi3CDpjYRNoeTzAN8IOwq")
    domain = os.getenv("SF_DOMAIN", "login")
    
    logger.info(f"Connecting to Salesforce with username: {username}")
    
    try:
        sf = Salesforce(
            username=username,
            password=password, 
            security_token=security_token,
            domain=domain
        )
        logger.info("Connected to Salesforce")
        
        # Query for an Account to update
        query = "SELECT Id, Name, Industry, Phone FROM Account LIMIT 1"
        logger.info(f"Running query: {query}")
        
        result = sf.query(query)
        if result['totalSize'] == 0:
            logger.error("No accounts found")
            return
        
        account = result['records'][0]
        account_id = account['Id']
        
        logger.info(f"Found Account: {account}")
        
        # Create the data for update
        update_data = {
            'Phone': '555-123-4567',  # A sample phone number to update
            'Industry': 'Technology'   # A sample industry to update
        }
        
        logger.info(f"Updating Account {account_id} with data: {update_data}")
        
        # Get the Account object and update the record
        try:
            # Method 1: Using object attribute
            result = sf.Account.update(account_id, update_data)
            logger.info(f"Update result (method 1): {result}")
            
            # Method 2: Using generic update
            # result = sf.update('Account', account_id, update_data)
            # logger.info(f"Update result (method 2): {result}")
            
            logger.info("Update appears to be successful!")
        except Exception as e:
            logger.error(f"Error updating record: {str(e)}")
            
    except Exception as e:
        logger.error(f"Error connecting to Salesforce: {str(e)}")

if __name__ == "__main__":
    main() 
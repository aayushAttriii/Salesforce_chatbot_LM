# Salesforce AI Assistant

This application provides a chatbot interface to interact with your Salesforce data using natural language queries. It features auto-login to Salesforce, data visualization, and the ability to export data as CSV files.

## Features

- **Auto-login**: Automatically authenticates with Salesforce on startup
- **Natural Language Interface**: Ask questions about your Salesforce data in plain English
- **Data Visualization**: Automatically generates charts for relevant data
- **CSV Export**: Download query results as CSV files
- **Conversational UI**: Chat-like interface for easy interaction

## Available Query Types

The chatbot can understand various types of queries:

1. **Account Queries**:
   - "Show me the top accounts by opportunity amount"
   - "Which accounts are most valuable?"

2. **Opportunity Queries**:
   - "Show me recent opportunities"
   - "Get latest opportunities"
   - "Show opportunities by stage"

3. **Contact Queries**:
   - "List contacts"
   - "Show me contact information"

4. **Visualization Requests**:
   - "Create a chart of opportunities by stage"
   - "Show me a graph of top opportunity amounts"

5. **Custom SOQL Queries**:
   - "SELECT Id, Name FROM Account LIMIT 5"
   - Any valid SOQL query

## Setup Instructions

1. Ensure you have the required environment variables in your `.env` file:
   ```
   CLIENT_ID=your_salesforce_client_id
   CLIENT_SECRET=your_salesforce_client_secret
   LOGIN_URL=your_salesforce_login_url
   SECURITY_TOKEN=your_salesforce_security_token
   ```

2. Install the required dependencies:
   ```
   pip install streamlit pandas requests python-dotenv altair
   ```

3. Run the application:
   ```
   streamlit run chatbot_app.py
   ```

## Usage

1. When you start the application, it will automatically authenticate with Salesforce
2. Type your question in the chat input at the bottom of the screen
3. The chatbot will interpret your question, fetch the relevant data, and display it
4. For appropriate data types, visualizations will be automatically generated
5. You can download any result set as a CSV file using the "Download as CSV" button
6. Clear the chat history using the "Clear Chat History" button in the sidebar

## Comparison with Standard Application

This chatbot version differs from the standard Salesforce Data Explorer in several ways:

1. **Auto-login** instead of requiring manual authentication
2. **Natural language queries** instead of predefined menu options
3. **Conversation history** is maintained in a chat interface
4. **Automatic visualization** of appropriate datasets
5. **More intuitive UI** for casual users who may not know SOQL

## Extending the Application

To add more query types:

1. Add new intent detection patterns in the `detect_intent()` function
2. Add corresponding SOQL queries in the `generate_query()` function
3. Create any additional visualizations in the `create_visualization()` function
4. Update the `intent_map` in `process_chatbot_query()` with appropriate titles and filenames 
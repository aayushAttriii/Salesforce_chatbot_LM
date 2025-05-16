# Salesforce Gemini Assistant

This application provides an AI-powered chatbot interface to interact with your Salesforce data using natural language. It uses Google's Gemini AI to understand your queries and translate them into SOQL (Salesforce Object Query Language).

## Features

- **AI-Powered Understanding**: Uses Google Gemini to interpret natural language queries
- **Auto-login**: Automatically authenticates with Salesforce on startup
- **Natural Language Interface**: Ask questions in plain English about your Salesforce data
- **Data Visualization**: Automatically generates charts for relevant data
- **CSV Export**: Download query results as CSV files
- **Conversational UI**: Chat-like interface for easy interaction

## Setup Instructions

1. Ensure you have the required environment variables in your `.env` file:
   ```
   CLIENT_ID=your_salesforce_client_id
   CLIENT_SECRET=your_salesforce_client_secret
   LOGIN_URL=your_salesforce_login_url
   SECURITY_TOKEN=your_salesforce_security_token
   GEMINI_API_KEY=your_gemini_api_key
   ```

2. Install the required dependencies:
   ```
   pip install streamlit pandas requests python-dotenv altair google-generativeai
   ```

3. Run the application:
   ```
   streamlit run gemini_salesforce_app.py
   ```
   
   Or use the provided scripts:
   - Windows: Double-click `run_gemini_app.bat`
   - Mac/Linux: Run `./run_gemini_app.sh` (you may need to make it executable with `chmod +x run_gemini_app.sh`)

## How It Works

1. The app authenticates with Salesforce using the provided credentials
2. Google's Gemini AI interprets your natural language query
3. The AI determines the intent and generates an appropriate SOQL query
4. The query is executed against the Salesforce API
5. Results are displayed with appropriate visualizations
6. You can download the results as a CSV file

## Example Queries

You can ask questions in natural language such as:

- "Show me the top 5 accounts by opportunity amount"
- "What were my most recent opportunities?"
- "Give me a breakdown of opportunities by stage"
- "Create a chart showing opportunities by stage"
- "List contacts from our largest accounts"
- "How many opportunities are in the 'Closed Won' stage?"
- "Which account has generated the most revenue?"
- "Show me a visualization of my top opportunities"

## Troubleshooting

- **Gemini API Issues**: Ensure your API key is correct and has sufficient quota
- **Salesforce Authentication**: Check your Salesforce credentials and ensure API access is enabled
- **Query Errors**: If you get errors with specific queries, try rephrasing or use more specific language
- **Visualization Issues**: Some data may not be suitable for visualization - try requesting specific chart types

## Advantages Over Rule-Based Approaches

This Gemini-powered assistant has several advantages over rule-based approaches:

1. **Better Query Understanding**: Can understand a wider variety of natural language queries
2. **More Flexible**: Can generate custom SOQL for unique requirements
3. **Contextual Understanding**: Understands the intent behind your questions
4. **Explanations**: Provides explanations of what the query is doing
5. **Adaptability**: Can handle queries about different objects and relationships without hardcoding 
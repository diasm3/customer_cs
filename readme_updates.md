# Testing with Playwright

This project includes end-to-end testing using Playwright, a browser automation library.

## Setup

To set up Playwright for testing this application:

1. Install Playwright and its dependencies:

```bash
pip install playwright
playwright install
```

2. Make sure your application is running:

```bash
# In one terminal, start the LangGraph server
langgraph serve persona_agent:graph --port 2024

# In another terminal, start the Streamlit app
streamlit run app.py
```

3. Run the Playwright tests:

```bash
python test_app_with_playwright.py
```

## Test Features

The Playwright test script performs an end-to-end test of the application:

1. Navigates to the login page
2. Enters a test username
3. Selects a company (SK텔레콤)
4. Selects a scenario (유심 보호 서비스 문의)
5. Sends a test message and waits for a response
6. Tests the conversation ending functionality

## Modifying Tests

You can modify the test script to test different flows or specific features:

- Change the test user name
- Select different companies or scenarios
- Modify the test message content
- Add assertions for expected responses
- Test error conditions

## Headless Mode

For CI environments, you can run tests in headless mode by changing:

```python
browser = await p.chromium.launch(headless=False)
```

to:

```python
browser = await p.chromium.launch(headless=True)
```

## Additional Test Scenarios

You can create additional test files for different scenarios, such as:

- Testing error handling when LangGraph server is unavailable
- Testing different company personas and scenarios
- Performance testing with multiple conversations
- Testing responsive design on different viewport sizes
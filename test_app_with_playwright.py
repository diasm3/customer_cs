import asyncio
from playwright.async_api import async_playwright
import time
import re

async def test_app():
    async with async_playwright() as p:
        # Launch the browser
        browser = await p.chromium.launch(headless=False)  # Set headless=True for production
        context = await browser.new_context()
        page = await context.new_page()
        
        # Navigate to the Streamlit app
        await page.goto("http://localhost:8501")  # Default Streamlit port
        print("Navigated to Streamlit app")
        
        # Wait for the app to load
        await page.wait_for_selector("input[placeholder='닉네임을 입력하세요']", timeout=10000)
        print("App loaded successfully")
        
        # Test login flow
        await page.fill("input[placeholder='닉네임을 입력하세요']", "TestUser")
        await page.click("text=시작하기")
        
        # Wait for company selection page
        await page.wait_for_selector("text=어떤 기업과 대화하시겠어요?", timeout=10000)
        print("Successfully navigated to company selection page")
        
        # Select the first company (SK텔레콤)
        company_buttons = await page.query_selector_all("button:has-text('선택')")
        await company_buttons[0].click()
        
        # Wait for scenario selection page
        await page.wait_for_selector("text=상황 선택", timeout=10000)
        print("Successfully navigated to scenario selection page")
        
        # Select the first scenario
        scenario_buttons = await page.query_selector_all("button:has-text('이 상황으로 시작')")
        await scenario_buttons[0].click()
        
        # Wait for chat page
        await page.wait_for_selector(".chat-container", timeout=10000)
        print("Successfully navigated to chat page")
        
        # Get initial bot message
        messages = await page.query_selector_all(".bot-message")
        if messages:
            initial_message = await messages[0].inner_text()
            print(f"Initial bot message: {initial_message}")
        
        # Wait a bit to ensure the form is fully loaded
        await asyncio.sleep(3)
        
        # Debug info
        print("Looking for message input field...")
        input_fields = await page.query_selector_all("input")
        for i, field in enumerate(input_fields):
            placeholder = await field.get_attribute("placeholder")
            print(f"Input field {i}: placeholder='{placeholder}'")
        
        # Try to find the input field and submit button more precisely
        await page.wait_for_selector("form[key='message_form']", timeout=10000)
        message_form = await page.query_selector("form[key='message_form']")
        
        if message_form:
            input_field = await message_form.query_selector("input")
            if input_field:
                await input_field.fill("유심 해킹에 대해 걱정이 됩니다. 어떻게 보호할 수 있나요?")
                submit_button = await message_form.query_selector("button[type='submit']")
                if submit_button:
                    await submit_button.click()
                else:
                    print("Could not find submit button in form")
            else:
                print("Could not find input field in form")
        else:
            print("Could not find message form")
        
        # Wait for response (this may take some time depending on your LLM)
        print("Waiting for response...")
        # Wait for a new message to appear (by counting the messages)
        initial_message_count = len(await page.query_selector_all(".bot-message"))
        
        # Wait for up to 20 seconds for a new message
        max_wait_time = 20
        start_time = time.time()
        while time.time() - start_time < max_wait_time:
            current_message_count = len(await page.query_selector_all(".bot-message"))
            if current_message_count > initial_message_count:
                break
            await asyncio.sleep(1)
        
        # Check if we got a response
        messages = await page.query_selector_all(".bot-message")
        if len(messages) > initial_message_count:
            response = await messages[-1].inner_text()
            print(f"Bot response: {response[:100]}...")  # Print first 100 chars
            print("Successfully received response from the bot")
        else:
            print("Did not receive a response within the timeout period")
        
        # Test "대화 종료" functionality - use the same method as before to find and fill the form
        if message_form:
            input_field = await message_form.query_selector("input")
            if input_field:
                await input_field.fill("감사합니다")
                submit_button = await message_form.query_selector("button[type='submit']")
                if submit_button:
                    await submit_button.click()
                else:
                    print("Could not find submit button for second message")
            else:
                print("Could not find input field for second message")
        else:
            # Try to find the form again
            message_form = await page.query_selector("form[key='message_form']")
            if message_form:
                input_field = await message_form.query_selector("input")
                if input_field:
                    await input_field.fill("감사합니다")
                    submit_button = await message_form.query_selector("button[type='submit']")
                    if submit_button:
                        await submit_button.click()
                    else:
                        print("Could not find submit button for second message (retry)")
                else:
                    print("Could not find input field for second message (retry)")
            else:
                print("Could not find message form for second message")
        
        # Wait for response
        await asyncio.sleep(5)
        
        # End conversation
        end_convo_button = await page.query_selector("button:has-text('대화 종료')")
        if end_convo_button:
            await end_convo_button.click()
            await page.wait_for_selector("text=상담 요약", timeout=10000)
            print("Successfully ended conversation and displayed summary")
        
        # Close the browser
        await browser.close()
        print("Test completed successfully")

if __name__ == "__main__":
    asyncio.run(test_app())
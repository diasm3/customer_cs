import asyncio
from playwright.async_api import async_playwright

async def test_app():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Step 1: Navigate to the Streamlit app
        print("Navigating to Streamlit app...")
        await page.goto("http://localhost:8501")
        
        # Allow time for Streamlit to fully load
        await asyncio.sleep(5)
        print("App loaded")
        
        # Step 2: Take screenshot of the login page
        await page.screenshot(path="1_login_page.png")
        print("Login page screenshot saved")
        
        # Step 3: Fill nickname and click start
        print("Entering nickname...")
        try:
            await page.fill("input[placeholder='닉네임을 입력하세요']", "TestUser")
            await page.click("text=시작하기")
            print("Login completed")
            await asyncio.sleep(3)
            await page.screenshot(path="2_company_select.png")
        except Exception as e:
            print(f"Error during login: {e}")
            await page.screenshot(path="error_login.png")
        
        # Step 4: Select company (first company)
        print("Selecting company...")
        try:
            select_buttons = await page.query_selector_all("button")
            for button in select_buttons:
                text = await button.text_content()
                if "선택" in text:
                    await button.click()
                    print("Company selected")
                    break
            await asyncio.sleep(3)
            await page.screenshot(path="3_scenario_select.png")
        except Exception as e:
            print(f"Error selecting company: {e}")
            await page.screenshot(path="error_company_select.png")
        
        # Step 5: Select scenario (first scenario)
        print("Selecting scenario...")
        try:
            scenario_buttons = await page.query_selector_all("button")
            for button in scenario_buttons:
                text = await button.text_content()
                if "이 상황으로 시작" in text:
                    await button.click()
                    print("Scenario selected")
                    break
            await asyncio.sleep(3)
            await page.screenshot(path="4_chat_page.png")
        except Exception as e:
            print(f"Error selecting scenario: {e}")
            await page.screenshot(path="error_scenario_select.png")
        
        # Step 6: Get all form elements on the page for debugging
        print("Examining form elements...")
        forms = await page.query_selector_all("form")
        print(f"Found {len(forms)} forms on the page")
        
        for i, form in enumerate(forms):
            inputs = await form.query_selector_all("input")
            buttons = await form.query_selector_all("button")
            print(f"Form {i}: {len(inputs)} inputs, {len(buttons)} buttons")
            
            for j, input_elem in enumerate(inputs):
                placeholder = await input_elem.get_attribute("placeholder")
                print(f"  Input {j}: placeholder='{placeholder}'")
            
            for j, button in enumerate(buttons):
                text = await button.text_content()
                print(f"  Button {j}: text='{text}'")
        
        # Wait before closing
        await asyncio.sleep(5)
        await browser.close()
        print("Test completed")

if __name__ == "__main__":
    asyncio.run(test_app())
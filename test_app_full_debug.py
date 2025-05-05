import asyncio
from playwright.async_api import async_playwright
import time

async def debug_element(page, element, name="Element"):
    """Helper to debug elements"""
    if element:
        tag = await element.evaluate("el => el.tagName")
        attrs = await element.evaluate("el => Object.entries(el.attributes).map(([_, attr]) => `${attr.name}='${attr.value}'`).join(' ')")
        text = await element.text_content()
        is_visible = await element.is_visible()
        box = await element.bounding_box()
        
        print(f"{name}: <{tag} {attrs}> text='{text[:50]}{'...' if len(text) > 50 else ''}' visible={is_visible} box={box}")
        return True
    else:
        print(f"{name}: Not found")
        return False

async def test_app():
    async with async_playwright() as p:
        # Launch browser in non-headless mode so we can see what's happening
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        
        # Create a new page and navigate to the app
        page = await context.new_page()
        await page.goto("http://localhost:8501")
        print("Navigated to app")
        
        # Wait for page to fully load
        await page.wait_for_load_state("networkidle")
        print("Page fully loaded")
        
        # Step 1: Screenshot initial state
        await page.screenshot(path="debug_1_initial.png")
        
        # Step 2: Input nickname
        input_field = await page.query_selector("input[placeholder='닉네임을 입력하세요']")
        if await debug_element(page, input_field, "Nickname input"):
            await input_field.fill("TestUser")
            print("Filled nickname")
        
        # Step 3: Click start button
        start_button = await page.query_selector("button:has-text('시작하기')")
        if await debug_element(page, start_button, "Start button"):
            await start_button.click()
            print("Clicked start button")
        
        # Wait for navigation
        await asyncio.sleep(3)
        await page.screenshot(path="debug_2_company_select.png")
        
        # Step 4: Find and click company selection button
        company_buttons = await page.query_selector_all("button:has-text('선택')")
        print(f"Found {len(company_buttons)} company buttons")
        
        if len(company_buttons) > 0:
            await debug_element(page, company_buttons[0], "First company button")
            await company_buttons[0].click()
            print("Clicked first company")
        
        # Wait for navigation
        await asyncio.sleep(3)
        await page.screenshot(path="debug_3_scenario_select.png")
        
        # Step 5: Find and click scenario button
        scenario_buttons = await page.query_selector_all("button:has-text('이 상황으로 시작')")
        print(f"Found {len(scenario_buttons)} scenario buttons")
        
        if len(scenario_buttons) > 0:
            await debug_element(page, scenario_buttons[0], "First scenario button")
            await scenario_buttons[0].click()
            print("Clicked first scenario")
        
        # Wait for navigation
        await asyncio.sleep(3)
        await page.screenshot(path="debug_4_chat_page.png")
        
        # Step 6: Debug all forms and interactive elements on the chat page
        print("\n--- Forms on chat page ---")
        forms = await page.query_selector_all("form")
        print(f"Found {len(forms)} forms")
        
        for i, form in enumerate(forms):
            print(f"\nForm {i+1}:")
            form_key = await form.get_attribute("key")
            print(f"Form key: {form_key}")
            
            # Get all inputs in the form
            inputs = await form.query_selector_all("input")
            print(f"Inputs in form: {len(inputs)}")
            for j, input_elem in enumerate(inputs):
                await debug_element(page, input_elem, f"Input {j+1}")
            
            # Get all buttons in the form
            buttons = await form.query_selector_all("button")
            print(f"Buttons in form: {len(buttons)}")
            for j, button in enumerate(buttons):
                await debug_element(page, button, f"Button {j+1}")
        
        # Step 7: Try to fill in message form
        # Streamlit sometimes uses iframes or shadow DOM for its components
        print("\n--- Attempting to interact with message form ---")
        
        # Try method 1: Direct text input
        try:
            user_message = await page.query_selector("input[key='user_message']")
            if await debug_element(page, user_message, "Message input (by key)"):
                await user_message.fill("테스트 메시지")
                print("Filled message input")
            else:
                # Try other selector methods
                user_message = await page.query_selector("input[aria-label='메시지 입력:']")
                if await debug_element(page, user_message, "Message input (by aria-label)"):
                    await user_message.fill("테스트 메시지")
                    print("Filled message input (aria-label)")
        except Exception as e:
            print(f"Error filling message: {str(e)}")
            
        # Try to find the send button 
        try:
            send_button = await page.query_selector("button:has-text('전송')")
            if await debug_element(page, send_button, "Send button"):
                # Before clicking, take another screenshot
                await page.screenshot(path="debug_5_before_send.png")
                await send_button.click()
                print("Clicked send button")
            else:
                # Try to find submit button in the form
                message_form = await page.query_selector("form[key='message_form']")
                if message_form:
                    submit_button = await message_form.query_selector("button[type='submit']")
                    if await debug_element(page, submit_button, "Submit button"):
                        await submit_button.click()
                        print("Clicked submit button")
        except Exception as e:
            print(f"Error clicking send button: {str(e)}")
        
        # Wait to see if message is sent
        await asyncio.sleep(5)
        await page.screenshot(path="debug_6_after_send.png")
            
        # Step 8: DOM structure exploration - this can help identify why selectors aren't working
        print("\n--- DOM Structure ---")
        structure = await page.evaluate('''() => {
            function getStructure(element, depth = 0) {
                if (!element) return '';
                
                let result = ' '.repeat(depth * 2) + element.tagName.toLowerCase();
                
                if (element.id) result += `#${element.id}`;
                if (element.className) {
                    const classes = element.className.split(' ').filter(c => c).map(c => `.${c}`).join('');
                    result += classes;
                }
                
                // Add key attribute if present (useful for Streamlit)
                if (element.hasAttribute('key')) {
                    result += ` key="${element.getAttribute('key')}"`;
                }
                
                // Add placeholder for inputs
                if (element.tagName.toLowerCase() === 'input' && element.hasAttribute('placeholder')) {
                    result += ` placeholder="${element.getAttribute('placeholder')}"`;
                }
                
                result += '\\n';
                
                for (const child of element.children) {
                    result += getStructure(child, depth + 1);
                }
                
                return result;
            }
            
            return getStructure(document.body);
        }''')
        
        print("DOM Structure (partial):")
        lines = structure.split('\n')
        # Print only form-related lines for brevity
        for line in lines:
            if 'form' in line or 'input' in line or 'button' in line:
                print(line)
        
        # Wait before closing
        await asyncio.sleep(10)
        await browser.close()
        print("Debug session completed")

if __name__ == "__main__":
    asyncio.run(test_app())
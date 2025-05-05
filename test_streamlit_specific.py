import asyncio
from playwright.async_api import async_playwright

async def test_streamlit_app():
    """
    Streamlit-specific test script that uses a different approach to interact with Streamlit forms.
    Streamlit uses shadow DOM and iframes which can make standard Playwright selectors challenging.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Navigate to the app and wait for load
        await page.goto("http://localhost:8501")
        print("Navigated to Streamlit app")
        await page.wait_for_load_state("networkidle")
        
        # Login flow
        try:
            # Wait for the stStreamlitApp element which contains the entire app
            await page.wait_for_selector("div[data-testid='stAppViewContainer']", timeout=10000)
            print("Streamlit app container found")
            
            # Use JavaScript evaluation to interact with the form
            # This can bypass shadow DOM issues
            await page.evaluate("""
                // Find the nickname input by its placeholder
                const inputs = Array.from(document.querySelectorAll('input'));
                const nicknameInput = inputs.find(input => input.placeholder === '닉네임을 입력하세요');
                if (nicknameInput) {
                    nicknameInput.value = 'TestUser';
                    nicknameInput.dispatchEvent(new Event('input', { bubbles: true }));
                    console.log('Set nickname value');
                }
                
                // Find and click the start button
                setTimeout(() => {
                    const buttons = Array.from(document.querySelectorAll('button'));
                    const startButton = buttons.find(button => button.innerText.includes('시작하기'));
                    if (startButton) {
                        startButton.click();
                        console.log('Clicked start button');
                    }
                }, 500);
            """)
            
            print("Performed login via JavaScript")
            await page.screenshot(path="streamlit_1_after_login.png")
            await asyncio.sleep(3)
            
            # Company selection
            await page.evaluate("""
                const buttons = Array.from(document.querySelectorAll('button'));
                const selectButtons = buttons.filter(button => button.innerText.includes('선택'));
                if (selectButtons.length > 0) {
                    selectButtons[0].click();
                    console.log('Clicked first company select button');
                }
            """)
            
            print("Selected company via JavaScript")
            await page.screenshot(path="streamlit_2_after_company.png")
            await asyncio.sleep(3)
            
            # Scenario selection
            await page.evaluate("""
                const buttons = Array.from(document.querySelectorAll('button'));
                const scenarioButtons = buttons.filter(button => button.innerText.includes('이 상황으로 시작'));
                if (scenarioButtons.length > 0) {
                    scenarioButtons[0].click();
                    console.log('Clicked first scenario button');
                }
            """)
            
            print("Selected scenario via JavaScript")
            await page.screenshot(path="streamlit_3_after_scenario.png")
            await asyncio.sleep(3)
            
            # Message sending with modified approach for Streamlit
            try:
                print("Attempting to find and interact with message input...")
                
                # Wait a bit to make sure chat UI is fully loaded
                await asyncio.sleep(3)
                
                # Take screenshot before attempting to find input
                await page.screenshot(path="streamlit_before_input_search.png")
                
                # First approach: Use direct DOM manipulation
                # This prints all inputs on the page for debugging
                input_elements = await page.evaluate("""() => {
                    const inputs = Array.from(document.querySelectorAll('input'));
                    return inputs.map((input, i) => {
                        return {
                            index: i,
                            placeholder: input.placeholder || 'no-placeholder',
                            id: input.id,
                            type: input.type,
                            className: input.className,
                            isVisible: input.getBoundingClientRect().width > 0 && input.getBoundingClientRect().height > 0
                        };
                    });
                }""")
                
                print("Found input elements on page:")
                for i, inp in enumerate(input_elements):
                    print(f"  Input {i}: placeholder='{inp['placeholder']}', type={inp['type']}, visible={inp['isVisible']}")
                
                # Enhanced approach: Interact directly with stTextInput widgets
                await page.evaluate("""() => {
                    // More aggressive approach to find Streamlit inputs
                    // 1. Look for specific Streamlit structures
                    const streamlitWidgets = document.querySelectorAll('[data-testid="stFormSubmitButton"]');
                    console.log(`Found ${streamlitWidgets.length} Streamlit form submit buttons`);
                    
                    // If we found form submit buttons, find their parent forms
                    if (streamlitWidgets.length > 0) {
                        let formElement;
                        let submitButton;
                        
                        // Find the form element containing the submit button
                        for (const btn of streamlitWidgets) {
                            let element = btn;
                            while (element && element.tagName !== 'FORM') {
                                element = element.parentElement;
                            }
                            if (element && element.tagName === 'FORM') {
                                formElement = element;
                                submitButton = btn;
                                console.log('Found form with submit button');
                                break;
                            }
                        }
                        
                        if (formElement) {
                            // Find any input in the form
                            const inputs = formElement.querySelectorAll('input');
                            console.log(`Form has ${inputs.length} inputs`);
                            
                            if (inputs.length > 0) {
                                // Use the first input we find
                                const input = inputs[0];
                                console.log(`Found input element: id=${input.id}, type=${input.type}`);
                                
                                // Set the value and dispatch events
                                input.value = '유심 해킹에 대해 걱정이 됩니다. 어떻게 보호할 수 있나요?';
                                input.dispatchEvent(new Event('input', { bubbles: true }));
                                input.dispatchEvent(new Event('change', { bubbles: true }));
                                
                                console.log('Set input value');
                                
                                // Delay before clicking submit
                                setTimeout(() => {
                                    if (submitButton) {
                                        submitButton.click();
                                        console.log('Clicked submit button');
                                    }
                                }, 1000);
                                
                                return true;
                            }
                        }
                    }
                    
                    // 2. General approach - look for any input in the document
                    const inputs = Array.from(document.querySelectorAll('input:not([type="hidden"]'));
                    console.log(`Found ${inputs.length} non-hidden inputs in document`);
                    
                    if (inputs.length > 0) {
                        // Try to find an input with message-related placeholder or nearby a "전송" button
                        let messageInput = null;
                        
                        // First pass: Look for placeholder containing 메시지
                        messageInput = inputs.find(input => 
                            input.placeholder && input.placeholder.includes('메시지'));
                        
                        // Second pass: Look for visible inputs
                        if (!messageInput) {
                            messageInput = inputs.find(input => {
                                const rect = input.getBoundingClientRect();
                                return rect.width > 0 && rect.height > 0;
                            });
                        }
                        
                        // Third pass: Just use any input
                        if (!messageInput && inputs.length > 0) {
                            messageInput = inputs[0];
                        }
                        
                        if (messageInput) {
                            console.log(`Using input: id=${messageInput.id}, type=${messageInput.type}, placeholder=${messageInput.placeholder}`);
                            
                            // Set value and dispatch events
                            messageInput.value = '유심 해킹에 대해 걱정이 됩니다. 어떻게 보호할 수 있나요?';
                            messageInput.dispatchEvent(new Event('input', { bubbles: true }));
                            messageInput.dispatchEvent(new Event('change', { bubbles: true }));
                            
                            console.log('Set message input value');
                            
                            // Find a nearby submit button
                            const submitButtons = Array.from(document.querySelectorAll('button'));
                            let submitButton = null;
                            
                            // First try to find a button with text containing "전송"
                            submitButton = submitButtons.find(button => 
                                button.innerText && button.innerText.includes('전송'));
                            
                            // If not found, try to find a submit button
                            if (!submitButton) {
                                submitButton = document.querySelector('button[type="submit"]');
                            }
                            
                            // If still not found, look for a button near the input
                            if (!submitButton) {
                                // Find the nearest form or container
                                let container = messageInput.closest('form') || messageInput.parentElement;
                                while (container && !container.querySelector('button') && container !== document.body) {
                                    container = container.parentElement;
                                }
                                
                                if (container) {
                                    submitButton = container.querySelector('button');
                                }
                            }
                            
                            if (submitButton) {
                                setTimeout(() => {
                                    console.log(`Clicking button: ${submitButton.innerText || 'unnamed button'}`);
                                    submitButton.click();
                                }, 1000);
                                return true;
                            } else {
                                console.log('Could not find submit button');
                            }
                        }
                    }
                    
                    return false;
                }""")
                
                # Wait for any response
                await asyncio.sleep(10)
                
                # Take screenshot after attempting to send message
                await page.screenshot(path="streamlit_after_send_attempt.png")
                print("Screenshot saved after send attempt")
                
            except Exception as e:
                print(f"Error during message sending: {e}")
                await page.screenshot(path="streamlit_error_sending.png")
                
            # Capture final state
            await asyncio.sleep(5)
            await page.screenshot(path="streamlit_4_after_message.png")
                
        except Exception as e:
            print(f"Test failed: {e}")
            await page.screenshot(path="streamlit_error.png")
        
        finally:
            # Always close the browser
            await asyncio.sleep(5)
            await browser.close()
            print("Test completed")

if __name__ == "__main__":
    asyncio.run(test_streamlit_app())
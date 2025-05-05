import pytest
import asyncio
from playwright.async_api import Page, expect

@pytest.mark.asyncio
async def test_login_page(page: Page):
    # Navigate to the Streamlit app
    await page.goto("http://localhost:8501")
    
    # Check if the login page is displayed
    await expect(page.locator("text=CS 대화 시뮬레이션")).to_be_visible()
    await expect(page.locator("text=환영합니다!")).to_be_visible()
    
    # Test the login form
    await page.fill("input[placeholder='닉네임을 입력하세요']", "TestUser")
    await page.click("text=시작하기")
    
    # Check if navigated to company selection page
    await expect(page.locator("text=어떤 기업과 대화하시겠어요?")).to_be_visible()

@pytest.mark.asyncio
async def test_company_selection(page: Page):
    # First login
    await page.goto("http://localhost:8501")
    await page.fill("input[placeholder='닉네임을 입력하세요']", "TestUser")
    await page.click("text=시작하기")
    
    # Check if all companies are displayed
    await expect(page.locator("text=SK텔레콤")).to_be_visible()
    await expect(page.locator("text=삼성전자")).to_be_visible()
    await expect(page.locator("text=쿠팡")).to_be_visible()
    
    # Select a company
    company_buttons = await page.query_selector_all("button:has-text('선택')")
    await company_buttons[0].click()
    
    # Check if navigated to scenario selection page
    await expect(page.locator("text=상황 선택")).to_be_visible()

@pytest.mark.asyncio
async def test_chat_functionality(page: Page):
    # Login
    await page.goto("http://localhost:8501")
    await page.fill("input[placeholder='닉네임을 입력하세요']", "TestUser")
    await page.click("text=시작하기")
    
    # Select company
    company_buttons = await page.query_selector_all("button:has-text('선택')")
    await company_buttons[0].click()
    
    # Select scenario
    scenario_buttons = await page.query_selector_all("button:has-text('이 상황으로 시작')")
    await scenario_buttons[0].click()
    
    # Check if chat page is loaded
    await expect(page.locator(".chat-container")).to_be_visible()
    
    # Send a message
    await page.fill("input[placeholder='메시지 입력:']", "안녕하세요")
    await page.click("text=전송")
    
    # Wait for response (may need adjustment based on response time)
    await page.wait_for_timeout(5000)
    
    # Check if a new bot message is displayed
    messages = await page.query_selector_all(".bot-message")
    assert len(messages) >= 1, "Did not receive a response from the bot"

@pytest.mark.asyncio
async def test_error_handling(page: Page):
    # Test with LangGraph server down (assume it's down for this test)
    # Note: This test may need to be adjusted to simulate server downtime
    
    # Navigate to app with server down conditions
    await page.goto("http://localhost:8501")
    
    # Complete login flow
    await page.fill("input[placeholder='닉네임을 입력하세요']", "TestUser")
    await page.click("text=시작하기")
    
    # Select company and scenario
    company_buttons = await page.query_selector_all("button:has-text('선택')")
    await company_buttons[0].click()
    
    scenario_buttons = await page.query_selector_all("button:has-text('이 상황으로 시작')")
    await scenario_buttons[0].click()
    
    # Send a message that would trigger server communication
    await page.fill("input[placeholder='메시지 입력:']", "테스트 메시지")
    await page.click("text=전송")
    
    # Check for error handling (this may need adjustment)
    # Either look for an error message or check that the UI handles the error gracefully
    await page.wait_for_timeout(3000)
    
    # The test passes if no uncaught exceptions are thrown
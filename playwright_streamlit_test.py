import asyncio
from playwright.async_api import async_playwright
import time

"""
이 스크립트는 Streamlit 앱을 Playwright로 테스트하기 위한 최적화된 코드입니다.
Streamlit의 특수한 DOM 구조를 고려하여 작성되었습니다.
"""

async def test_streamlit_app():
    async with async_playwright() as p:
        # 브라우저 및 페이지 설정
        browser = await p.chromium.launch(headless=False)  # GUI로 확인하기 위해 headless=False
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # Step 1: 애플리케이션 로드
            print("Streamlit 앱을 로드 중...")
            await page.goto("http://localhost:8501")
            await page.wait_for_load_state("networkidle")
            print("앱 로드 완료")
            
            # Step 2: 로그인
            print("로그인 진행 중...")
            await page.wait_for_selector("input[placeholder='닉네임을 입력하세요']", timeout=10000)
            await page.fill("input[placeholder='닉네임을 입력하세요']", "TestUser")
            
            # 디버깅용 스크린샷
            await page.screenshot(path="step1_login.png")
            
            await page.click("button:has-text('시작하기')")
            await page.wait_for_selector("text=어떤 기업과 대화하시겠어요?", timeout=10000)
            print("로그인 성공")
            
            # Step 3: 기업 선택
            print("기업 선택 중...")
            company_buttons = await page.query_selector_all("button:has-text('선택')")
            if len(company_buttons) == 0:
                print("⚠️ 기업 선택 버튼을 찾을 수 없습니다")
                await page.screenshot(path="error_company_selection.png")
                return
            
            await company_buttons[0].click()  # 첫 번째 기업 선택
            await page.wait_for_selector("text=상황 선택", timeout=10000)
            print("기업 선택 성공")
            
            # 디버깅용 스크린샷
            await page.screenshot(path="step2_company_selected.png")
            
            # Step 4: 시나리오 선택
            print("시나리오 선택 중...")
            scenario_buttons = await page.query_selector_all("button:has-text('이 상황으로 시작')")
            if len(scenario_buttons) == 0:
                print("⚠️ 시나리오 선택 버튼을 찾을 수 없습니다")
                await page.screenshot(path="error_scenario_selection.png")
                return
            
            await scenario_buttons[0].click()  # 첫 번째 시나리오 선택
            
            # 채팅 페이지가 로드될 때까지 대기
            await page.wait_for_selector(".chat-container", timeout=10000)
            print("시나리오 선택 성공, 채팅 UI 로드됨")
            
            # 디버깅용 스크린샷
            await page.screenshot(path="step3_scenario_selected.png")
            
            # 채팅 UI가 완전히 로드될 때까지 약간의 지연
            await asyncio.sleep(2)
            
            # Step 5: 메시지 입력 구현
            print("메시지 입력 및 전송 준비 중...")
            
            # Streamlit 폼 구조는 복잡할 수 있어 JavaScript로 직접 DOM 조작
            sent = await page.evaluate("""() => {
                // 1. 모든 입력 필드 검색
                const inputs = Array.from(document.querySelectorAll('input'));
                console.log(`${inputs.length}개의 입력 필드 발견`);
                
                // 2. 메시지 입력으로 보이는 필드 찾기 (여러 가지 방법 시도)
                let messageInput = null;
                
                // 플레이스홀더로 먼저 시도
                messageInput = inputs.find(input => input.placeholder && input.placeholder.includes('메시지'));
                
                // 못 찾으면 form 내부의 입력 필드 시도
                if (!messageInput) {
                    const form = document.querySelector('form');
                    if (form) {
                        const formInputs = form.querySelectorAll('input');
                        if (formInputs.length > 0) {
                            messageInput = formInputs[0];
                        }
                    }
                }
                
                // 여전히 못 찾으면 첫 번째 입력 필드 사용
                if (!messageInput && inputs.length > 0) {
                    messageInput = inputs[0];
                }
                
                if (!messageInput) {
                    console.error('메시지 입력 필드를 찾을 수 없습니다.');
                    return false;
                }
                
                // 3. 입력 필드에 값 설정
                console.log(`메시지 입력 필드 식별됨: ${messageInput.placeholder || '플레이스홀더 없음'}`);
                messageInput.value = '유심 해킹 관련 보호 조치에 대해 알려주세요.';
                
                // 4. 이벤트 발생시키기 (Streamlit은 이벤트 감지)
                messageInput.dispatchEvent(new Event('input', { bubbles: true }));
                messageInput.dispatchEvent(new Event('change', { bubbles: true }));
                
                // 5. 전송 버튼 찾기
                // a. 폼 내부의 제출 버튼
                let submitButton = null;
                const form = messageInput.closest('form');
                
                if (form) {
                    submitButton = form.querySelector('button[type="submit"]');
                }
                
                // b. "전송" 텍스트가 있는 버튼
                if (!submitButton) {
                    const buttons = Array.from(document.querySelectorAll('button'));
                    submitButton = buttons.find(btn => btn.innerText && btn.innerText.includes('전송'));
                }
                
                // c. 폼 안의 아무 버튼
                if (!submitButton && form) {
                    const formButtons = form.querySelectorAll('button');
                    if (formButtons.length > 0) {
                        submitButton = formButtons[0];
                    }
                }
                
                if (!submitButton) {
                    console.error('전송 버튼을 찾을 수 없습니다.');
                    return false;
                }
                
                // 6. 버튼 클릭
                console.log(`전송 버튼 클릭: ${submitButton.innerText || '텍스트 없음'}`);
                submitButton.click();
                
                return true;
            }""")
            
            if sent:
                print("✅ 메시지 전송 성공!")
            else:
                print("⚠️ 메시지 전송 실패")
            
            # 응답 대기 (LLM 처리 시간이 필요합니다)
            print("챗봇 응답 대기 중...")
            await asyncio.sleep(10)  # 필요에 따라 시간 조정
            
            # 최종 상태 확인 및 스크린샷
            await page.screenshot(path="step4_message_sent.png")
            
            # 봇 응답 확인 시도
            bot_messages = await page.query_selector_all(".bot-message")
            print(f"발견된 봇 메시지: {len(bot_messages)}개")
            
            if len(bot_messages) >= 2:  # 초기 인사말 + 응답
                bot_message_text = await bot_messages[-1].inner_text()
                print(f"봇 응답 (일부): {bot_message_text[:100]}...")
                print("✅ 대화 테스트가 성공적으로 완료되었습니다!")
            else:
                print("⚠️ 봇의 응답을 감지하지 못했습니다.")
                
        except Exception as e:
            print(f"❌ 테스트 중 오류 발생: {str(e)}")
            await page.screenshot(path="error_screenshot.png")
            print("오류 발생 시점의 스크린샷이 저장되었습니다.")
            
        finally:
            # 브라우저 닫기 전 지연
            await asyncio.sleep(3)
            await browser.close()
            print("테스트 종료")

if __name__ == "__main__":
    asyncio.run(test_streamlit_app())
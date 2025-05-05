import asyncio
from playwright.async_api import async_playwright

"""
이 스크립트는 Streamlit 앱의 DOM 구조를 분석하고 입력 필드와 버튼을 찾기 위한 도우미 스크립트입니다.
Streamlit은 shadow DOM 및 iframe을 사용하기 때문에 일반적인 Playwright 셀렉터가 작동하지 않을 수 있습니다.
"""

async def analyze_streamlit_form():
    """Streamlit 페이지의 폼 구조를 분석합니다."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        # 앱으로 이동 및 로드 대기
        print("Streamlit 앱으로 이동 중...")
        await page.goto("http://localhost:8501")
        await page.wait_for_load_state("networkidle")
        
        # 로그인
        print("로그인 시도 중...")
        await page.fill("input[placeholder='닉네임을 입력하세요']", "TestUser")
        await page.click("text=시작하기")
        await asyncio.sleep(3)
        
        # 기업 선택
        print("기업 선택 중...")
        company_buttons = await page.query_selector_all("button:has-text('선택')")
        if len(company_buttons) > 0:
            await company_buttons[0].click()
            await asyncio.sleep(3)
        
        # 시나리오 선택
        print("시나리오 선택 중...")
        scenario_buttons = await page.query_selector_all("button:has-text('이 상황으로 시작')")
        if len(scenario_buttons) > 0:
            await scenario_buttons[0].click()
            await asyncio.sleep(3)
        
        # 페이지의 모든 HTML 구조 출력 (폼 구조에 중점)
        print("\n=== 메시지 폼 분석 시작 ===")
        
        # 모든 폼 요소 찾기
        form_info = await page.evaluate("""() => {
            // 모든 폼 찾기
            const forms = Array.from(document.querySelectorAll('form'));
            
            return forms.map((form, formIndex) => {
                // 폼 속성 수집
                const formAttrs = {};
                Array.from(form.attributes).forEach(attr => {
                    formAttrs[attr.name] = attr.value;
                });
                
                // 폼 내 입력 필드 찾기
                const inputs = Array.from(form.querySelectorAll('input'));
                const inputsInfo = inputs.map((input, inputIndex) => {
                    // 입력 필드 속성 수집
                    const inputAttrs = {};
                    Array.from(input.attributes).forEach(attr => {
                        inputAttrs[attr.name] = attr.value;
                    });
                    
                    // 위치 정보
                    const rect = input.getBoundingClientRect();
                    const isVisible = rect.width > 0 && rect.height > 0;
                    
                    return {
                        index: inputIndex,
                        type: input.type,
                        id: input.id,
                        name: input.name,
                        placeholder: input.placeholder,
                        value: input.value,
                        attributes: inputAttrs,
                        isVisible,
                        position: {
                            x: rect.x,
                            y: rect.y,
                            width: rect.width,
                            height: rect.height
                        }
                    };
                });
                
                // 폼 내 버튼 찾기
                const buttons = Array.from(form.querySelectorAll('button'));
                const buttonsInfo = buttons.map((button, buttonIndex) => {
                    // 버튼 속성 수집
                    const buttonAttrs = {};
                    Array.from(button.attributes).forEach(attr => {
                        buttonAttrs[attr.name] = attr.value;
                    });
                    
                    // 위치 정보
                    const rect = button.getBoundingClientRect();
                    const isVisible = rect.width > 0 && rect.height > 0;
                    
                    return {
                        index: buttonIndex,
                        type: button.type,
                        id: button.id,
                        text: button.innerText,
                        attributes: buttonAttrs,
                        isVisible,
                        position: {
                            x: rect.x,
                            y: rect.y,
                            width: rect.width,
                            height: rect.height
                        }
                    };
                });
                
                return {
                    formIndex,
                    attributes: formAttrs,
                    inputs: inputsInfo,
                    buttons: buttonsInfo
                };
            });
        }""")
        
        # 폼 정보 출력
        print(f"\n총 {len(form_info)}개의 폼이 발견되었습니다.")
        
        for i, form in enumerate(form_info):
            print(f"\n== 폼 #{i+1} ==")
            print(f"속성: {form['attributes']}")
            
            print(f"\n입력 필드 ({len(form['inputs'])}개):")
            for input_field in form['inputs']:
                print(f"  - 입력 필드 #{input_field['index']+1}")
                print(f"    유형: {input_field['type']}")
                print(f"    ID: {input_field['id']}")
                print(f"    플레이스홀더: {input_field['placeholder']}")
                print(f"    보이는지 여부: {input_field['isVisible']}")
                print(f"    위치: x={input_field['position']['x']}, y={input_field['position']['y']}")
            
            print(f"\n버튼 ({len(form['buttons'])}개):")
            for button in form['buttons']:
                print(f"  - 버튼 #{button['index']+1}")
                print(f"    유형: {button['type']}")
                print(f"    ID: {button['id']}")
                print(f"    텍스트: {button['text']}")
                print(f"    보이는지 여부: {button['isVisible']}")
                print(f"    위치: x={button['position']['x']}, y={button['position']['y']}")
        
        # Streamlit 특수 요소 분석
        print("\n=== Streamlit 특수 요소 분석 ===")
        streamlit_elements = await page.evaluate("""() => {
            const results = {};
            
            // Streamlit에서 사용하는 특수 data-testid 속성 찾기
            const testIdElements = Array.from(document.querySelectorAll('[data-testid]'));
            results.testIdElements = testIdElements.map(el => {
                return {
                    testId: el.getAttribute('data-testid'),
                    tagName: el.tagName,
                    innerText: el.innerText.substring(0, 30) + (el.innerText.length > 30 ? '...' : '')
                };
            });
            
            // Streamlit의 iframe 분석 (있는 경우)
            const iframes = Array.from(document.querySelectorAll('iframe'));
            results.iframes = iframes.map(iframe => {
                return {
                    src: iframe.src,
                    id: iframe.id,
                    name: iframe.name
                };
            });
            
            return results;
        }""")
        
        print("\nStreamlit 테스트 ID 요소:")
        for el in streamlit_elements.get('testIdElements', []):
            print(f"  - {el['tagName']} [data-testid='{el['testId']}']: {el['innerText']}")
        
        print("\nIframe 요소 (있는 경우):")
        for iframe in streamlit_elements.get('iframes', []):
            print(f"  - src: {iframe['src']}, id: {iframe['id']}, name: {iframe['name']}")
        
        # 채팅 UI 분석
        chat_container = await page.query_selector(".chat-container")
        if chat_container:
            print("\n=== 채팅 UI 분석 ===")
            
            # 채팅 컨테이너 구조
            chat_structure = await page.evaluate("""() => {
                const container = document.querySelector('.chat-container');
                if (!container) return null;
                
                // 메시지 찾기
                const userMessages = Array.from(container.querySelectorAll('.user-message'));
                const botMessages = Array.from(container.querySelectorAll('.bot-message'));
                
                return {
                    userMessageCount: userMessages.length,
                    botMessageCount: botMessages.length,
                    latestUserMessage: userMessages.length > 0 ? userMessages[userMessages.length-1].innerText : null,
                    latestBotMessage: botMessages.length > 0 ? botMessages[botMessages.length-1].innerText.substring(0, 50) + '...' : null
                };
            }""")
            
            print(f"사용자 메시지 수: {chat_structure['userMessageCount']}")
            print(f"봇 메시지 수: {chat_structure['botMessageCount']}")
            print(f"최근 사용자 메시지: {chat_structure['latestUserMessage']}")
            print(f"최근 봇 메시지: {chat_structure['latestBotMessage']}")
        
        # 완성된 선택자 제안
        print("\n=== 권장 선택자 ===")
        suggested_selectors = await page.evaluate("""() => {
            // 메시지 입력 필드 찾기
            let messageInput = null;
            let submitButton = null;
            
            // 방법 1: 폼 키로 찾기
            const messageForm = document.querySelector('form[key="message_form"]');
            if (messageForm) {
                messageInput = messageForm.querySelector('input');
                submitButton = messageForm.querySelector('button[type="submit"]');
            }
            
            // 방법 2: 플레이스홀더로 찾기
            if (!messageInput) {
                messageInput = Array.from(document.querySelectorAll('input')).find(
                    input => input.placeholder && input.placeholder.includes('메시지')
                );
            }
            
            // 방법 3: 전송 버튼 텍스트로 찾기
            if (!submitButton) {
                submitButton = Array.from(document.querySelectorAll('button')).find(
                    button => button.innerText && button.innerText.includes('전송')
                );
            }
            
            // 찾은 요소로 선택자 생성
            const selectors = {};
            
            if (messageInput) {
                // 입력 필드 선택자 생성
                selectors.messageInputId = messageInput.id ? `input#${messageInput.id}` : null;
                selectors.messageInputClass = messageInput.className ? `input.${messageInput.className.replace(/\s+/g, '.')}` : null;
                selectors.messageInputPlaceholder = messageInput.placeholder ? `input[placeholder="${messageInput.placeholder}"]` : null;
                
                // 위치 기반 선택자 (마지막 수단)
                const rect = messageInput.getBoundingClientRect();
                selectors.messageInputPosition = `x: ${rect.x}, y: ${rect.y}, width: ${rect.width}, height: ${rect.height}`;
            }
            
            if (submitButton) {
                // 버튼 선택자 생성
                selectors.submitButtonId = submitButton.id ? `button#${submitButton.id}` : null;
                selectors.submitButtonClass = submitButton.className ? `button.${submitButton.className.replace(/\s+/g, '.')}` : null;
                selectors.submitButtonText = submitButton.innerText ? `button:has-text("${submitButton.innerText}")` : null;
            }
            
            return selectors;
        }""")
        
        if suggested_selectors:
            print("메시지 입력 필드에 대한 권장 선택자:")
            if suggested_selectors.get('messageInputId'):
                print(f"  ID 선택자: {suggested_selectors['messageInputId']}")
            if suggested_selectors.get('messageInputClass'):
                print(f"  클래스 선택자: {suggested_selectors['messageInputClass']}")
            if suggested_selectors.get('messageInputPlaceholder'):
                print(f"  플레이스홀더 선택자: {suggested_selectors['messageInputPlaceholder']}")
            
            print("\n전송 버튼에 대한 권장 선택자:")
            if suggested_selectors.get('submitButtonId'):
                print(f"  ID 선택자: {suggested_selectors['submitButtonId']}")
            if suggested_selectors.get('submitButtonClass'):
                print(f"  클래스 선택자: {suggested_selectors['submitButtonClass']}")
            if suggested_selectors.get('submitButtonText'):
                print(f"  텍스트 선택자: {suggested_selectors['submitButtonText']}")
        
        # 권장 JavaScript 코드
        print("\n=== 권장 JavaScript 코드 ===")
        print("""
// Streamlit 채팅 메시지 전송을 위한 JavaScript 코드
function sendChatMessage(message) {
    // 1. 모든 폼 검색
    const messageForm = document.querySelector('form[key="message_form"]');
    
    if (messageForm) {
        // 2. 폼에서 입력 필드 찾기
        const inputField = messageForm.querySelector('input');
        
        if (inputField) {
            // 3. 메시지 설정
            inputField.value = message;
            inputField.dispatchEvent(new Event('input', { bubbles: true }));
            
            // 4. 폼 제출
            const submitButton = messageForm.querySelector('button[type="submit"]');
            if (submitButton) {
                submitButton.click();
                return true;
            }
        }
    }
    
    // 대체 방법: 플레이스홀더로 검색
    const inputs = Array.from(document.querySelectorAll('input'));
    const messageInput = inputs.find(input => 
        input.placeholder && input.placeholder.includes('메시지 입력'));
    
    if (messageInput) {
        messageInput.value = message;
        messageInput.dispatchEvent(new Event('input', { bubbles: true }));
        
        // 가장 가까운 폼 찾기
        const form = messageInput.closest('form');
        if (form) {
            const submitButton = form.querySelector('button[type="submit"]');
            if (submitButton) {
                submitButton.click();
                return true;
            }
        }
        
        // 전송 텍스트가 있는 버튼 찾기
        const buttons = Array.from(document.querySelectorAll('button'));
        const sendButton = buttons.find(button => 
            button.innerText && button.innerText.includes('전송'));
        
        if (sendButton) {
            sendButton.click();
            return true;
        }
    }
    
    return false;
}
        """)
        
        # 실제 메시지 전송 시도 (테스트 목적)
        print("\n=== 실제 메시지 전송 시도 ===")
        sent = await page.evaluate("""() => {
            // 위에서 제안한 함수 다시 정의
            function sendChatMessage(message) {
                // 1. 모든 폼 검색
                const messageForm = document.querySelector('form');
                
                if (messageForm) {
                    // 2. 폼에서 입력 필드 찾기
                    const inputField = messageForm.querySelector('input');
                    
                    if (inputField) {
                        // 3. 메시지 설정
                        inputField.value = message;
                        inputField.dispatchEvent(new Event('input', { bubbles: true }));
                        
                        // 4. 폼 제출
                        const submitButton = messageForm.querySelector('button[type="submit"]');
                        if (submitButton) {
                            submitButton.click();
                            return true;
                        }
                    }
                }
                
                // 대체 방법: 모든 입력 필드 중 첫 번째
                const inputs = Array.from(document.querySelectorAll('input'));
                if (inputs.length > 0) {
                    const messageInput = inputs[0];
                    messageInput.value = message;
                    messageInput.dispatchEvent(new Event('input', { bubbles: true }));
                    
                    // 모든 버튼 중 첫 번째
                    const buttons = Array.from(document.querySelectorAll('button'));
                    if (buttons.length > 0) {
                        buttons[0].click();
                        return true;
                    }
                }
                
                return false;
            }
            
            // 실제 메시지 전송 시도
            return sendChatMessage("안녕하세요, 메시지 전송 테스트입니다.");
        }""")
        
        print(f"메시지 전송 시도 결과: {'성공' if sent else '실패'}")
        
        # 테스트 후 스크린샷 촬영
        await page.screenshot(path="streamlit_test_result.png")
        print("스크린샷 저장됨: streamlit_test_result.png")
        
        # 완료 후 브라우저 닫기
        await asyncio.sleep(3)
        await browser.close()
        print("분석 완료")

if __name__ == "__main__":
    asyncio.run(analyze_streamlit_form())
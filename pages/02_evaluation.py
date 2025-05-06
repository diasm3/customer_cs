import streamlit as st
import asyncio
import sys
import os
import uuid
from datetime import datetime
import json
import re

# 상위 디렉토리를 import path에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# LangGraph 클라이언트 임포트
from utils.langraph_client import create_langgraph_client,  add_message_to_thread

# evaluation_agent 모듈 임포트
from agents.evaluation_agent import (
    evaluate_conversation_node,
    analyze_conversation_context,
    preprocess_conversation,
    postprocess_evaluation,
    run_llm_evaluation,
    construct_evaluation_prompt
)

# CSS 파일 로드 함수
def load_css(css_file):
    with open(css_file, "r") as f:
        css = f.read()
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

# CSS 로드
css_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "css", "chat_style.css")
load_css(css_path)

# 페이지 제목
st.write("<div class='main-title'>대화 평가 결과</div>", unsafe_allow_html=True)

# 로그인 확인
if 'nickname' not in st.session_state or not st.session_state.nickname:
    st.warning("먼저, 닉네임을 입력해주세요.")
    st.session_state.page = "login"
    st.rerun()

# 채팅 메시지 확인
if 'chat_messages' not in st.session_state or len(st.session_state.chat_messages) < 2:
    st.warning("먼저, 대화를 진행해주세요.")
    st.session_state.page = "scenario_select"
    st.rerun()

# 회사 및 시나리오 정보 확인
company = st.session_state.company
scenario = st.session_state.scenario
user_id = st.session_state.user_id

# 시나리오 정보
with st.expander("대화 시나리오 정보", expanded=False):
    st.write(f"""
    <div class='scenario-box'>
        <h3>{company['name']} - {scenario['title']}</h3>
        <p><strong>설명:</strong> {scenario['description']}</p>
        <p><strong>고객 목표:</strong> {scenario.get('customer_objective', '지정된 목표 없음')}</p>
        <p><strong>기업 목표:</strong> {scenario.get('company_objective', '지정된 목표 없음')}</p>
    </div>
    """, unsafe_allow_html=True)

# 대화 내용 표시
with st.expander("대화 내용", expanded=False):
    st.write("<div class='chat-container'>", unsafe_allow_html=True)
    for msg in st.session_state.chat_messages:
        role_class = "user-message" if msg["role"] == "user" else "bot-message"
        st.write(f"<div class='{role_class}'>{msg['content']}</div>", unsafe_allow_html=True)
    st.write("</div>", unsafe_allow_html=True)

# evaluation_agent를 사용하여 평가 결과 가져오기
if 'evaluation_result' not in st.session_state:
    st.write("<div class='subtitle'>대화 평가 중입니다...</div>", unsafe_allow_html=True)
    progress_bar = st.progress(0)
    
    # 비동기 함수로 평가 실행
    async def evaluate_conversation():
        try:
            progress_bar.progress(10)
            
            # 대화 메시지 준비
            messages = []
            for msg in st.session_state.chat_messages:
                role = "user" if msg["role"] == "user" else "assistant"
                content = msg["content"]
                messages.append({"role": role, "content": content})
            
            progress_bar.progress(20)
            
            # 대화 전처리
            processed_conversation = preprocess_conversation(messages)
            
            progress_bar.progress(30)
            
            # 시나리오 컨텍스트 정보
            scenario_context = {
                "scenario_id": scenario['id'],
                "description": scenario['description']
            }
            
            # 고객 및 기업 목표
            customer_objective = scenario.get('customer_objective', '지정된 고객 목표 없음')
            company_objective = scenario.get('company_objective', '지정된 기업 목표 없음')
            
            progress_bar.progress(40)
            
            # 대화 맥락 분석
            context_analysis = analyze_conversation_context(
                processed_conversation,
                customer_objective,
                company_objective,
                scenario_context
            )
            
            progress_bar.progress(50)
            
            # 평가 프롬프트 구성
            prompt = construct_evaluation_prompt(
                processed_conversation,
                context_analysis,
                customer_objective,
                company_objective
            )
            
            progress_bar.progress(60)
            
            # LLM 기반 평가 실행
            evaluation_result = await run_llm_evaluation(prompt)
            
            progress_bar.progress(80)
            
            # 평가 결과 구조화
            final_result = postprocess_evaluation(evaluation_result)
            
            progress_bar.progress(90)
            
            # 평가 결과 텍스트 생성
            result_text = f"""
            # 대화 평가 결과

            ## 점수 요약
            - 고객 총점: {final_result['customer_scores']['total']}/500
            - 기업 총점: {final_result['company_scores']['total']}/500
            - 승자: {final_result['winner']} (점수차: {final_result.get('margin', '정보 없음')})

            ## 상세 분석
            {final_result['explanation']}

            ## 주요 순간
            {format_key_moments(final_result.get('key_moments', []))}

            ## 개선 제안
            - 고객: {final_result.get('improvement_suggestions', {}).get('customer', '정보 없음')}
            - 기업: {final_result.get('improvement_suggestions', {}).get('company', '정보 없음')}
            """
            
            # 점수 정보 변환 (그래프용)
            scores = {}
            if "customer_scores" in final_result and isinstance(final_result["customer_scores"], dict):
                for key, value in final_result["customer_scores"].items():
                    if key != "total":
                        scores[f"고객_{key}"] = float(value) / 100
            
            if "company_scores" in final_result and isinstance(final_result["company_scores"], dict):
                for key, value in final_result["company_scores"].items():
                    if key != "total":
                        scores[f"기업_{key}"] = float(value) / 100
            
            # 평가 결과 저장
            st.session_state.evaluation_result = {
                "text": result_text,
                "scores": scores,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "raw_data": final_result
            }
            
            progress_bar.progress(100)
            
        except Exception as e:
            st.error(f"평가 중 오류가 발생했습니다: {str(e)}")
            st.session_state.evaluation_result = {
                "text": f"평가 중 오류가 발생했습니다: {str(e)}",
                "scores": {},
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
    
    # 주요 순간 형식화 함수
    def format_key_moments(key_moments):
        if not key_moments:
            return "주요 순간 정보 없음"
        
        formatted = ""
        for moment in key_moments:
            formatted += f"- 턴 {moment.get('turn', '?')}: {moment.get('description', '설명 없음')} (영향: {moment.get('impact', '정보 없음')}, 점수 변화: {moment.get('score_change', '정보 없음')})\n"
        
        return formatted
    
    # 비동기 함수 실행
    asyncio.run(evaluate_conversation())
    
    # 페이지 새로고침
    st.rerun()

# 평가 결과 표시
if 'evaluation_result' in st.session_state:
    # 결과 컨테이너
    with st.container():
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # 평가 내용
            st.write("<div class='scenario-box'>", unsafe_allow_html=True)
            st.write("<h3>평가 세부 내용</h3>", unsafe_allow_html=True)
            st.write(st.session_state.evaluation_result["text"])
            st.write("<p class='company-info'>평가 시간: " + st.session_state.evaluation_result["timestamp"] + "</p>", unsafe_allow_html=True)
            st.write("</div>", unsafe_allow_html=True)
        
        with col2:
            # 점수 표시
            if st.session_state.evaluation_result["scores"]:
                st.write("<div class='company-card'>", unsafe_allow_html=True)
                st.write("<h3>평가 점수</h3>", unsafe_allow_html=True)
                
                for category, score in st.session_state.evaluation_result["scores"].items():
                    # 점수에 따른 색상 결정
                    if score >= 0.9:
                        score_color = "#4CAF50"  # 초록색 (매우 좋음)
                    elif score >= 0.7:
                        score_color = "#2196F3"  # 파란색 (좋음)
                    elif score >= 0.5:
                        score_color = "#FF9800"  # 주황색 (보통)
                    else:
                        score_color = "#F44336"  # 빨간색 (좋지 않음)
                    
                    # 별점 표시 (0.0-1.0 점수를 0-5점 별점으로 변환)
                    stars_count = int(score * 5)
                    half_star = (score * 5) - stars_count >= 0.5
                    stars = "⭐" * stars_count
                    if half_star:
                        stars += "★"
                    
                    # 스코어 표시 (0.0-1.0 점수를 0-100점으로 변환)
                    score_display = int(score * 100)
                    
                    st.write(f"""
                    <div style="margin-bottom: 15px;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span>{category}</span>
                            <span style="color: {score_color}; font-weight: bold;">{score_display}</span>
                        </div>
                        <div style="margin-top: 5px;">{stars}</div>
                        <div style="height: 6px; background-color: #eee; border-radius: 3px; margin-top: 5px;">
                            <div style="height: 100%; width: {score*100}%; background-color: {score_color}; border-radius: 3px;"></div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.write("</div>", unsafe_allow_html=True)
                
                # 승자 배지 표시
                if "raw_data" in st.session_state.evaluation_result and "winner" in st.session_state.evaluation_result["raw_data"]:
                    winner = st.session_state.evaluation_result["raw_data"]["winner"]
                    margin = st.session_state.evaluation_result["raw_data"].get("margin", "")
                    
                    badge_color = "#4CAF50" if winner.lower() == "customer" else "#2196F3"
                    winner_display = "고객" if winner.lower() == "customer" else "기업"
                    
                    st.write(f"""
                    <div style="text-align: center; margin-top: 15px;">
                        <div style="display: inline-block; padding: 8px 15px; background-color: {badge_color}; color: white; border-radius: 20px; font-weight: bold;">
                            승자: {winner_display} {f"(차이: {margin}점)" if margin else ""}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

    # 공유 버튼
    st.write("<div style='text-align: center; margin: 20px 0;'>", unsafe_allow_html=True)
    st.download_button(
        label="평가 결과 다운로드",
        data=st.session_state.evaluation_result["text"],
        file_name=f"chat_evaluation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        mime="text/plain"
    )
    st.write("</div>", unsafe_allow_html=True)

# 버튼 영역
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    # 다시 하기 버튼
    if st.button("다른 시나리오 시작하기", use_container_width=True):
        st.session_state.scenario = None
        st.session_state.thread_id = None
        st.session_state.chat_messages = []
        st.session_state.evaluation_result = None
        st.session_state.page = "scenario_select"
        st.rerun()

    # 처음으로 버튼
    if st.button("처음으로", use_container_width=True):
        # 세션 상태 초기화
        for key in list(st.session_state.keys()):
            if key != 'nickname' and key != 'user_id':
                del st.session_state[key]
        
        st.session_state.page = "login"
        st.rerun()
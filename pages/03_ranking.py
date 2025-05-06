import streamlit as st
import asyncio
import sys
import os
import pandas as pd
from datetime import datetime

# 상위 디렉토리를 import path에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# CSS 파일 로드 함수
def load_css(css_file):
    with open(css_file, "r") as f:
        css = f.read()
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

# CSS 로드
css_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "css", "chat_style.css")
load_css(css_path)

# 페이지 제목
st.write("<div class='main-title'>대화 시뮬레이션 랭킹</div>", unsafe_allow_html=True)

# 세션 상태 초기화
if 'ranking_data' not in st.session_state:
    # 임시 랭킹 데이터 생성
    st.session_state.ranking_data = {
        "company_rankings": [
            {"company_id": "skt", "name": "SK Telecom", "avg_score": 4.7, "completed_scenarios": 128},
            {"company_id": "kt", "name": "KT", "avg_score": 4.5, "completed_scenarios": 97},
            {"company_id": "shinhan", "name": "신한은행", "avg_score": 4.3, "completed_scenarios": 85},
            {"company_id": "samsung", "name": "삼성전자", "avg_score": 4.2, "completed_scenarios": 112},
            {"company_id": "hyundai", "name": "현대자동차", "avg_score": 4.1, "completed_scenarios": 76},
            {"company_id": "lotte", "name": "롯데마트", "avg_score": 4.0, "completed_scenarios": 63},
            {"company_id": "kb", "name": "KB금융", "avg_score": 3.9, "completed_scenarios": 58},
            {"company_id": "coupang", "name": "쿠팡", "avg_score": 3.8, "completed_scenarios": 91},
        ],
        "user_rankings": [
            {"nickname": "상담의신", "total_score": 458, "avg_score": 4.9, "completed_scenarios": 35},
            {"nickname": "CS마스터", "total_score": 432, "avg_score": 4.8, "completed_scenarios": 30},
            {"nickname": "대화왕", "total_score": 378, "avg_score": 4.7, "completed_scenarios": 27},
            {"nickname": "친절한용성씨", "total_score": 356, "avg_score": 4.6, "completed_scenarios": 26},
            {"nickname": "초보상담사", "total_score": 289, "avg_score": 4.5, "completed_scenarios": 22},
            {"nickname": "서비스킹", "total_score": 267, "avg_score": 4.4, "completed_scenarios": 20},
            {"nickname": "텔레마케터", "total_score": 234, "avg_score": 4.3, "completed_scenarios": 18},
            {"nickname": "매너왕", "total_score": 216, "avg_score": 4.2, "completed_scenarios": 17},
            {"nickname": "전화응대전문가", "total_score": 198, "avg_score": 4.1, "completed_scenarios": 16},
            {"nickname": "친절왕", "total_score": 176, "avg_score": 4.0, "completed_scenarios": 15},
        ],
        "scenario_rankings": [
            {"scenario_id": "complaint_handling", "title": "고객 불만 처리", "avg_score": 4.3, "completed_count": 78},
            {"scenario_id": "product_inquiry", "title": "상품 문의 응대", "avg_score": 4.2, "completed_count": 92},
            {"scenario_id": "service_cancellation", "title": "서비스 해지 방어", "avg_score": 4.0, "completed_count": 63},
            {"scenario_id": "upselling", "title": "상위 상품 판매", "avg_score": 3.9, "completed_count": 54},
            {"scenario_id": "technical_support", "title": "기술 지원", "avg_score": 3.8, "completed_count": 47},
        ],
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

# 탭 설정
tab1, tab2, tab3 = st.tabs(["기업 랭킹", "사용자 랭킹", "시나리오 랭킹"])

# 기업 랭킹 탭
with tab1:
    st.write("<div class='subtitle'>기업별 평균 평가 점수</div>", unsafe_allow_html=True)
    
    # 기업 랭킹 데이터
    company_data = st.session_state.ranking_data["company_rankings"]
    
    # 데이터프레임 변환
    df_companies = pd.DataFrame(company_data)
    
    # 각 기업에 대한 카드 표시
    for i, company in enumerate(company_data):
        # 점수에 따른 색상 결정
        if company["avg_score"] >= 4.5:
            score_color = "#4CAF50"  # 초록색 (매우 좋음)
        elif company["avg_score"] >= 4.0:
            score_color = "#2196F3"  # 파란색 (좋음)
        elif company["avg_score"] >= 3.5:
            score_color = "#FF9800"  # 주황색 (보통)
        else:
            score_color = "#F44336"  # 빨간색 (좋지 않음)
        
        # 별점 표시
        stars = "⭐" * int(company["avg_score"])
        if company["avg_score"] - int(company["avg_score"]) >= 0.5:
            stars += "★"
        
        # 순위 배지 스타일 설정
        badge_style = ""
        if i < 3:  # 상위 3개 회사
            if i == 0:
                badge_style = "background-color: gold; color: #333;"
            elif i == 1:
                badge_style = "background-color: silver; color: #333;"
            elif i == 2:
                badge_style = "background-color: #cd7f32; color: white;"  # Bronze
        else:
            badge_style = "background-color: #f0f0f0; color: #666;"
        
        # 카드 표시
        st.write(f"""
        <div class='scenario-box' style="margin-bottom: 15px; position: relative;">
            <div style="position: absolute; top: -10px; left: -10px; width: 30px; height: 30px; border-radius: 50%; {badge_style} display: flex; justify-content: center; align-items: center; font-weight: bold; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
                {i+1}
            </div>
            <h3 style="margin-left: 20px;">{company["name"]}</h3>
            <div style="display: flex; justify-content: space-between; margin-top: 10px;">
                <div>
                    <p style="font-size: 0.9rem;">완료된 시나리오: <strong>{company["completed_scenarios"]}</strong></p>
                </div>
                <div style="text-align: right;">
                    <p style="font-size: 1.1rem; margin-bottom: 5px;">평균 점수: <span style="color: {score_color}; font-weight: bold;">{company["avg_score"]:.1f}</span></p>
                    <div>{stars}</div>
                </div>
            </div>
            <div style="height: 6px; background-color: #eee; border-radius: 3px; margin-top: 15px;">
                <div style="height: 100%; width: {company['avg_score']*20}%; background-color: {score_color}; border-radius: 3px;"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# 사용자 랭킹 탭
with tab2:
    st.write("<div class='subtitle'>사용자별 평가 점수</div>", unsafe_allow_html=True)
    
    # 사용자 랭킹 데이터
    user_data = st.session_state.ranking_data["user_rankings"]
    
    # 현재 사용자 닉네임
    current_user = st.session_state.get("nickname", "")
    
    # 각 사용자에 대한 카드 표시
    for i, user in enumerate(user_data):
        # 현재 사용자 여부 확인
        is_current_user = user["nickname"] == current_user
        
        # 점수에 따른 색상 결정
        if user["avg_score"] >= 4.5:
            score_color = "#4CAF50"  # 초록색 (매우 좋음)
        elif user["avg_score"] >= 4.0:
            score_color = "#2196F3"  # 파란색 (좋음)
        elif user["avg_score"] >= 3.5:
            score_color = "#FF9800"  # 주황색 (보통)
        else:
            score_color = "#F44336"  # 빨간색 (좋지 않음)
        
        # 카드 스타일 설정
        card_style = "border-left: 4px solid #4CAF50;" if is_current_user else ""
        background_style = "background-color: #f5fff5;" if is_current_user else ""
        
        # 순위 배지 스타일 설정
        badge_style = ""
        if i < 3:  # 상위 3명
            if i == 0:
                badge_style = "background-color: gold; color: #333;"
            elif i == 1:
                badge_style = "background-color: silver; color: #333;"
            elif i == 2:
                badge_style = "background-color: #cd7f32; color: white;"  # Bronze
        else:
            badge_style = "background-color: #f0f0f0; color: #666;"
        
        # 카드 표시
        st.write(f"""
        <div class='company-card' style="{card_style} {background_style} margin-bottom: 15px; position: relative;">
            <div style="position: absolute; top: -10px; left: -10px; width: 30px; height: 30px; border-radius: 50%; {badge_style} display: flex; justify-content: center; align-items: center; font-weight: bold; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
                {i+1}
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <h3 style="margin-left: 20px;">{user["nickname"]}{' (나)' if is_current_user else ''}</h3>
                <div style="text-align: right;">
                    <p style="font-size: 1.1rem; margin-bottom: 5px;">평균 점수: <span style="color: {score_color}; font-weight: bold;">{user["avg_score"]:.1f}</span></p>
                </div>
            </div>
            <div style="display: flex; justify-content: space-between; margin-top: 10px;">
                <div>
                    <p>완료된 시나리오: <strong>{user["completed_scenarios"]}</strong></p>
                    <p>총 점수: <strong>{user["total_score"]}</strong></p>
                </div>
                <div style="text-align: right;">
                    <div style="height: 6px; width: 150px; background-color: #eee; border-radius: 3px; margin-top: 15px;">
                        <div style="height: 100%; width: {user['avg_score']*20}%; background-color: {score_color}; border-radius: 3px;"></div>
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# 시나리오 랭킹 탭
with tab3:
    st.write("<div class='subtitle'>인기 시나리오 순위</div>", unsafe_allow_html=True)
    
    # 시나리오 랭킹 데이터
    scenario_data = st.session_state.ranking_data["scenario_rankings"]
    
    # 각 시나리오에 대한 카드 표시
    for i, scenario in enumerate(scenario_data):
        # 점수에 따른 색상 결정
        if scenario["avg_score"] >= 4.5:
            score_color = "#4CAF50"  # 초록색 (매우 좋음)
        elif scenario["avg_score"] >= 4.0:
            score_color = "#2196F3"  # 파란색 (좋음)
        elif scenario["avg_score"] >= 3.5:
            score_color = "#FF9800"  # 주황색 (보통)
        else:
            score_color = "#F44336"  # 빨간색 (좋지 않음)
        
        # 순위 배지 스타일 설정
        badge_style = ""
        if i < 3:  # 상위 3개 시나리오
            if i == 0:
                badge_style = "background-color: gold; color: #333;"
            elif i == 1:
                badge_style = "background-color: silver; color: #333;"
            elif i == 2:
                badge_style = "background-color: #cd7f32; color: white;"  # Bronze
        else:
            badge_style = "background-color: #f0f0f0; color: #666;"
        
        # 카드 표시
        st.write(f"""
        <div class='scenario-box' style="margin-bottom: 15px; position: relative;">
            <div style="position: absolute; top: -10px; left: -10px; width: 30px; height: 30px; border-radius: 50%; {badge_style} display: flex; justify-content: center; align-items: center; font-weight: bold; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
                {i+1}
            </div>
            <h3 style="margin-left: 20px;">{scenario["title"]}</h3>
            <div style="display: flex; justify-content: space-between; margin-top: 10px;">
                <div>
                    <p>완료된 횟수: <strong>{scenario["completed_count"]}</strong></p>
                </div>
                <div style="text-align: right;">
                    <p style="font-size: 1.1rem; margin-bottom: 5px;">평균 점수: <span style="color: {score_color}; font-weight: bold;">{scenario["avg_score"]:.1f}</span></p>
                    <div style="height: 6px; width: 150px; background-color: #eee; border-radius: 3px; margin-top: 5px;">
                        <div style="height: 100%; width: {scenario['avg_score']*20}%; background-color: {score_color}; border-radius: 3px;"></div>
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# 랭킹 정보
st.write(f"""
<div style="text-align: center; margin-top: 20px; font-size: 0.8rem; color: #666;">
마지막 업데이트: {st.session_state.ranking_data["last_updated"]}
</div>
""", unsafe_allow_html=True)

# 시뮬레이션 버튼
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.button("시뮬레이션 시작하기", use_container_width=True):
        st.session_state.scenario = None
        st.session_state.thread_id = None
        st.session_state.chat_messages = []
        st.session_state.evaluation_result = None
        st.session_state.step = "company_select"
        st.session_state.page = "scenario_select"
        st.rerun()
import streamlit as st
import json
import time
from datetime import datetime

# 기본 페이지 설정
st.set_page_config(layout="wide", page_title="CS 대화 시뮬레이션")

# CSS 스타일 로드 함수
def load_css():
    st.write("""
    <style>
        .main-title {
            font-size: 28px;
            font-weight: bold;
            margin-bottom: 20px;
        }
        .subtitle {
            font-size: 20px;
            font-weight: bold;
            margin: 15px 0;
        }
        .paragraph {
            margin: 10px 0;
        }
        .chat-container {
            height: 400px;
            overflow-y: auto;
            padding: 20px;
            border-radius: 10px;
            background-color: #f9f9f9;
            margin-bottom: 10px;
        }
        .user-message {
            background-color: #dcf8c6;
            padding: 10px;
            border-radius: 10px;
            margin: 5px 0;
            max-width: 80%;
            margin-left: auto;
            word-wrap: break-word;
        }
        .bot-message {
            background-color: #e5e5ea;
            padding: 10px;
            border-radius: 10px;
            margin: 5px 0;
            max-width: 80%;
            word-wrap: break-word;
        }
        .company-card {
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 10px;
            background-color: #f0f2f6;
            border: 1px solid #ddd;
        }
        .company-name {
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 8px;
        }
        .company-desc {
            margin-bottom: 8px;
        }
        .company-info {
            font-size: 14px;
            color: #666;
        }
        .divider {
            height: 1px;
            background-color: #ddd;
            margin: 20px 0;
        }
        .label {
            font-weight: bold;
            margin-right: 5px;
        }
        .scenario-box {
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 20px;
        }
    </style>
    """, unsafe_allow_html=True)

# 세션 상태 초기화 함수
def initialize_session_state():
    if 'page' not in st.session_state:
        st.session_state.page = "login"
    if 'chat_messages' not in st.session_state:
        st.session_state.chat_messages = []
    if 'company' not in st.session_state:
        st.session_state.company = None
    if 'scenario' not in st.session_state:
        st.session_state.scenario = None
    if 'nickname' not in st.session_state:
        st.session_state.nickname = None
    if 'thread_id' not in st.session_state:
        st.session_state.thread_id = None

# 메인 함수
def main():
    # CSS 스타일 로드
    load_css()
    
    # 세션 상태 초기화
    initialize_session_state()
    
    # 타이틀 표시
    st.write("<div class='main-title'>CS 대화 시뮬레이션</div>", unsafe_allow_html=True)
    
    # pages 폴더의 스크립트들이 실행될 것입니다.
    # Streamlit은 pages 폴더의 파일들을 자동으로 사이드바 메뉴로 표시하고 실행합니다.

if __name__ == "__main__":
    main()
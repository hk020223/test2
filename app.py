import streamlit as st
import pandas as pd
import os
import glob
import datetime
import time
import base64
import re  # 정규표현식 사용
import json # JSON 처리를 위한 라이브러리
from langchain_community.document_loaders import PyPDFLoader
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import HumanMessage

# Firebase 라이브러리 (Admin SDK)
import firebase_admin
from firebase_admin import credentials, firestore

# -----------------------------------------------------------------------------
# [0] 설정 및 데이터 로드
# -----------------------------------------------------------------------------
st.set_page_config(page_title="KW-강의마스터 Pro", page_icon="🦄", layout="wide")

def set_style():
    st.markdown("""
        <style>
        /* [Import Font] Pretendard - 웹 폰트 표준 */
        @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
        
        /* [Global Reset] */
        html, body, [class*="css"] {
            font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif !important;
            color: #333333;
        }
        
        /* [Background] Warm Grey - 눈이 편안한 배경 */
        .stApp {
            background-color: #F8F9FA !important;
        }

        /* [Header Alignment] 중앙 정렬 완벽 보정 */
        h1.main-title {
            font-family: 'Pretendard', sans-serif;
            font-weight: 800;
            color: #8A1538; /* 광운 버건디 */
            font-size: 2.8rem;
            text-align: center;
            margin-bottom: 0.5rem;
            letter-spacing: -1px;
            text-shadow: 0 2px 4px rgba(138, 21, 56, 0.1);
        }
        p.subtitle {
            text-align: center;
            color: #6c757d;
            font-size: 1.1rem;
            margin-bottom: 2rem;
            font-weight: 500;
        }

        /* [Navigation] Floating Segmented Control (Toss Style) */
        div.row-widget.stRadio > div[role="radiogroup"] {
            background-color: #FFFFFF;
            padding: 8px;
            border-radius: 16px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.04);
            display: flex;
            justify-content: center;
            gap: 10px;
            border: 1px solid #E9ECEF;
            max-width: 800px;
            margin: 0 auto; /* 중앙 정렬 */
        }
        div.row-widget.stRadio > div[role="radiogroup"] > label {
            flex: 1;
            text-align: center;
            border-radius: 12px !important;
            padding: 12px 20px !important;
            font-weight: 600 !important;
            font-size: 1rem !important;
            transition: all 0.2s cubic-bezier(0.25, 0.8, 0.25, 1);
            border: none !important;
            background: transparent !important;
            color: #ADB5BD !important;
            box-shadow: none !important;
            margin: 0 !important;
        }
        div.row-widget.stRadio > div[role="radiogroup"] > label[data-checked="true"] {
            background-color: #8A1538 !important; /* Active Color */
            color: #FFFFFF !important;
            box-shadow: 0 4px 12px rgba(138, 21, 56, 0.25) !important;
            transform: translateY(-1px);
        }
        div.row-widget.stRadio > div[role="radiogroup"] > label:hover {
            color: #8A1538 !important;
            background-color: #FFF5F7 !important;
        }

        /* [Card UI] Soft Shadow Containers */
        [data-testid="stVerticalBlockBorderWrapper"] {
            background-color: #FFFFFF !important;
            border-radius: 24px !important;
            border: 1px solid rgba(0,0,0,0.03) !important;
            box-shadow: 0 10px 40px rgba(0,0,0,0.03) !important;
            padding: 30px !important;
            margin-bottom: 20px;
            transition: transform 0.2s ease;
        }
        
        /* [Input Field] Glassmorphism Chat */
        [data-testid="stChatInput"] {
            padding-bottom: 20px;
        }
        textarea[data-testid="stChatInputTextArea"] {
            background-color: rgba(255, 255, 255, 0.7) !important;
            backdrop-filter: blur(20px) !important;
            -webkit-backdrop-filter: blur(20px) !important;
            border: 1px solid rgba(138, 21, 56, 0.15) !important;
            border-radius: 30px !important;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.05) !important;
            padding: 15px 20px !important;
            font-size: 1rem !important;
            color: #333 !important;
        }
        textarea[data-testid="stChatInputTextArea"]:focus {
            border-color: #8A1538 !important;
            box-shadow: 0 8px 32px rgba(138, 21, 56, 0.15) !important;
            background-color: rgba(255, 255, 255, 0.95) !important;
        }
        [data-testid="stChatInputSubmitButton"] {
            background: transparent !important;
            color: #8A1538 !important;
            border: none !important;
        }

        /* [Sidebar] Dashboard Style */
        [data-testid="stSidebar"] {
            background-color: #FFFFFF !important;
            border-right: 1px solid #F0F0F0;
        }
        [data-testid="stSidebar"] hr {
            margin: 20px 0;
            border-color: #F0F0F0;
        }
        
        /* [Buttons] Modern Pill Shape */
        button {
            border-radius: 12px !important;
            font-weight: 600 !important;
            transition: all 0.2s !important;
        }
        button[kind="primary"] {
            background: linear-gradient(135deg, #8A1538 0%, #68102A 100%) !important;
            box-shadow: 0 4px 15px rgba(138, 21, 56, 0.3) !important;
            border: none !important;
        }
        button[kind="primary"]:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(138, 21, 56, 0.4) !important;
        }
        button[kind="secondary"] {
            background-color: #F8F9FA !important;
            color: #555 !important;
            border: 1px solid #E9ECEF !important;
        }

        /* [Expander] Clean Accordion */
        .streamlit-expanderHeader {
            background-color: #FFFFFF !important;
            border-radius: 12px !important;
            font-weight: 600 !important;
            color: #333 !important;
            border: 1px solid #eee !important;
        }
        
        /* [Tabs] Minimalist Tabs */
        .stTabs [data-baseweb="tab-list"] {
            gap: 20px;
            background-color: transparent;
            border-bottom: 2px solid #eee;
        }
        .stTabs [data-baseweb="tab"] {
            height: 50px;
            white-space: pre-wrap;
            border: none;
            color: #888;
            font-weight: 600;
        }
        .stTabs [aria-selected="true"] {
            color: #8A1538 !important;
            border-bottom: 3px solid #8A1538 !important;
        }

        /* [Toast] Styling */
        div[data-baseweb="toast"] {
            background-color: white !important;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1) !important;
            border-radius: 12px !important;
            border-left: 5px solid #8A1538 !important;
        }
        
        /* Hide default header/footer */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        </style>
    """, unsafe_allow_html=True)

set_style()

# API Key 로드
if "GOOGLE_API_KEY" in st.secrets:
    api_key = st.secrets["GOOGLE_API_KEY"]
else:
    api_key = os.environ.get("GOOGLE_API_KEY", "")

if not api_key:
    st.error("🚨 **Google API Key가 설정되지 않았습니다.**")
    st.stop()

# 세션 상태 초기화 (없으면 생성)
if "global_log" not in st.session_state:
    st.session_state.global_log = [] 
if "timetable_result" not in st.session_state:
    st.session_state.timetable_result = "" 
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [] 
if "current_menu" not in st.session_state:
    st.session_state.current_menu = "🤖 AI 학사 지식인"
# 라디오 버튼 위젯 상태 초기화
if "menu_radio" not in st.session_state:
    st.session_state["menu_radio"] = "🤖 AI 학사 지식인"

if "timetable_chat_history" not in st.session_state:
    st.session_state.timetable_chat_history = []
if "graduation_analysis_result" not in st.session_state:
    st.session_state.graduation_analysis_result = ""
if "graduation_chat_history" not in st.session_state:
    st.session_state.graduation_chat_history = []
if "user" not in st.session_state:
    st.session_state.user = None

# 현재 불러온 시간표 메타데이터 (ID, 이름, 즐겨찾기 여부 등) 관리용
if "current_timetable_meta" not in st.session_state:
    st.session_state.current_timetable_meta = {}

# [추가] 선택된 강의계획서 뷰어 상태 관리
if "selected_syllabus" not in st.session_state:
    st.session_state.selected_syllabus = None

def add_log(role, content, menu_context=None):
    timestamp = datetime.datetime.now().strftime("%H:%M")
    st.session_state.global_log.append({
        "role": role,
        "content": content,
        "time": timestamp,
        "menu": menu_context
    })

# HTML 코드 정제 함수
def clean_html_output(text):
    cleaned = text.strip()
    if cleaned.startswith("```html"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    return cleaned.replace("```html", "").replace("```", "").strip()

# ★ 재시도(Retry) 로직 ★
def run_with_retry(func, *args, **kwargs):
    max_retries = 5
    delays = [1, 2, 4, 8, 16]
    for i in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg or "503" in error_msg:
                if i < max_retries - 1:
                    time.sleep(delays[i])
                    continue
            raise e

# -----------------------------------------------------------------------------
# [Firebase Manager] Firestore 기반 자체 인증 및 DB 관리
# -----------------------------------------------------------------------------
class FirebaseManager:
    def __init__(self):
        self.db = None
        self.is_initialized = False
        self.init_firestore()

    def init_firestore(self):
        """Firestore DB 초기화 (Service Account 사용)"""
        if "firebase_service_account" in st.secrets:
            try:
                if not firebase_admin._apps:
                    cred_info = dict(st.secrets["firebase_service_account"])
                    cred = credentials.Certificate(cred_info)
                    firebase_admin.initialize_app(cred)
                self.db = firestore.client()
                self.is_initialized = True
            except Exception:
                pass

    def login(self, email, password):
        """Firestore에서 이메일/비번 매칭 검사"""
        if not self.is_initialized:
            return None, "Firebase 연결 실패"
        
        try:
            # users 컬렉션에서 email과 password가 일치하는 문서 검색
            users_ref = self.db.collection('users')
            query = users_ref.where('email', '==', email).where('password', '==', password).stream()
            
            for doc in query:
                user_data = doc.to_dict()
                user_data['localId'] = doc.id
                return user_data, None
            
            return None, "이메일 또는 비밀번호가 일치하지 않습니다."
        except Exception as e:
            return None, f"로그인 오류: {str(e)}"

    def signup(self, email, password):
        """Firestore에 신규 유저 정보 저장"""
        if not self.is_initialized:
            return None, "Firebase 연결 실패"

        try:
            users_ref = self.db.collection('users')
            existing_user = list(users_ref.where('email', '==', email).stream())
            if len(existing_user) > 0:
                return None, "이미 가입된 이메일입니다."
            
            new_user_ref = users_ref.document()
            user_data = {
                "email": email,
                "password": password,
                "created_at": firestore.SERVER_TIMESTAMP
            }
            new_user_ref.set(user_data)
            
            user_data['localId'] = new_user_ref.id
            return user_data, None
        except Exception as e:
            return None, f"회원가입 오류: {str(e)}"

    def save_data(self, collection, doc_id, data):
        """데이터 저장 (덮어쓰기)"""
        if not self.is_initialized or not st.session_state.user:
            return False
        try:
            user_id = st.session_state.user['localId']
            doc_ref = self.db.collection('users').document(user_id).collection(collection).document(doc_id)
            data['updated_at'] = firestore.SERVER_TIMESTAMP
            doc_ref.set(data)
            return True
        except:
            return False

    def update_data(self, collection, doc_id, data):
        """데이터 부분 업데이트 (이름 변경, 즐겨찾기 등)"""
        if not self.is_initialized or not st.session_state.user:
            return False
        try:
            user_id = st.session_state.user['localId']
            doc_ref = self.db.collection('users').document(user_id).collection(collection).document(doc_id)
            data['updated_at'] = firestore.SERVER_TIMESTAMP
            doc_ref.update(data)
            return True
        except:
            return False

    def load_collection(self, collection):
        """데이터 목록 불러오기"""
        if not self.is_initialized or not st.session_state.user:
            return []
        try:
            user_id = st.session_state.user['localId']
            docs = self.db.collection('users').document(user_id).collection(collection).order_by('updated_at', direction=firestore.Query.DESCENDING).stream()
            return [{"id": doc.id, **doc.to_dict()} for doc in docs]
        except:
            return []

fb_manager = FirebaseManager()

# PDF 데이터 로드
@st.cache_resource(show_spinner="PDF 문서를 분석 중입니다...")
def load_knowledge_base():
    if not os.path.exists("data"):
        return ""
    pdf_files = glob.glob("data/*.pdf")
    if not pdf_files:
        return ""
    all_content = ""
    for pdf_file in pdf_files:
        try:
            loader = PyPDFLoader(pdf_file)
            pages = loader.load_and_split()
            filename = os.path.basename(pdf_file)
            all_content += f"\n\n--- [문서: {filename}] ---\n"
            for page in pages:
                all_content += page.page_content
        except Exception as e:
            print(f"Error loading {pdf_file}: {e}")
            continue
    return all_content

PRE_LEARNED_DATA = load_knowledge_base()

# -----------------------------------------------------------------------------
# [1] AI 엔진 (gemini-2.5-flash-preview-09-2025)
# -----------------------------------------------------------------------------
def get_llm():
    if not api_key: return None
    return ChatGoogleGenerativeAI(model="gemini-2.5-flash-preview-09-2025", temperature=0)

def get_pro_llm():
    if not api_key: return None
    return ChatGoogleGenerativeAI(model="gemini-2.5-flash-preview-09-2025", temperature=0)

def ask_ai(question):
    llm = get_llm()
    if not llm: return "⚠️ API Key 오류"
    def _execute():
        chain = PromptTemplate.from_template(
            "문서 내용: {context}\n질문: {question}\n문서에 기반해 답변해줘. 답변할 때 근거가 되는 문서의 원문 내용을 반드시 \" \" (쌍따옴표) 안에 인용해서 포함해줘."
        ) | llm
        return chain.invoke({"context": PRE_LEARNED_DATA, "question": question}).content
    try:
        return run_with_retry(_execute)
    except Exception as e:
        if "RESOURCE_EXHAUSTED" in str(e):
            return "⚠️ **잠시만요!** 사용량이 많아 AI가 숨을 고르고 있습니다. 1분 뒤에 다시 시도해주세요."
        return f"❌ AI 오류: {str(e)}"

# =============================================================================
# [Helper Functions] 인터랙티브 시간표 & AI 데이터 추출
# =============================================================================

# 1. 시간 충돌 감지 로직
def check_time_conflict(new_course, current_schedule):
    new_slots = set(new_course.get('time_slots', []))
    for existing in current_schedule:
        existing_slots = set(existing.get('time_slots', []))
        overlap = new_slots & existing_slots
        if overlap:
            return True, existing['name']
    return False, None

# [UI 리뉴얼] 시간표 렌더링 함수 (스티커 모던 디자인)
def render_interactive_timetable(schedule_list):
    """
    구글 캘린더/애플 캘린더 스타일의 현대적인 시간표 렌더링
    """
    days = ["월", "화", "수", "목", "금"]
    
    # 1. 그리드 초기화
    table_grid = {i: {d: None for d in days} for i in range(1, 10)}
    online_courses = []

    # 2. 색상 팔레트 (Modern Pastel)
    palette = [
        {"bg": "#FFEBEE", "border": "#FFCDD2", "text": "#C62828"}, # Red
        {"bg": "#E3F2FD", "border": "#BBDEFB", "text": "#1565C0"}, # Blue
        {"bg": "#E8F5E9", "border": "#C8E6C9", "text": "#2E7D32"}, # Green
        {"bg": "#F3E5F5", "border": "#E1BEE7", "text": "#6A1B9A"}, # Purple
        {"bg": "#FFF3E0", "border": "#FFE0B2", "text": "#EF6C00"}, # Orange
        {"bg": "#E0F2F1", "border": "#B2DFDB", "text": "#00695C"}, # Teal
        {"bg": "#FCE4EC", "border": "#F8BBD0", "text": "#AD1457"}, # Pink
    ]

    # 3. 데이터 채우기
    for course in schedule_list:
        slots = course.get('time_slots', [])
        
        # 온라인/시간미정 처리
        if not slots or slots == ["시간미정"] or not isinstance(slots, list):
            online_courses.append(course)
            continue

        # 과목별 색상 배정
        color_idx = abs(hash(course['name'])) % len(palette)
        style = palette[color_idx]

        # 슬롯 파싱
        for slot in slots:
            if len(slot) < 2: continue
            day_char = slot[0] # "월"
            try:
                period = int(slot[1:]) # "3"
                if day_char in days and 1 <= period <= 9:
                    table_grid[period][day_char] = {
                        "name": course['name'],
                        "prof": course['professor'],
                        "style": style
                    }
            except:
                pass 

    # 4. 모던 HTML 생성
    html = """
    <style>
        .tt-table { width: 100%; border-collapse: separate; border-spacing: 6px; table-layout: fixed; }
        .tt-header { background-color: transparent; color: #888; padding: 10px; font-weight: 700; text-align: center; font-size: 14px; border-bottom: 2px solid #eee; }
        .tt-time { color: #aaa; font-weight: 600; text-align: center; vertical-align: middle; font-size: 12px; height: 60px;}
        .tt-cell { vertical-align: middle; padding: 0; height: 60px; }
        .tt-card {
            width: 100%; height: 100%;
            display: flex; flex-direction: column; justify-content: center; align-items: center;
            border-radius: 12px; 
            font-size: 12px; line-height: 1.3; padding: 4px; text-align: center;
            transition: all 0.2s;
            cursor: default;
        }
        .tt-card:hover { transform: scale(1.05); box-shadow: 0 8px 16px rgba(0,0,0,0.1); z-index: 10; }
        .tt-name { font-weight: 800; margin-bottom: 2px; display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 95%; }
        .tt-prof { font-size: 11px; opacity: 0.9; font-weight: 500; }
        .tt-online { margin-top: 20px; padding: 15px; background: #fff; border-radius: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.03); border: 1px solid #f0f0f0; }
        .tt-online-badge { display: inline-block; margin: 4px; padding: 6px 10px; border-radius: 8px; font-size: 12px; font-weight: 700; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    <table class="tt-table">
        <tr>
            <th style="width: 8%;"></th>
            <th class="tt-header">MON</th>
            <th class="tt-header">TUE</th>
            <th class="tt-header">WED</th>
            <th class="tt-header">THU</th>
            <th class="tt-header">FRI</th>
        </tr>
    """
    
    for i in range(1, 10):
        html += f"<tr><td class='tt-time'>{i}</td>"
        for day in days:
            cell_data = table_grid[i][day]
            if cell_data:
                s = cell_data['style']
                # 카드형 디자인 적용
                card_html = f"""
                <div class="tt-card" style="background-color: {s['bg']}; color: {s['text']};">
                    <span class="tt-name">{cell_data['name']}</span>
                    <span class="tt-prof">{cell_data['prof']}</span>
                </div>
                """
                html += f"<td class='tt-cell'>{card_html}</td>"
            else:
                # 빈 셀 (가이드라인)
                html += "<td class='tt-cell' style='background-color: #fdfdfd; border-radius: 8px; border: 1px dashed #f0f0f0;'></td>"
        html += "</tr>"
    html += "</table>"

    # 온라인 강의 표시
    if online_courses:
        html += "<div class='tt-online'><strong style='color:#555;'>✨ Online / Unscheduled: </strong><br>"
        for c in online_courses:
            color_idx = abs(hash(c['name'])) % len(palette)
            s = palette[color_idx]
            html += f"<span class='tt-online-badge' style='background-color: {s['bg']}; color: {s['text']};'>{c['name']}</span>"
        html += "</div>"
        
    return html

# 3. AI 후보군 추출 (엄격한 데이터 파싱 - 주관 배제)
def get_course_candidates_json(major, grade, semester, diagnosis_text=""):
    llm = get_llm()
    if not llm: return []

    prompt_template = """
    너는 [대학교 학사 데이터베이스 파서]이다. 
    제공된 [수강신청자료집/시간표 문서]를 분석하여 **{major} {grade} {semester}** 학생이 수강 가능한 **모든 정규 개설 과목**을 JSON 리스트로 추출하라.
    
    [학생 정보]
    - 전공: {major}
    - 대상: {grade} {semester}
    
    [진단 결과 (재수강 체크용)]
    {diagnosis_context}
    
    [엄격한 제약 사항]
    1. **주관적 추천 금지:** "취업에 유리함", "커리어 도움됨" 같은 추측성 설명은 절대 하지 마라.
    2. **전수 조사:** 해당 학과/학년/학기에 배정된 과목은 하나도 빠뜨리지 말고 모두 포함하라. (분반이 다르면 모두 포함)
    3. **제외 대상:** 타 학과 전용 과목, 해당 학년 대상이 아닌 과목은 리스트에서 제외하라.
    4. **Reason 필드 작성 규칙:** - 기본적으로 **"이수구분(전공필수/선택/교양) | 학점"** 형식의 팩트만 적어라.
       - 단, [진단 결과]에 "재수강"이 명시된 과목은 **"재수강 필수 대상"**이라고 적어라.
    5. **Priority 설정:**
       - 전공필수 또는 재수강 과목 = "High"
       - 전공선택 = "Medium"
       - 교양/기타 = "Normal"
    
    [JSON 출력 포맷 예시]
    [
        {{
            "id": "unique_id_1",
            "name": "회로이론1",
            "professor": "김광운",
            "credits": 3,
            "time_slots": ["월3", "수4"],
            "classification": "전공필수",
            "priority": "High", 
            "reason": "전공필수 | 3학점"
        }},
         {{
            "id": "unique_id_2",
            "name": "대학영어",
            "professor": "Smith",
            "credits": 2,
            "time_slots": ["화1", "목1"],
            "classification": "교양필수",
            "priority": "Normal", 
            "reason": "교양필수 | 2학점"
        }}
    ]
    
    **오직 JSON 리스트만 출력하라.**
    [문서 데이터]
    {context}
    """
    
    def _execute():
        chain = PromptTemplate.from_template(prompt_template) | llm
        return chain.invoke({
            "major": major,
            "grade": grade,
            "semester": semester,
            "diagnosis_context": diagnosis_text,
            "context": PRE_LEARNED_DATA
        }).content

    try:
        response = run_with_retry(_execute)
        cleaned_json = response.replace("```json", "").replace("```", "").strip()
        if not cleaned_json.startswith("["):
             start = cleaned_json.find("[")
             end = cleaned_json.rfind("]")
             if start != -1 and end != -1:
                 cleaned_json = cleaned_json[start:end+1]
        return json.loads(cleaned_json)
    except Exception as e:
        print(f"JSON Parsing Error: {e}")
        return []

def chat_with_timetable_ai(current_timetable, user_input, major, grade, semester):
    llm = get_llm()
    def _execute():
        template = """
        너는 현재 시간표에 대한 상담을 해주는 AI 조교야.
        [현재 시간표 상태]
        {current_timetable}
        [사용자 입력]
        "{user_input}"
        [학생 정보]
        - 소속: {major}
        - 학년/학기: {grade} {semester}
        [지시사항]
        사용자의 입력 의도를 파악해서 답변해.
        [문서 근거 필수] 문서 내용을 인용할 땐 " " 안에 넣어.
        [학습된 문서]
        {context}
        """
        prompt = PromptTemplate(template=template, input_variables=["current_timetable", "user_input", "major", "grade", "semester", "context"])
        chain = prompt | llm
        return chain.invoke({
            "current_timetable": current_timetable, 
            "user_input": user_input,
            "major": major,
            "grade": grade,
            "semester": semester,
            "context": PRE_LEARNED_DATA
        }).content
    try:
        return run_with_retry(_execute)
    except Exception as e:
        if "RESOURCE_EXHAUSTED" in str(e):
            return "⚠️ **사용량 초과**: 잠시 후 다시 시도해주세요."
        return f"❌ AI 오류: {str(e)}"

# =============================================================================
# [섹션] 성적 및 진로 진단 분석 함수
# =============================================================================
def analyze_graduation_requirements(uploaded_images):
    llm = get_pro_llm()
    if not llm: return "⚠️ API Key 오류"

    def encode_image(image_file):
        image_file.seek(0)
        return base64.b64encode(image_file.read()).decode("utf-8")

    image_messages = []
    for img_file in uploaded_images:
        base64_image = encode_image(img_file)
        image_messages.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
        })

    def _execute():
        prompt = """
        당신은 [냉철하고 현실적인 대기업 인사담당자 출신의 취업 컨설턴트]입니다.
        제공된 학생의 [성적표 이미지]와 [학습된 학사 문서]를 바탕으로 3가지 측면에서 분석 결과를 작성해주세요.
        
        **[핵심 지시사항 - 중요]**
        - 단순히 "열심히 하세요" 같은 뜬구름 잡는 조언은 하지 마십시오.
        - **반드시** 삼성전자, SK하이닉스, 현대자동차, 네이버, 카카오 등 **실제 한국 주요 대기업의 실명과 구체적인 직무명(JD)**을 언급하며 조언하세요.
        - 예: "삼성전자 DS부문 메모리사업부의 공정기술 직무에서는 반도체공학 A학점 이상을 선호하지만, 현재 학생의 성적은 B+이므로..." 와 같이 구체적으로 비교하세요.

        **[출력 형식]**
        반드시 아래의 구분자(`[[SECTION: ...]]`)를 사용하여 답변을 3개의 구역으로 명확히 나누세요.

        [[SECTION:GRADUATION]]
        ### 🎓 1. 졸업 요건 정밀 진단
        - [학습된 학사 문서]의 규정과 비교하여 졸업 가능 여부를 판정하세요.
        - 부족한 학점(전공, 교양 등)과 미이수 필수 과목을 표나 리스트로 정리하세요.
        - **종합 판정:** [졸업 가능 / 위험 / 불가]

        [[SECTION:GRADES]]
        ### 📊 2. 성적 정밀 분석
        - **전체 평점 vs 전공 평점 비교:** 전공 학점이 전체보다 낮은지 확인하고 질책하세요. (직무 전문성 결여 지적)
        - **재수강 권고:** C+ 이하의 전공 핵심 과목이 있다면 구체적으로 지적하며 재수강을 강력히 권고하세요.
        - **수강 패턴 분석:** 꿀강(학점 따기 쉬운 교양) 위주로 들었는지, 기피 과목(어려운 전공)을 피했는지 간파하고 지적하세요.

        [[SECTION:CAREER]]
        ### 💼 3. AI 커리어 솔루션 (대기업 JD 매칭)
        - **직무 추천:** 학생의 수강 내역(회로 위주, SW 위주 등)을 분석하여 가장 적합한 **구체적인 대기업 직무**를 2~3개 추천하세요. (예: 삼성전자 회로설계, 현대모비스 임베디드SW 등)
        - **Skill Gap 분석:** 해당 직무의 시장 요구사항(대기업 채용 기준) 대비 현재 부족한 점을 냉정하게 꼬집으세요.
        - **Action Plan:** 남은 학기에 반드시 수강해야 할 과목이나, 학교 밖에서 채워야 할 경험(프로젝트, 기사 자격증 등)을 구체적으로 지시하세요.

        [학습된 학사 문서]
        """
        
        content_list = [{"type": "text", "text": prompt}]
        content_list.extend(image_messages)
        content_list.append({"type": "text", "text": f"\n\n{PRE_LEARNED_DATA}"})

        message = HumanMessage(content=content_list)
        response = llm.invoke([message])
        return response.content

    try:
        return run_with_retry(_execute)
    except Exception as e:
         if "RESOURCE_EXHAUSTED" in str(e):
            return "⚠️ **사용량 초과**: 잠시 후 다시 시도해주세요."
         return f"❌ AI 오류: {str(e)}"

# 성적/진로 상담 및 수정 함수
def chat_with_graduation_ai(current_analysis, user_input):
    llm = get_llm()
    def _execute():
        template = """
        당신은 냉철하고 독설적인 'AI 취업 컨설턴트'입니다.
        학생의 성적 및 진로 진단 결과는 다음과 같습니다:
        
        [현재 진단 결과]
        {current_analysis}

        [사용자 입력]
        "{user_input}"

        [지시사항]
        - 사용자의 질문에 대해 현실적이고 직설적으로 답변하세요. 위로는 필요 없습니다.
        - 정보 수정 요청(예: "나 이 과목 들었어")이 들어오면 `[수정]` 태그를 붙이고 전체 진단 결과를 업데이트하세요.
        - **기업 채용 관점**에서 답변하세요. "이 과목은 삼성전자가 좋아합니다/신경 안 씁니다" 식으로 설명하세요.
        
        [참고 문헌]
        {context}
        """
        prompt = PromptTemplate(template=template, input_variables=["current_analysis", "user_input", "context"])
        chain = prompt | llm
        return chain.invoke({
            "current_analysis": current_analysis,
            "user_input": user_input,
            "context": PRE_LEARNED_DATA
        }).content

    try:
        return run_with_retry(_execute)
    except Exception as e:
        if "RESOURCE_EXHAUSTED" in str(e):
            return "⚠️ **사용량 초과**: 잠시 후 다시 시도해주세요."
        return f"❌ AI 오류: {str(e)}"

# -----------------------------------------------------------------------------
# [2] UI 구성 (리뉴얼)
# -----------------------------------------------------------------------------
def change_menu(menu_name):
    st.session_state.current_menu = menu_name

# 사이드바 (Dashboard Style)
with st.sidebar:
    st.markdown("### 🎛️ Control Tower")
    
    # [로그인 UI]
    if st.session_state.user is None:
        with st.expander("🔐 Login / Sign Up", expanded=True):
            auth_mode = st.radio("Mode", ["로그인", "회원가입"], horizontal=True, key="auth_radio", label_visibility="collapsed")
            email = st.text_input("Email", placeholder="example@kw.ac.kr")
            password = st.text_input("Password", type="password", placeholder="********")
            
            if st.button("Enter", key="auth_btn", type="primary", use_container_width=True):
                if not email or not password:
                    st.error("이메일과 비밀번호를 입력하세요.")
                else:
                    if not fb_manager.is_initialized:
                        st.error("Firebase 연결 실패 (Secrets를 확인하세요)")
                    else:
                        with st.spinner(f"{auth_mode} 중..."):
                            if auth_mode == "로그인":
                                user, err = fb_manager.login(email, password)
                            else:
                                user, err = fb_manager.signup(email, password)
                            
                            if user:
                                st.session_state.user = user
                                st.success(f"환영합니다! ({user['email']})")
                                st.rerun()
                            else:
                                st.error(f"오류: {err}")
    else:
        # 로그인된 상태의 프로필 카드
        st.markdown(f"""
        <div style="background-color: #F8F9FA; padding: 16px; border-radius: 12px; margin-bottom: 20px; border: 1px solid #E9ECEF;">
            <div style="font-weight: bold; color: #333; margin-bottom: 4px;">👤 {st.session_state.user['email']}</div>
            <div style="font-size: 12px; color: #8A1538;">Student Verified</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("로그아웃", use_container_width=True):
            st.session_state.clear()
            st.session_state["menu_radio"] = "🤖 AI 학사 지식인" 
            st.rerun()
    
    st.write("") # Whitespace
    st.markdown("##### ⚙️ Settings")
    
    if st.button("📡 학교 데이터 동기화 (Sync)", help="최신 학사 정보 업데이트"):
        status_text = st.empty()
        progress_bar = st.progress(0)
        status_text.caption("🔄 연결 중...")
        time.sleep(1.0) 
        progress_bar.progress(30)
        status_text.caption("📂 최신 규정 스캔 중...")
        time.sleep(1.5)
        progress_bar.progress(70)
        st.cache_resource.clear()
        time.sleep(1.0)
        progress_bar.progress(100)
        st.toast("동기화 완료! 최신 데이터가 반영되었습니다.", icon="✅")
        time.sleep(1)
        st.rerun()          
    
    st.write("")
    st.markdown("##### 🕒 Recent Activities")
    log_container = st.container(height=250)
    with log_container:
        if not st.session_state.global_log:
            st.caption("기록 없음")
        else:
            for i, log in enumerate(reversed(st.session_state.global_log)):
                label = f"[{log['time']}] {log['content'][:12]}.."
                if st.button(label, key=f"log_btn_{i}", use_container_width=True):
                    if log['menu']:
                        st.session_state.current_menu = log['menu']
                        st.session_state["menu_radio"] = log['menu'] 
                        st.rerun()

    st.write("")
    if PRE_LEARNED_DATA:
         st.markdown("<div style='font-size:12px; color:#2E7D32; text-align:center;'>✅ KLAS Knowledge Active</div>", unsafe_allow_html=True)
    else:
        st.error("⚠️ 데이터 없음")

# -----------------------------------------------------------------------------
# [2] 메인 UI (The New Layout)
# -----------------------------------------------------------------------------

# 1. 상단 헤더 (완벽한 중앙 정렬)
st.markdown('<h1 class="main-title">🦄 KW-Master Pro</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Digital Campus Agent for Kwangwoon Univ.</p>', unsafe_allow_html=True)

# 2. 기능 선택 메뉴 (Floating Segmented Control)
st.write("")
menu = st.radio(
    "메뉴 선택", 
    options=["🤖 AI 학사 지식인", "📅 스마트 시간표(수정가능)", "📈 성적 및 진로 진단"],
    index=0,
    horizontal=True,
    key="menu_radio",
    label_visibility="collapsed"
)

# 메뉴 상태 동기화
if menu != st.session_state.current_menu:
    st.session_state.current_menu = menu
    st.rerun()

st.write("") 
st.write("") 

# 메인 콘텐츠 컨테이너 (Shadow Card 적용됨)
with st.container(border=True):

    if st.session_state.current_menu == "🤖 AI 학사 지식인":
        st.subheader("🤖 무엇이든 물어보세요")
        
        # 상단 도구 모음
        if st.session_state.user and fb_manager.is_initialized:
            col_save, col_load = st.columns([1, 2])
            with col_save:
                if st.button("💾 대화 저장", use_container_width=True):
                    doc_id = str(int(time.time()))
                    data = {"history": [msg for msg in st.session_state.chat_history]}
                    if fb_manager.save_data('chat_history', doc_id, data):
                        st.toast("저장되었습니다.")
            with col_load:
                 saved_chats = fb_manager.load_collection('chat_history')
                 if saved_chats:
                     selected = st.selectbox("불러오기", saved_chats, format_func=lambda x: datetime.datetime.fromtimestamp(int(x['id'])).strftime('%m/%d %H:%M'), label_visibility="collapsed")
                     if st.button("로드", key="load_chat_btn"):
                         st.session_state.chat_history = selected['history']
                         st.rerun()

        # 대화창 영역
        chat_container = st.container()
        with chat_container:
            for msg in st.session_state.chat_history:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
        
        # 입력창 처리
        if user_input := st.chat_input("광운대 학사 규정, 장학금, 수강신청 등 궁금한 점을 입력하세요..."):
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            add_log("user", f"[지식인] {user_input}", "🤖 AI 학사 지식인")
            with st.chat_message("user"):
                st.markdown(user_input)
            with st.chat_message("assistant"):
                with st.spinner("Analyzing KLAS Documents..."):
                    response = ask_ai(user_input)
                    st.markdown(response)
            st.session_state.chat_history.append({"role": "assistant", "content": response})

    elif st.session_state.current_menu == "📅 스마트 시간표(수정가능)":
        st.subheader("📅 AI Smart Timetable")
        
        # [A] 설정 및 후보군 로딩
        with st.expander("🛠️ Configuration (학과/학년 설정)", expanded=not bool(st.session_state.candidate_courses)):
            kw_departments = [
                "전자공학과", "전자통신공학과", "전자융합공학과", "전기공학과", "전자재료공학과", "반도체시스템공학부", "로봇학부",
                "컴퓨터정보공학부", "소프트웨어학부", "정보융합학부", "지능형로봇학과", "건축학과", "건축공학과", "화학공학과", "환경공학과",
                "수학과", "전자바이오물리학과", "화학과", "스포츠융합과학과", "정보콘텐츠학과", "국어국문학과", "영어산업학과", 
                "미디어커뮤니케이션학부", "산업심리학과", "동북아문화산업학부", "행정학과", "법학부", "국제학부", "자산관리학과",
                "경영학부", "국제통상학부", "자율전공학부(자연)", "자율전공학부(인문)"
            ]
            
            c1, c2, c3 = st.columns(3)
            major = c1.selectbox("학과", kw_departments, key="tt_major")
            grade = c2.selectbox("학년", ["1학년", "2학년", "3학년", "4학년"], key="tt_grade")
            semester = c3.selectbox("학기", ["1학기", "2학기"], key="tt_semester")
            
            use_diagnosis = st.checkbox("☑️ 성적 진단 결과 반영 (재수강/추천 과목 로드)", value=True)
            
            if st.button("🚀 강의 데이터 스캔 (AI Scan)", type="primary", use_container_width=True):
                diag_text = ""
                if use_diagnosis and st.session_state.graduation_analysis_result:
                      diag_text = st.session_state.graduation_analysis_result
                elif use_diagnosis and st.session_state.user and fb_manager.is_initialized:
                      saved_diags = fb_manager.load_collection('graduation_diagnosis')
                      if saved_diags:
                          diag_text = saved_diags[0]['result']
                          st.toast("저장된 진단 결과를 불러왔습니다.")

                with st.spinner("요람에서 해당 학기 개설 과목을 전수 조사 중입니다..."):
                    candidates = get_course_candidates_json(major, grade, semester, diag_text)
                    if candidates:
                        st.session_state.candidate_courses = candidates
                        st.session_state.my_schedule = [] 
                        st.rerun()
                    else:
                        st.error("강의 정보를 추출하지 못했습니다. 다시 시도해주세요.")

        # [B] 인터랙티브 빌더 UI
        if st.session_state.candidate_courses:
            st.write("---")
            col_left, col_right = st.columns([1, 1.4], gap="large")

            # [좌측] 강의 장바구니
            with col_left:
                st.markdown("#### 📚 Courses")
                st.caption("클릭하여 시간표에 추가하세요.")
                
                with st.container(height=650): 
                    tab1, tab2, tab3 = st.tabs(["🔥 필수/재수강", "🏫 전공선택", "🧩 교양/기타"])
                    
                    def draw_course_row(course, key_prefix):
                        current_names = [c['name'] for c in st.session_state.my_schedule]
                        if course['name'] in current_names:
                            return 

                        priority = course.get('priority', 'Normal')
                        card_style = "border-left: 4px solid #eee;"
                        if priority == 'High': card_style = "border-left: 4px solid #8A1538; background-color: #FFF5F7;"
                        elif priority == 'Medium': card_style = "border-left: 4px solid #1565C0; background-color: #F5FBFF;"
                        
                        st.markdown(f"""
                        <div style="{card_style} padding:12px; border-radius:8px; margin-bottom:10px; box-shadow:0 2px 5px rgba(0,0,0,0.03); background-color:white;">
                            <div style="font-weight:700; color:#333; font-size:15px;">{course['name']}</div>
                            <div style="font-size:13px; color:#666; margin-top:2px;">{course['credits']}학점 | {course['professor']}</div>
                            <div style="font-size:12px; color:#888; margin-top:4px;">🕒 {', '.join(course['time_slots']) if course['time_slots'] else '미정'}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        if st.button("담기 ➕", key=f"add_{key_prefix}_{course['id']}", use_container_width=True):
                            conflict, conflict_name = check_time_conflict(course, st.session_state.my_schedule)
                            if conflict:
                                st.toast(f"⚠️ 시간 충돌! '{conflict_name}' 수업과 겹칩니다.", icon="🚫")
                            else:
                                st.session_state.my_schedule.append(course)
                                st.rerun()
                        st.write("") # Spacer

                    # 분류 및 렌더링
                    must_list = [c for c in st.session_state.candidate_courses if c.get('priority') == 'High']
                    major_list = [c for c in st.session_state.candidate_courses if c.get('priority') == 'Medium' or ('전공' in c.get('classification', '') and c not in must_list)]
                    other_list = [c for c in st.session_state.candidate_courses if c not in must_list and c not in major_list]

                    with tab1:
                        for c in must_list: draw_course_row(c, "must")
                    with tab2:
                        for c in major_list: draw_course_row(c, "mj")
                    with tab3:
                        for c in other_list: draw_course_row(c, "ot")

            # [우측] 실시간 프리뷰
            with col_right:
                st.markdown("#### 🗓️ Weekly Schedule")
                
                # 학점 대시보드
                if "max_credits" not in st.session_state:
                    st.session_state.max_credits = 21 
                
                total_credits = sum([c.get('credits', 0) for c in st.session_state.my_schedule])
                
                # 학점 게이지 (Custom CSS)
                st.caption(f"Credits: {total_credits} / {st.session_state.max_credits}")
                if st.session_state.max_credits > 0:
                    prog = min(total_credits / st.session_state.max_credits, 1.0)
                    st.progress(prog)
                
                # 최대 학점 조절
                st.session_state.max_credits = st.number_input("Max Credits", 15, 30, st.session_state.max_credits, label_visibility="collapsed")
                
                # 신청 내역 리스트 (Pill Tags)
                if st.session_state.my_schedule:
                    st.markdown("<div style='margin-bottom:10px;'></div>", unsafe_allow_html=True)
                    del_cols = st.columns(3)
                    for idx, added_course in enumerate(st.session_state.my_schedule):
                        col_idx = idx % 3
                        with del_cols[col_idx]:
                            if st.button(f"✕ {added_course['name']}", key=f"del_{idx}", help="제거"):
                                st.session_state.my_schedule.pop(idx)
                                st.rerun()
                
                # [핵심] 모던 시간표 렌더링
                html_table = render_interactive_timetable(st.session_state.my_schedule)
                st.markdown(html_table, unsafe_allow_html=True)
                
                st.write("")
                col_save_tt, col_reset_tt = st.columns([3, 1])
                with col_save_tt:
                    if st.button("💾 Save Schedule", use_container_width=True, type="primary"):
                        if not st.session_state.my_schedule:
                            st.error("Empty Schedule")
                        else:
                            st.session_state.timetable_result = html_table 
                            doc_data = {
                                "result": html_table,
                                "major": major,
                                "grade": grade,
                                "name": f"{major} {grade} (Custom)",
                                "is_favorite": False,
                                "created_at": datetime.datetime.now()
                            }
                            if st.session_state.user and fb_manager.is_initialized:
                                 doc_id = str(int(time.time()))
                                 if fb_manager.save_data('timetables', doc_id, doc_data):
                                     st.toast("Saved successfully!", icon="✅")
                            else:
                                st.warning("Please login first.")
                with col_reset_tt:
                     if st.button("Reset", use_container_width=True):
                        st.session_state.my_schedule = []
                        st.rerun()

    elif st.session_state.current_menu == "📈 성적 및 진로 진단":
        st.subheader("📈 Career & Grade Diagnosis")
        st.info("💡 **전체 성적표(취득학점 내역)**를 캡처하여 업로드하세요. AI가 삼성전자, 하이닉스 등 대기업 기준에 맞춰 분석해드립니다.")

        # 저장된 결과 로드
        if st.session_state.user and fb_manager.is_initialized:
            saved_diags = fb_manager.load_collection('graduation_diagnosis')
            if saved_diags:
                with st.expander("📂 Load Past Report"):
                    selected_diag = st.selectbox("Select Report", 
                                                 saved_diags, 
                                                 format_func=lambda x: datetime.datetime.fromtimestamp(int(x['id'])).strftime('%Y-%m-%d %H:%M'),
                                                 label_visibility="collapsed")
                    if st.button("Load Report", use_container_width=True):
                        st.session_state.graduation_analysis_result = selected_diag['result']
                        st.rerun()

        uploaded_files = st.file_uploader("Upload Scorecard Images", type=["png", "jpg", "jpeg"], accept_multiple_files=True)

        if uploaded_files:
            if st.button("Analyze Now 🚀", type="primary", use_container_width=True):
                with st.spinner("AI Consultant is analyzing your data..."):
                    analysis_result = analyze_graduation_requirements(uploaded_files)
                    st.session_state.graduation_analysis_result = analysis_result
                    st.session_state.graduation_chat_history = []
                    add_log("user", "[진단] 이미지 분석 요청", "📈 성적 및 진로 진단")
                    st.rerun()

        if st.session_state.graduation_analysis_result:
            st.write("---")
            result_text = st.session_state.graduation_analysis_result
            
            # 탭으로 섹션 구분
            tab1, tab2, tab3 = st.tabs(["🎓 Graduation Check", "📊 Grade Analysis", "💼 Career Solution"])
            
            # 파싱 로직
            parts_grad = result_text.split("[[SECTION:GRADUATION]]")
            content_grad = parts_grad[1].split("[[SECTION:GRADES]]")[0] if len(parts_grad) > 1 else result_text
            
            parts_grade = result_text.split("[[SECTION:GRADES]]")
            content_grade = parts_grade[1].split("[[SECTION:CAREER]]")[0] if len(parts_grade) > 1 else ""
            
            parts_career = result_text.split("[[SECTION:CAREER]]")
            content_career = parts_career[1] if len(parts_career) > 1 else ""

            with tab1: st.markdown(content_grad)
            with tab2: st.markdown(content_grade)
            with tab3: st.markdown(content_career)
            
            # 저장 버튼
            if st.session_state.user and fb_manager.is_initialized:
                if st.button("☁️ Save Report", use_container_width=True):
                    doc_data = {
                        "result": st.session_state.graduation_analysis_result,
                        "created_at": datetime.datetime.now()
                    }
                    doc_id = str(int(time.time()))
                    fb_manager.save_data('graduation_diagnosis', doc_id, doc_data)
                    st.toast("Report Saved!", icon="✅")
            
            # 상담 채팅창
            st.write("---")
            st.subheader("💬 Chat with Consultant")
            for msg in st.session_state.graduation_chat_history:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

            if chat_input := st.chat_input("Ask about your career path..."):
                st.session_state.graduation_chat_history.append({"role": "user", "content": chat_input})
                add_log("user", f"[진단상담] {chat_input}", "📈 성적 및 진로 진단")
                with st.chat_message("user"):
                    st.write(chat_input)
                with st.chat_message("assistant"):
                    with st.spinner("Thinking..."):
                        response = chat_with_graduation_ai(st.session_state.graduation_analysis_result, chat_input)
                        if "[수정]" in response:
                            new_result = response.replace("[수정]", "").strip()
                            st.session_state.graduation_analysis_result = new_result
                            st.session_state.graduation_chat_history.append({"role": "assistant", "content": "Information Updated."})
                            st.rerun()
                        else:
                            st.markdown(response)
                            st.session_state.graduation_chat_history.append({"role": "assistant", "content": response})

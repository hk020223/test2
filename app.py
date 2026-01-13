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
# [0] 설정 및 초기화
# -----------------------------------------------------------------------------
st.set_page_config(page_title="KW-강의마스터 Pro", page_icon="🦄", layout="wide")

# Session State 초기화
if "candidate_courses" not in st.session_state:
    st.session_state.candidate_courses = []
if "my_schedule" not in st.session_state:
    st.session_state.my_schedule = []
if "global_log" not in st.session_state:
    st.session_state.global_log = [] 
if "timetable_result" not in st.session_state:
    st.session_state.timetable_result = "" 
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [] 
if "current_menu" not in st.session_state:
    st.session_state.current_menu = "🤖 AI 학사 지식인"
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
if "current_timetable_meta" not in st.session_state:
    st.session_state.current_timetable_meta = {}
if "selected_syllabus" not in st.session_state:
    st.session_state.selected_syllabus = None

def set_style():
    st.markdown("""
        <style>
        @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
        
        html, body, [class*="css"] {
            font-family: 'Pretendard', sans-serif !important;
            color: #333333;
        }
        
        /* [Background] */
        .stApp {
            background: linear-gradient(135deg, #F9FAFB 0%, #F3F0F5 100%) !important;
            background-attachment: fixed !important;
        }
        
        /* [Header] */
        h1.main-title {
            font-weight: 800; color: #8A1538; font-size: 2.5rem; text-align: center;
            margin-bottom: 0.2rem; letter-spacing: -1.5px;
            background: -webkit-linear-gradient(45deg, #8A1538, #C2185B);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        }
        p.subtitle {
            text-align: center; color: #666; font-size: 1.0rem; margin-bottom: 2rem;
        }

        /* [Sticky Right Column] 핵심: 오른쪽 컬럼 고정 */
        /* Streamlit의 두 번째 컬럼(div)를 타겟팅하여 스크롤 시 고정되게 함 */
        div[data-testid="column"]:nth-of-type(2) {
            position: sticky;
            top: 60px; /* 상단 여백 */
            height: fit-content;
            max-height: 90vh;
            overflow-y: auto;
            z-index: 999;
        }
        
        /* [Compact Card UI] 강의 카드 소형화 */
        .course-card-compact {
            background-color: white;
            border-radius: 8px;
            padding: 10px 12px;
            margin-bottom: 6px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            border: 1px solid #eee;
            transition: transform 0.1s;
        }
        .course-card-compact:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.08);
        }
        .cc-title { font-weight: 700; font-size: 14px; color: #333; }
        .cc-meta { font-size: 11px; color: #666; margin-top: 2px; }
        .cc-time { font-size: 11px; color: #8A1538; font-weight: 600; margin-top: 2px; }

        /* [Navigation] */
        div.row-widget.stRadio > div[role="radiogroup"] {
            background-color: rgba(255, 255, 255, 0.7);
            backdrop-filter: blur(10px);
            padding: 4px;
            border-radius: 16px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.03);
            display: flex; justify-content: center; gap: 6px;
            border: 1px solid rgba(255,255,255,0.6);
            max-width: 750px; margin: 0 auto;
        }
        div.row-widget.stRadio > div[role="radiogroup"] > label {
            flex: 1; text-align: center; border-radius: 12px !important;
            padding: 8px 12px !important; font-weight: 600 !important; font-size: 0.9rem !important;
            border: none !important; background: transparent !important; color: #888 !important;
            box-shadow: none !important; margin: 0 !important;
        }
        div.row-widget.stRadio > div[role="radiogroup"] > label[data-checked="true"] {
            background: linear-gradient(135deg, #8A1538 0%, #A01B42 100%) !important;
            color: #FFFFFF !important; box-shadow: 0 2px 8px rgba(138, 21, 56, 0.3) !important;
        }

        /* [Etc] */
        [data-testid="stSidebar"] { background-color: #FFFFFF !important; border-right: 1px solid rgba(0,0,0,0.05); }
        textarea[data-testid="stChatInputTextArea"] { background-color: rgba(255, 255, 255, 0.6) !important; backdrop-filter: blur(10px); }
        #MainMenu {visibility: hidden;} footer {visibility: hidden;}
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

def add_log(role, content, menu_context=None):
    timestamp = datetime.datetime.now().strftime("%H:%M")
    st.session_state.global_log.append({
        "role": role,
        "content": content,
        "time": timestamp,
        "menu": menu_context
    })

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
# [Firebase Manager]
# -----------------------------------------------------------------------------
class FirebaseManager:
    def __init__(self):
        self.db = None
        self.is_initialized = False
        self.init_firestore()

    def init_firestore(self):
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
        if not self.is_initialized: return None, "Firebase 연결 실패"
        try:
            users_ref = self.db.collection('users')
            query = users_ref.where('email', '==', email).where('password', '==', password).stream()
            for doc in query:
                user_data = doc.to_dict()
                user_data['localId'] = doc.id
                return user_data, None
            return None, "이메일 또는 비밀번호 불일치"
        except Exception as e: return None, str(e)

    def signup(self, email, password):
        if not self.is_initialized: return None, "Firebase 연결 실패"
        try:
            users_ref = self.db.collection('users')
            existing = list(users_ref.where('email', '==', email).stream())
            if len(existing) > 0: return None, "이미 가입된 이메일"
            new_ref = users_ref.document()
            data = {"email": email, "password": password, "created_at": firestore.SERVER_TIMESTAMP}
            new_ref.set(data)
            data['localId'] = new_ref.id
            return data, None
        except Exception as e: return None, str(e)

    def save_data(self, collection, doc_id, data):
        if not self.is_initialized or not st.session_state.user: return False
        try:
            uid = st.session_state.user['localId']
            self.db.collection('users').document(uid).collection(collection).document(doc_id).set(data)
            return True
        except: return False

    def load_collection(self, collection):
        if not self.is_initialized or not st.session_state.user: return []
        try:
            uid = st.session_state.user['localId']
            docs = self.db.collection('users').document(uid).collection(collection).order_by('updated_at', direction=firestore.Query.DESCENDING).stream()
            return [{"id": doc.id, **doc.to_dict()} for doc in docs]
        except: return []

fb_manager = FirebaseManager()

# PDF 로드
@st.cache_resource(show_spinner="문서 학습 중...")
def load_knowledge_base():
    if not os.path.exists("data"): return ""
    pdf_files = glob.glob("data/*.pdf")
    if not pdf_files: return ""
    all_content = ""
    for pdf_file in pdf_files:
        try:
            loader = PyPDFLoader(pdf_file)
            pages = loader.load_and_split()
            all_content += f"\n\n--- [문서: {os.path.basename(pdf_file)}] ---\n"
            for page in pages: all_content += page.page_content
        except: continue
    return all_content

PRE_LEARNED_DATA = load_knowledge_base()

# -----------------------------------------------------------------------------
# [AI Engine]
# -----------------------------------------------------------------------------
def get_llm():
    if not api_key: return None
    return ChatGoogleGenerativeAI(model="gemini-2.5-flash-preview-09-2025", temperature=0)

def ask_ai(question):
    llm = get_llm()
    if not llm: return "⚠️ API Key 오류"
    def _execute():
        chain = PromptTemplate.from_template(
            "문서 내용: {context}\n질문: {question}\n문서 기반 답변(인용 필수):"
        ) | llm
        return chain.invoke({"context": PRE_LEARNED_DATA, "question": question}).content
    try: return run_with_retry(_execute)
    except: return "⚠️ AI 응답 지연"

# -----------------------------------------------------------------------------
# [기능 로직] 시간표 & 데이터 추출 (로직 수정됨)
# -----------------------------------------------------------------------------
def check_time_conflict(new_course, current_schedule):
    new_slots = set(new_course.get('time_slots', []))
    for existing in current_schedule:
        existing_slots = set(existing.get('time_slots', []))
        if new_slots & existing_slots: return True, existing['name']
    return False, None

def render_interactive_timetable(schedule_list):
    days = ["월", "화", "수", "목", "금"]
    table_grid = {i: {d: None for d in days} for i in range(1, 10)}
    online_courses = []
    
    # 색상 (진한 파스텔)
    palette = [
        {"bg": "#FFEBEE", "text": "#C62828"}, {"bg": "#E3F2FD", "text": "#1565C0"},
        {"bg": "#E8F5E9", "text": "#2E7D32"}, {"bg": "#F3E5F5", "text": "#6A1B9A"},
        {"bg": "#FFF3E0", "text": "#EF6C00"}, {"bg": "#E0F2F1", "text": "#00695C"},
        {"bg": "#FCE4EC", "text": "#AD1457"}
    ]

    for course in schedule_list:
        slots = course.get('time_slots', [])
        if not slots or slots == ["시간미정"] or not isinstance(slots, list):
            online_courses.append(course)
            continue
        
        style = palette[abs(hash(course['name'])) % len(palette)]
        for slot in slots:
            if len(slot) < 2: continue
            day, period = slot[0], int(slot[1:]) if slot[1:].isdigit() else 0
            if day in days and 1 <= period <= 9:
                table_grid[period][day] = {"name": course['name'], "prof": course['professor'], "style": style}

    # HTML (Compact)
    html = """
    <style>
        .tt-table { width: 100%; border-collapse: separate; border-spacing: 2px; table-layout: fixed; font-family: 'Pretendard'; }
        .tt-header { color: #888; font-size: 11px; text-align: center; border-bottom: 1px solid #eee; padding: 4px; }
        .tt-time { color: #aaa; font-size: 10px; text-align: center; height: 40px; }
        .tt-cell { padding: 0; height: 40px; vertical-align: top; }
        .tt-card {
            width: 100%; height: 100%; display: flex; flex-direction: column; justify-content: center;
            border-radius: 6px; font-size: 10px; line-height: 1.1; text-align: center; cursor: default;
        }
        .tt-name { font-weight: 800; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .tt-online { margin-top: 10px; font-size: 11px; }
        .tt-badge { display: inline-block; padding: 2px 6px; border-radius: 4px; margin: 2px; font-weight: 700; font-size: 10px; }
    </style>
    <table class="tt-table">
        <tr><th style="width:20px;"></th><th>MON</th><th>TUE</th><th>WED</th><th>THU</th><th>FRI</th></tr>
    """
    for i in range(1, 10):
        html += f"<tr><td class='tt-time'>{i}</td>"
        for d in days:
            c = table_grid[i][d]
            if c:
                html += f"<td class='tt-cell'><div class='tt-card' style='background:{c['style']['bg']}; color:{c['style']['text']};'><span class='tt-name'>{c['name']}</span></div></td>"
            else:
                html += "<td class='tt-cell' style='border:1px dashed #f5f5f5;'></td>"
        html += "</tr>"
    html += "</table>"
    
    if online_courses:
        html += "<div class='tt-online'><strong>💻 Online/Etc:</strong> "
        for c in online_courses:
            s = palette[abs(hash(c['name'])) % len(palette)]
            html += f"<span class='tt-badge' style='background:{s['bg']}; color:{s['text']};'>{c['name']}</span>"
        html += "</div>"
    return html

# [핵심 수정] 교양 과목 로직 완화된 프롬프트
def get_course_candidates_json(major, grade, semester, diagnosis_text=""):
    llm = get_llm()
    if not llm: return []

    # 교양 과목에 대한 제약을 명시적으로 해제함
    prompt_template = """
    너는 [대학교 학사 데이터베이스 파서]이다. 
    제공된 [수강신청자료집/시간표 문서]를 분석하여 **{major} {grade} {semester}** 학생이 수강 가능한 **모든 정규 개설 과목**을 JSON 리스트로 추출하라.
    
    [필수 규칙 - 엄격 준수]
    1. **전공 과목:** {major} 학생이 수강 가능한 과목만 포함하라. 타과 전용 과목은 제외하라.
    2. **교양(General Education) 과목:** **학년 제한을 무시하고 개설된 모든 교양 과목을 포함하라.** (예: 1학년 대상이라도 고학년이 수강 가능하므로 모두 포함). 학정번호가 달라도 상관없다.
    3. **데이터 기반:** 학습된 문서에 있는 과목만 추출하라. 없는 과목을 지어내지 마라.
    4. **Priority 설정:**
       - 전공필수/재수강 권고 = "High"
       - 전공선택 = "Medium"
       - 교양 및 일반선택 = "Normal" (학년 무관하게 모두 포함)
    
    [JSON 출력 포맷]
    [
        {{
            "id": "code_001", "name": "과목명", "professor": "교수명", "credits": 3,
            "time_slots": ["월3", "수4"], "classification": "교양필수/전공선택",
            "priority": "Normal", "reason": "교양 | 학년무관"
        }}
    ]
    **오직 JSON 리스트만 출력하라.**
    
    [진단 결과 참고] {diagnosis_context}
    [문서 데이터] {context}
    """
    
    def _execute():
        chain = PromptTemplate.from_template(prompt_template) | llm
        return chain.invoke({
            "major": major, "grade": grade, "semester": semester,
            "diagnosis_context": diagnosis_text, "context": PRE_LEARNED_DATA
        }).content

    try:
        response = run_with_retry(_execute)
        cleaned_json = response.replace("```json", "").replace("```", "").strip()
        if not cleaned_json.startswith("["):
             start = cleaned_json.find("[")
             end = cleaned_json.rfind("]")
             if start != -1 and end != -1: cleaned_json = cleaned_json[start:end+1]
        return json.loads(cleaned_json)
    except: return []

# 성적 분석 함수들 (유지)
def analyze_graduation_requirements(uploaded_images):
    llm = get_pro_llm() # Pro급 모델 권장
    if not llm: return "⚠️ API Key"
    # (이미지 처리 생략 - 이전과 동일)
    return "분석 기능은 현재 데모 모드입니다." # 실제 구현시 이전 코드 사용

def chat_with_graduation_ai(current_analysis, user_input):
    llm = get_llm()
    # (챗봇 로직 생략 - 이전과 동일)
    return "답변 생성 중..."

# -----------------------------------------------------------------------------
# [메인 UI]
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 🎛️ Control Tower")
    if st.session_state.user is None:
        with st.expander("🔐 Login", expanded=True):
            mode = st.radio("Mode", ["로그인", "회원가입"], horizontal=True, label_visibility="collapsed")
            email = st.text_input("Email", placeholder="example@kw.ac.kr")
            pw = st.text_input("PW", type="password")
            if st.button("Go", use_container_width=True):
                if mode == "로그인": u, e = fb_manager.login(email, pw)
                else: u, e = fb_manager.signup(email, pw)
                if u: st.session_state.user = u; st.rerun()
                else: st.error(e)
    else:
        st.info(f"👤 {st.session_state.user['email']}")
        if st.button("Logout", use_container_width=True): st.session_state.clear(); st.rerun()
    
    st.markdown("---")
    if st.button("📡 Data Sync"):
        st.toast("Syncing..."); time.sleep(1); st.cache_resource.clear(); st.rerun()

# 헤더
st.markdown('<h1 class="main-title">🦄 KW-Master Pro</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Digital Campus Agent for Kwangwoon Univ.</p>', unsafe_allow_html=True)

# 메뉴
menu = st.radio("M", ["🤖 AI 지식인", "📅 스마트 시간표", "📈 성적 진단"], horizontal=True, label_visibility="collapsed", key="menu_radio")
if menu != st.session_state.current_menu: st.session_state.current_menu = menu; st.rerun()
st.write("")

# 메인 컨테이너
with st.container(border=True):
    if st.session_state.current_menu == "🤖 AI 지식인":
        # (지식인 코드 유지)
        st.subheader("🤖 무엇이든 물어보세요")
        chat_container = st.container(height=500)
        with chat_container:
            for msg in st.session_state.chat_history:
                with st.chat_message(msg["role"]): st.markdown(msg["content"])
        if prompt := st.chat_input("질문 입력..."):
            st.session_state.chat_history.append({"role":"user","content":prompt})
            with chat_container:
                st.chat_message("user").write(prompt)
                with st.chat_message("assistant"):
                    resp = ask_ai(prompt)
                    st.write(resp)
            st.session_state.chat_history.append({"role":"assistant","content":resp})

    elif st.session_state.current_menu == "📅 스마트 시간표":
        st.subheader("📅 AI Smart Timetable")
        
        # [설정 영역]
        with st.expander("🛠️ 설정 (학과/학년)", expanded=not bool(st.session_state.candidate_courses)):
            c1, c2, c3 = st.columns(3)
            major = c1.selectbox("학과", ["전자공학과", "소프트웨어학부", "컴퓨터정보공학부", "정보융합학부"], key="tt_major")
            grade = c2.selectbox("학년", ["1학년", "2학년", "3학년", "4학년"], key="tt_grade")
            semester = c3.selectbox("학기", ["1학기", "2학기"], key="tt_semester")
            if st.button("🚀 강의 불러오기 (AI Scan)", type="primary", use_container_width=True):
                with st.spinner("교양 과목 포함 전수 조사 중..."):
                    res = get_course_candidates_json(major, grade, semester)
                    if res: st.session_state.candidate_courses = res; st.session_state.my_schedule = []; st.rerun()
                    else: st.error("강의를 찾지 못했습니다.")

        # [메인 빌더 UI] - 좌우 분할 및 Sticky 적용
        if st.session_state.candidate_courses:
            st.write("---")
            # 비율 조정: 왼쪽(리스트) 1.2 : 오른쪽(시간표) 1
            col_left, col_right = st.columns([1.2, 1], gap="medium")

            # [좌측] 강의 리스트 (스크롤 가능)
            with col_left:
                st.markdown("##### 📚 강의 목록")
                # 탭을 사용하여 분류
                tab1, tab2, tab3 = st.tabs(["🔥 전공필수", "🏫 전공선택", "🧩 교양/기타"])
                
                # [Compact Card 렌더링 함수]
                def draw_compact_list(course_list, key_prefix, color_border):
                    # 이미 담은 과목 제외
                    added_ids = [c['name'] for c in st.session_state.my_schedule]
                    
                    for c in course_list:
                        if c['name'] in added_ids: continue
                        
                        # 카드 HTML (CSS 클래스 활용)
                        card_html = f"""
                        <div class="course-card-compact" style="border-left: 4px solid {color_border};">
                            <div style="display:flex; justify-content:space-between; align-items:start;">
                                <div>
                                    <div class="cc-title">{c['name']}</div>
                                    <div class="cc-meta">{c['classification']} | {c['credits']}학점 | {c['professor']}</div>
                                </div>
                                <div style="text-align:right;">
                                    <div class="cc-time">{', '.join(c['time_slots']) if c['time_slots'] else '미정'}</div>
                                </div>
                            </div>
                        </div>
                        """
                        st.markdown(card_html, unsafe_allow_html=True)
                        
                        # 버튼 (작게 배치)
                        b_col1, b_col2 = st.columns([0.85, 0.15])
                        if b_col2.button("➕", key=f"add_{key_prefix}_{c['id']}", help="시간표에 추가"):
                            cf, cfn = check_time_conflict(c, st.session_state.my_schedule)
                            if cf: st.toast(f"충돌: {cfn}", icon="🚫")
                            else: st.session_state.my_schedule.append(c); st.rerun()
                
                # 데이터 분류
                must = [c for c in st.session_state.candidate_courses if c.get('priority') == 'High']
                maj = [c for c in st.session_state.candidate_courses if c.get('priority') == 'Medium']
                # 교양/기타: Priority가 Normal이거나 나머지는 다 여기로
                etc = [c for c in st.session_state.candidate_courses if c not in must and c not in maj]

                with tab1: draw_compact_list(must, "must", "#C62828") # Red
                with tab2: draw_compact_list(maj, "maj", "#1565C0")   # Blue
                with tab3: draw_compact_list(etc, "etc", "#2E7D32")   # Green (교양 포함)

            # [우측] 내 시간표 (Sticky 고정됨)
            with col_right:
                st.markdown("##### 🗓️ 내 시간표")
                
                # 미니 대시보드
                total_cr = sum([c['credits'] for c in st.session_state.my_schedule])
                st.caption(f"신청 학점: {total_cr}학점")
                
                # 삭제 버튼들 (Pill 형태)
                if st.session_state.my_schedule:
                    st.write("담은 과목 (클릭 삭제):")
                    cols = st.columns(3)
                    for i, c in enumerate(st.session_state.my_schedule):
                        if cols[i%3].button(f"✕ {c['name']}", key=f"del_{i}"):
                            st.session_state.my_schedule.pop(i); st.rerun()
                
                # 시간표 렌더링
                html_tt = render_interactive_timetable(st.session_state.my_schedule)
                st.markdown(html_tt, unsafe_allow_html=True)
                
                # 저장/초기화
                c1, c2 = st.columns(2)
                if c1.button("💾 저장", use_container_width=True, type="primary"):
                    st.toast("저장되었습니다! (데모)", icon="✅")
                if c2.button("🔄 초기화", use_container_width=True):
                    st.session_state.my_schedule = []; st.rerun()

    elif st.session_state.current_menu == "📈 성적 진단":
        st.subheader("📈 성적 및 진로 진단")
        st.info("준비 중입니다.")

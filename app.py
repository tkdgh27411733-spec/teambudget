import streamlit as st
import pandas as pd
import requests
import datetime
import plotly.express as px

st.set_page_config(page_title="팀 예산 관리 대시보드", page_icon="📊", layout="wide")

# 💡 Github에 코드를 올릴 때는 보안을 위해 Streamlit Secrets 기능을 활용합니다.
# 로컬 테스트 시 사이드바에 입력하거나, 배포 시 Streamlit Cloud 설정에서 Secrets를 추가하세요.
# 예: GAS_URL = "https://script.google.com/macros/s/.../exec"
WEB_APP_URL = st.secrets.get("GAS_URL", "https://script.google.com/macros/s/AKfycbyG4O6baCQAHg_KkwQ5nX_UmjF7KJhEwZwFnYqNaN3saxx3tb03HU1wD5XTtS0gSvk/exec")

@st.cache_data(ttl=10) # 서버 성능과 실시간성 밸런스를 위해 10초마다 갱신
def fetch_data(url):
    if url == "https://script.google.com/macros/s/AKfycbyG4O6baCQAHg_KkwQ5nX_UmjF7KJhEwZwFnYqNaN3saxx3tb03HU1wD5XTtS0gSvk/exec" or not url:
        return pd.DataFrame()
    try:
        response = requests.get(url)
        data = response.json()
        if data and len(data) > 0:
            df = pd.DataFrame(data)
            # 'Amount' 컬럼을 숫자로 변환 (에러 발생 시 NaN 처리 후 0으로 대체)
            df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
        return pd.DataFrame()

def submit_data(url, member, month, category, amount):
    if url == "여기에_앱스스크립트_URL을_입력하세요" or not url:
        st.error("Google Apps Script 웹앱 URL이 설정되지 않았습니다. 좌측 사이드바에서 설정해주세요.")
        return False

    payload = {
        "id": int(datetime.datetime.now().timestamp() * 1000),
        "Member": member,
        "Month": month,
        "Category": category,
        "Amount": amount
    }
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            st.success("✅ 예산 데이터가 스프레드시트에 성공적으로 기록되었습니다!")
            fetch_data.clear() # 새 데이터를 불러오기 위해 캐시 초기화
            return True
        else:
            st.error("❌ 저장에 실패했습니다. 스프레드시트 설정을 확인해주세요.")
            return False
    except Exception as e:
        st.error(f"요청 오류: {e}")
        return False

st.title("📊 팀 예산 관리 시스템")
st.caption("부장님 보고용 월별 예산 취합 및 대시보드 (Google Sheets 연동)")

with st.sidebar:
    st.header("⚙️ 환경 설정")
    if WEB_APP_URL == "여기에_앱스스크립트_URL을_입력하세요":
        st.warning("⚠️ Apps Script 웹앱 URL이 필요합니다.")
        user_url = st.text_input("Apps Script URL 입력", type="password")
        if user_url:
            WEB_APP_URL = user_url
    else:
        st.success("✅ Apps Script URL이 설정되었습니다.")
        # 만약 URL을 변경하고 싶을 경우를 대비한 입력창
        user_url = st.text_input("URL 수정 (필요시)", value=WEB_APP_URL, type="password")
        if user_url:
             WEB_APP_URL = user_url

tab_input, tab_dashboard = st.tabs(["📝 데이터 입력", "📈 전체 대시보드"])

# --- TAB 1: 데이터 입력 ---
with tab_input:
    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("내역 입력")
        with st.form("budget_form", clear_on_submit=True):
            member = st.selectbox("팀원 선택", ["부장님", "팀원1", "팀원2", "팀원3", "팀원4"])
            
            # 달력 위젯에서 날짜를 선택하면 YYYY-MM 형태로 변환
            current_date = datetime.date.today()
            selected_date = st.date_input("해당 월 (날짜 선택)", current_date)
            month_str = selected_date.strftime("%Y-%m")
            
            category = st.selectbox("예산 항목", ["수선유지비", "비품", "개량공사"])
            amount = st.number_input("사용 금액 (원)", min_value=0, step=1000)
            
            submitted = st.form_submit_button("기록 저장하기", use_container_width=True)
            
            if submitted:
                if amount > 0:
                    submit_data(WEB_APP_URL, member, month_str, category, amount)
                else:
                    st.warning("사용 금액은 0원보다 커야 합니다.")

    with col2:
        st.subheader("📂 최근 입력 내역 (Google Sheets)")
        df = fetch_data(WEB_APP_URL)
        if not df.empty:
            # id와 Timestamp 컬럼은 숨기고 최신순 정렬
            display_cols = ["Month", "Member", "Category", "Amount"]
            # 데이터프레임에 해당 컬럼들이 존재하는지 확인 후 필터링
            available_cols = [col for col in display_cols if col in df.columns]
            
            df_display = df.sort_values(by="id", ascending=False) if "id" in df.columns else df
            df_display = df_display[available_cols]
            
            # 금액에 콤마 포맷팅 적용
            st.dataframe(
                df_display.style.format({"Amount": "{:,.0f}원"}),
                use_container_width=True, 
                hide_index=True
            )
        else:
            st.info("아직 입력된 데이터가 없거나 스프레드시트가 비어있습니다.")

# --- TAB 2: 대시보드 ---
with tab_dashboard:
    df = fetch_data(WEB_APP_URL)
    
    if not df.empty and "Amount" in df.columns:
        total_amount = df['Amount'].sum()
        
        category_group = df.groupby('Category')['Amount'].sum()
        top_category = category_group.idxmax() if not category_group.empty else "-"
        top_category_amount = category_group.max() if not category_group.empty else 0
        
        data_count = len(df)

        metric_col1, metric_col2, metric_col3 = st.columns(3)
        metric_col1.metric("전체 누적 사용액", f"{total_amount:,.0f}원")
        metric_col2.metric("최대 사용 항목", f"{top_category}", f"{top_category_amount:,.0f}원", delta_color="off")
        metric_col3.metric("총 데이터 건수", f"{data_count}건")

        st.divider()

        chart_col1, chart_col2 = st.columns(2)

        with chart_col1:
            st.subheader("🏠 항목별 예산 분포")
            fig_pie = px.pie(
                df, 
                values='Amount', 
                names='Category', 
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig_pie.update_layout(margin=dict(t=0, b=0, l=0, r=0))
            st.plotly_chart(fig_pie, use_container_width=True)

        with chart_col2:
            st.subheader("👥 팀원별 누적 사용액")
            member_group = df.groupby('Member')['Amount'].sum().reset_index()
            fig_bar = px.bar(
                member_group, 
                x='Member', 
                y='Amount', 
                text='Amount', 
                color='Member',
                color_discrete_sequence=px.colors.qualitative.Set2
            )
            fig_bar.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
            fig_bar.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0))
            st.plotly_chart(fig_bar, use_container_width=True)

        st.divider()

        st.subheader("📅 월별/항목별 요약 테이블 (취합본)")
        try:
            pivot_df = df.pivot_table(
                index='Month', 
                columns='Category', 
                values='Amount', 
                aggfunc='sum', 
                fill_value=0
            )
            pivot_df['합계'] = pivot_df.sum(axis=1)
            # 월 기준 내림차순 정렬
            pivot_df = pivot_df.sort_index(ascending=False)
            
            st.dataframe(
                pivot_df.style.format("{:,.0f}원"), 
                use_container_width=True
            )
        except Exception as e:
            st.error("데이터를 취합하는 중 문제가 발생했습니다.")
            st.write(e)
            
    else:
        st.info("대시보드를 생성하기 위한 데이터가 부족합니다. 먼저 내역을 입력해주세요.")

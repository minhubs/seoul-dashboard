import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px

st.set_page_config(layout="wide")
st.title("🏛️ 서울시 문화/관광/행사 통합 대시보드")

# -----------------------------
# 데이터 로드
# -----------------------------
@st.cache_data
def load_data():
    df = pd.read_csv("서울시 문화공간 정보.csv", encoding="utf-8-sig")
    tour = pd.read_csv("서울시 관광 명소.csv", encoding="utf-8")
    event = pd.read_csv("서울시 문화행사 정보.csv", encoding="utf-8")
    return df, tour, event

df, tour, event = load_data()

# -----------------------------
# 컬럼 정리
# -----------------------------
df.rename(columns={
    '문화시설명':'시설명',
    '주제분류':'유형',
    '자치구':'자치구',
    '주소':'주소',
    '위도':'위도',
    '경도':'경도',
    '무료구분':'무료구분'
}, inplace=True)

tour.rename(columns={
    "상호명": "시설명",
    "신주소": "주소",
    "태그": "유형"
}, inplace=True)

tour = tour.loc[:, ~tour.columns.duplicated()]

event.rename(columns={
    "공연/행사명": "시설명",
    "장소": "주소",
    "분류": "유형"
}, inplace=True)

df["위도"] = pd.to_numeric(df["위도"], errors="coerce")
df["경도"] = pd.to_numeric(df["경도"], errors="coerce")

df = df[["시설명","자치구","유형","주소","위도","경도","무료구분"]]
tour = tour[["시설명","주소","유형"]]
event = event[["시설명","주소","유형"]]

# -----------------------------
# DB
# -----------------------------
conn = sqlite3.connect(":memory:")
df.to_sql("culture_space", conn, index=False, if_exists="replace")
tour.to_sql("tour_place", conn, index=False, if_exists="replace")
event.to_sql("culture_event", conn, index=False, if_exists="replace")

# -----------------------------
# 필터
# -----------------------------
st.sidebar.header("🔍 필터")

gu = st.sidebar.selectbox("자치구", ["전체"] + sorted(df["자치구"].dropna().unique()))
typ = st.sidebar.selectbox("유형", ["전체"] + sorted(df["유형"].dropna().unique()))

df_f = df.copy()

if gu != "전체":
    df_f = df_f[df_f["자치구"] == gu]

if typ != "전체":
    df_f = df_f[df_f["유형"] == typ]

# -----------------------------
# KPI
# -----------------------------
c1, c2, c3, c4 = st.columns(4)

c1.metric("문화시설", len(df_f))
c2.metric("관광명소", len(tour))
c3.metric("문화행사", len(event))

free_ratio = (df_f["무료구분"] == "무료").mean() * 100
c4.metric("무료 비율", f"{free_ratio:.1f}%")

st.divider()

# -----------------------------
# 차트 1
# -----------------------------
col1, col2 = st.columns(2)

with col1:
    st.subheader("📊 자치구별 문화시설 수")

    d1 = df_f.groupby("자치구").size().reset_index(name="시설수")

    fig1 = px.bar(
        d1,
        x="자치구",
        y="시설수",
        text="시설수",
        color="시설수",
        color_continuous_scale="Blues"
    )

    fig1.update_layout(template="plotly_white")
    fig1.update_traces(textposition="outside")

    st.plotly_chart(fig1, use_container_width=True)

    st.code("""
SELECT 자치구, COUNT(*) AS 시설수
FROM culture_space
GROUP BY 자치구
ORDER BY 시설수 DESC
""")

    st.write("""
👉 서울시 문화시설은 특정 자치구(강남, 종로, 중구 등)에 집중되어 있는 경향이 뚜렷하게 나타난다.  
👉 이는 지역 간 문화 인프라 접근성의 불균형을 의미하며, 일부 지역 주민은 상대적으로 문화시설 이용 기회가 제한될 수 있다.  
👉 따라서 문화시설이 부족한 지역에 대한 정책적 지원 및 균형 있는 배치 전략이 필요하다.
""")

# -----------------------------
# 차트 2
# -----------------------------
with col2:
    st.subheader("🎨 문화공간 유형 분포")

    d2 = df_f["유형"].value_counts().reset_index()
    d2.columns = ["유형", "개수"]

    fig2 = px.pie(
        d2,
        names="유형",
        values="개수",
        hole=0.5,
        color_discrete_sequence=px.colors.qualitative.Set2
    )

    fig2.update_traces(textinfo="percent+label")

    st.plotly_chart(fig2, use_container_width=True)

    st.code("""
SELECT 유형, COUNT(*) AS 개수
FROM culture_space
GROUP BY 유형
""")

    st.write("""
👉 도서관, 박물관, 미술관 등 특정 유형의 문화시설이 높은 비중을 차지하고 있다.  
👉 이는 시민들이 접할 수 있는 문화 콘텐츠의 다양성이 제한될 가능성을 의미한다.  
👉 다양한 문화 경험을 제공하기 위해 공연장, 복합문화공간 등 다양한 유형의 시설 확충이 필요하다.
""")

# -----------------------------
# 차트 3
# -----------------------------
st.subheader("💰 무료 vs 유료")

d3 = df_f["무료구분"].value_counts().reset_index()
d3.columns = ["무료구분", "개수"]

fig3 = px.pie(
    d3,
    names="무료구분",
    values="개수",
    color="무료구분",
    color_discrete_map={
        "무료": "#00B894",
        "유료": "#E17055",
        "정보없음": "#B2BEC3"
    }
)

st.plotly_chart(fig3)

st.code("""
SELECT 무료구분, COUNT(*) AS 개수
FROM culture_space
GROUP BY 무료구분
""")

st.write("""
👉 무료 문화시설의 비율은 시민들의 문화 접근성을 결정하는 중요한 요소이다.  
👉 무료 시설이 많을수록 경제적 부담 없이 문화생활을 즐길 수 있는 환경이 조성된다.  
👉 반대로 유료 시설 비중이 높을 경우 일부 계층의 문화 접근성이 제한될 수 있어, 공공 문화 정책의 보완이 필요하다.
""")

# -----------------------------
# 지도
# -----------------------------
st.subheader("🗺️ 문화시설 위치")

map_df = df_f.dropna(subset=["위도","경도"]).copy()

if not map_df.empty:
    fig_map = px.scatter_mapbox(
        map_df,
        lat="위도",
        lon="경도",
        hover_name="시설명",
        hover_data=["자치구","유형"],
        color="유형",
        zoom=10,
        height=500
    )

    fig_map.update_layout(mapbox_style="carto-positron")

    st.plotly_chart(fig_map, use_container_width=True)

# -----------------------------
# 테이블
# -----------------------------
st.subheader("📋 시설 목록")
st.dataframe(df_f)


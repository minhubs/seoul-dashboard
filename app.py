import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from pathlib import Path

# -----------------------------
# 페이지 기본 설정
# -----------------------------
st.set_page_config(
    page_title="서울시 문화/관광/행사 통합 대시보드",
    layout="wide"
)

st.title("🏛️ 서울시 문화/관광/행사 통합 대시보드")
st.caption("서울시 공공데이터를 활용한 문화공간 분포 및 문화 접근성 분석")

# -----------------------------
# 파일 경로 설정
# -----------------------------
BASE_DIR = Path(__file__).parent


# -----------------------------
# CSV 파일 자동 찾기 함수
# -----------------------------
def find_csv_file(keyword):
    """
    app.py와 같은 폴더에서 특정 키워드가 들어간 CSV 파일을 자동으로 찾는 함수
    예: keyword='문화공간' → '서울시 문화공간 정보.csv' 자동 탐색
    """
    files = sorted(BASE_DIR.glob(f"*{keyword}*.csv"))

    if len(files) == 0:
        return None

    return files[0]


# -----------------------------
# CSV 안전하게 읽기 함수
# -----------------------------
def read_csv_safely(file_path):
    """
    CSV 파일의 인코딩 문제를 줄이기 위해 여러 인코딩으로 읽어보는 함수
    """
    encodings = ["utf-8-sig", "utf-8", "cp949", "euc-kr"]

    for enc in encodings:
        try:
            return pd.read_csv(file_path, encoding=enc)
        except UnicodeDecodeError:
            continue

    # 위 인코딩으로 모두 실패하면 기본 방식으로 마지막 시도
    return pd.read_csv(file_path)


# -----------------------------
# 문화공간 컬럼 정리 함수
# -----------------------------
def normalize_culture_columns(df):
    """
    문화공간 데이터 컬럼명을 대시보드에서 쓰기 쉽게 통일
    공공데이터 컬럼명이 한글/영어 어느 쪽이어도 대응
    """

    rename_map = {
        "문화시설명": "시설명",
        "FAC_NAME": "시설명",
        "fac_name": "시설명",

        "주제분류": "유형",
        "SUBJCODE": "유형",
        "subjcode": "유형",

        "자치구": "자치구",
        "GNGU": "자치구",
        "gngu": "자치구",

        "주소": "주소",
        "ADDR": "주소",
        "addr": "주소",

        "위도": "위도",
        "X_COORD": "위도",
        "x_coord": "위도",

        "경도": "경도",
        "Y_COORD": "경도",
        "y_coord": "경도",

        "무료구분": "무료구분",
        "ENTRFREE": "무료구분",
        "entrfree": "무료구분",

        "관람료": "관람료",
        "ENTR_FEE": "관람료",
        "entr_fee": "관람료",

        "관람시간": "관람시간",
        "OPENHOUR": "관람시간",
        "openhour": "관람시간",

        "휴관일": "휴관일",
        "CLOSEDAY": "휴관일",
        "closeday": "휴관일",

        "홈페이지": "홈페이지",
        "HOMEPAGE": "홈페이지",
        "homepage": "홈페이지",

        "전화번호": "전화번호",
        "PHNE": "전화번호",
        "phne": "전화번호"
    }

    df = df.rename(columns=rename_map)

    # 필요한 컬럼이 없으면 오류 대신 '정보없음'으로 생성
    required_cols = [
        "시설명", "자치구", "유형", "주소",
        "위도", "경도", "무료구분",
        "관람료", "관람시간", "휴관일", "홈페이지", "전화번호"
    ]

    for col in required_cols:
        if col not in df.columns:
            df[col] = "정보없음"

    # 위도/경도 숫자형 변환
    df["위도"] = pd.to_numeric(df["위도"], errors="coerce")
    df["경도"] = pd.to_numeric(df["경도"], errors="coerce")

    # 결측치 정리
    text_cols = [
        "시설명", "자치구", "유형", "주소",
        "무료구분", "관람료", "관람시간",
        "휴관일", "홈페이지", "전화번호"
    ]

    for col in text_cols:
        df[col] = df[col].fillna("정보없음")
        df[col] = df[col].replace("", "정보없음")

    return df[required_cols]


# -----------------------------
# 관광명소 컬럼 정리 함수
# -----------------------------
def normalize_tour_columns(tour):
    """
    관광명소 데이터 컬럼명을 통일
    파일이 없거나 컬럼명이 달라도 앱이 멈추지 않게 처리
    """

    if tour.empty:
        return pd.DataFrame(columns=["시설명", "주소", "유형"])

    rename_map = {
        "상호명": "시설명",
        "명칭": "시설명",
        "관광지명": "시설명",
        "시설명": "시설명",

        "신주소": "주소",
        "주소": "주소",

        "태그": "유형",
        "분류": "유형",
        "유형": "유형"
    }

    tour = tour.rename(columns=rename_map)
    tour = tour.loc[:, ~tour.columns.duplicated()]

    for col in ["시설명", "주소", "유형"]:
        if col not in tour.columns:
            tour[col] = "정보없음"

    tour["시설명"] = tour["시설명"].fillna("정보없음")
    tour["주소"] = tour["주소"].fillna("정보없음")
    tour["유형"] = tour["유형"].fillna("정보없음")

    return tour[["시설명", "주소", "유형"]]


# -----------------------------
# 문화행사 컬럼 정리 함수
# -----------------------------
def normalize_event_columns(event):
    """
    문화행사 데이터 컬럼명을 통일
    파일이 없거나 컬럼명이 달라도 앱이 멈추지 않게 처리
    """

    if event.empty:
        return pd.DataFrame(columns=["시설명", "주소", "유형"])

    rename_map = {
        "공연/행사명": "시설명",
        "행사명": "시설명",
        "제목": "시설명",
        "시설명": "시설명",

        "장소": "주소",
        "주소": "주소",

        "분류": "유형",
        "유형": "유형"
    }

    event = event.rename(columns=rename_map)
    event = event.loc[:, ~event.columns.duplicated()]

    for col in ["시설명", "주소", "유형"]:
        if col not in event.columns:
            event[col] = "정보없음"

    event["시설명"] = event["시설명"].fillna("정보없음")
    event["주소"] = event["주소"].fillna("정보없음")
    event["유형"] = event["유형"].fillna("정보없음")

    return event[["시설명", "주소", "유형"]]


# -----------------------------
# 데이터 로드
# -----------------------------
@st.cache_data
def load_data():
    """
    CSV 파일을 불러와서 대시보드 분석에 맞게 정리
    문화공간 파일은 필수, 관광명소/문화행사 파일은 선택
    """

    culture_path = find_csv_file("문화공간")
    tour_path = find_csv_file("관광")
    event_path = find_csv_file("문화행사")

    # 문화공간 파일은 필수
    if culture_path is None:
        st.error("❌ 문화공간 CSV 파일을 찾을 수 없습니다.")
        st.write("app.py와 같은 폴더에 '문화공간'이라는 단어가 들어간 CSV 파일을 넣어주세요.")
        st.write("현재 폴더 파일 목록:")
        st.write([p.name for p in BASE_DIR.glob("*")])
        st.stop()

    df = read_csv_safely(culture_path)
    df = normalize_culture_columns(df)

    # 관광명소 파일은 선택
    if tour_path is not None:
        tour = read_csv_safely(tour_path)
        tour = normalize_tour_columns(tour)
    else:
        tour = pd.DataFrame(columns=["시설명", "주소", "유형"])

    # 문화행사 파일은 선택
    if event_path is not None:
        event = read_csv_safely(event_path)
        event = normalize_event_columns(event)
    else:
        event = pd.DataFrame(columns=["시설명", "주소", "유형"])

    return df, tour, event, culture_path, tour_path, event_path


df, tour, event, culture_path, tour_path, event_path = load_data()


# -----------------------------
# 불러온 파일 확인
# -----------------------------
with st.expander("📁 불러온 파일 확인"):
    st.write("문화공간 파일:", culture_path.name if culture_path else "없음")
    st.write("관광명소 파일:", tour_path.name if tour_path else "없음")
    st.write("문화행사 파일:", event_path.name if event_path else "없음")


# -----------------------------
# SQLite DB 생성
# -----------------------------
conn = sqlite3.connect(":memory:")

df.to_sql("culture_space", conn, index=False, if_exists="replace")
tour.to_sql("tour_place", conn, index=False, if_exists="replace")
event.to_sql("culture_event", conn, index=False, if_exists="replace")


# -----------------------------
# 사이드바 필터
# -----------------------------
st.sidebar.header("🔍 필터")

gu_list = ["전체"] + sorted(df["자치구"].dropna().astype(str).unique())
type_list = ["전체"] + sorted(df["유형"].dropna().astype(str).unique())

gu = st.sidebar.selectbox("자치구", gu_list)
typ = st.sidebar.selectbox("유형", type_list)

df_f = df.copy()

if gu != "전체":
    df_f = df_f[df_f["자치구"] == gu]

if typ != "전체":
    df_f = df_f[df_f["유형"] == typ]


# -----------------------------
# KPI 영역
# -----------------------------
c1, c2, c3, c4 = st.columns(4)

c1.metric("문화시설", len(df_f))
c2.metric("관광명소", len(tour))
c3.metric("문화행사", len(event))

if len(df_f) > 0:
    free_ratio = (df_f["무료구분"] == "무료").mean() * 100
else:
    free_ratio = 0

c4.metric("무료 비율", f"{free_ratio:.1f}%")

st.divider()


# -----------------------------
# 차트 1: 자치구별 문화시설 수
# -----------------------------
col1, col2 = st.columns(2)

with col1:
    st.subheader("📊 자치구별 문화시설 수 TOP 10")

    d1 = (
        df_f[df_f["자치구"] != "정보없음"]
        .groupby("자치구")
        .size()
        .reset_index(name="시설수")
        .sort_values("시설수", ascending=False)
        .head(10)
    )

    if d1.empty:
        st.info("선택한 조건에 해당하는 자치구별 데이터가 없습니다.")
    else:
        fig1 = px.bar(
            d1,
            x="자치구",
            y="시설수",
            text="시설수",
            color="시설수",
            color_continuous_scale="Blues"
        )

        fig1.update_layout(
            template="plotly_white",
            xaxis_title="자치구",
            yaxis_title="문화시설 수"
        )
        fig1.update_traces(textposition="outside")

        st.plotly_chart(fig1, use_container_width=True)

    st.markdown("**사용한 SQL**")
    st.code("""
SELECT 자치구, COUNT(*) AS 시설수
FROM culture_space
GROUP BY 자치구
ORDER BY 시설수 DESC
LIMIT 10;
""", language="sql")

    st.markdown("**인사이트**")
    st.write("""
자치구별 문화시설 수를 비교하면 서울시 문화 인프라가 어느 지역에 집중되어 있는지 확인할 수 있다.  
시설 수가 많은 지역은 문화 접근성이 높을 가능성이 있고, 시설 수가 적은 지역은 상대적으로 문화시설 이용 기회가 제한될 수 있다.  
따라서 이 분석은 지역 간 문화 인프라 격차를 확인하는 기초 자료로 활용할 수 있다.
""")


# -----------------------------
# 차트 2: 문화공간 유형 분포
# -----------------------------
with col2:
    st.subheader("🎨 문화공간 유형 분포")

    d2 = (
        df_f[df_f["유형"] != "정보없음"]["유형"]
        .value_counts()
        .reset_index()
    )

    d2.columns = ["유형", "개수"]

    if d2.empty:
        st.info("선택한 조건에 해당하는 유형 데이터가 없습니다.")
    else:
        fig2 = px.pie(
            d2,
            names="유형",
            values="개수",
            hole=0.5,
            color_discrete_sequence=px.colors.qualitative.Set2
        )

        fig2.update_traces(textinfo="percent+label")

        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("**사용한 SQL**")
    st.code("""
SELECT 유형, COUNT(*) AS 개수
FROM culture_space
GROUP BY 유형
ORDER BY 개수 DESC;
""", language="sql")

    st.markdown("**인사이트**")
    st.write("""
문화공간의 유형별 분포를 보면 서울시 문화시설이 어떤 콘텐츠 중심으로 구성되어 있는지 파악할 수 있다.  
도서관, 공연장, 박물관/기념관 등 특정 유형에 시설이 집중되어 있다면 시민들이 접할 수 있는 문화 경험의 폭이 제한될 수 있다.  
유형별 분석은 향후 부족한 문화시설 유형을 파악하는 기준으로 활용할 수 있다.
""")


# -----------------------------
# 차트 3: 무료 vs 유료 문화시설
# -----------------------------
st.subheader("💰 무료 vs 유료 문화시설 비율")

d3 = df_f["무료구분"].fillna("정보없음").value_counts().reset_index()
d3.columns = ["무료구분", "개수"]

if d3.empty:
    st.info("선택한 조건에 해당하는 무료/유료 데이터가 없습니다.")
else:
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

    fig3.update_traces(textinfo="percent+label")
    st.plotly_chart(fig3, use_container_width=True)

st.markdown("**사용한 SQL**")
st.code("""
SELECT 무료구분, COUNT(*) AS 개수
FROM culture_space
GROUP BY 무료구분;
""", language="sql")

st.markdown("**인사이트**")
st.write("""
무료 문화시설의 비율은 시민들의 문화 접근성을 판단하는 중요한 지표가 될 수 있다.  
무료 시설이 많을수록 경제적 부담 없이 문화생활을 즐길 수 있는 환경이 조성된다.  
반대로 유료 시설 비중이 높다면 일부 시민에게 문화 접근 장벽이 생길 수 있어 공공 문화 정책의 보완이 필요하다.
""")

st.divider()


# -----------------------------
# 지도 시각화
# -----------------------------
st.subheader("🗺️ 문화시설 위치 지도")

map_df = df_f.dropna(subset=["위도", "경도"]).copy()

if map_df.empty:
    st.info("표시할 수 있는 위도/경도 데이터가 없습니다.")
else:
    fig_map = px.scatter_mapbox(
        map_df,
        lat="위도",
        lon="경도",
        hover_name="시설명",
        hover_data=["자치구", "유형", "무료구분"],
        color="유형",
        zoom=10,
        height=500
    )

    fig_map.update_layout(
        mapbox_style="carto-positron",
        margin={"r": 0, "t": 0, "l": 0, "b": 0}
    )

    st.plotly_chart(fig_map, use_container_width=True)


# -----------------------------
# 시설 목록 테이블
# -----------------------------
st.subheader("📋 문화시설 목록")

table_cols = [
    "시설명", "자치구", "유형", "주소",
    "무료구분", "관람료", "관람시간", "휴관일",
    "홈페이지", "전화번호"
]

st.dataframe(
    df_f[table_cols],
    use_container_width=True
)


# -----------------------------
# 하단 안내
# -----------------------------
st.divider()
st.caption("※ CSV 파일은 app.py와 같은 폴더에 있어야 하며, 문화공간 파일명에는 '문화공간'이라는 단어가 포함되어 있어야 합니다.")

import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from pathlib import Path
import unicodedata

# =========================================================
# 페이지 기본 설정
# =========================================================
st.set_page_config(
    page_title="서울시 문화/관광/행사 통합 대시보드",
    layout="wide"
)

st.title("🏛️ 서울시 문화/관광/행사 통합 대시보드")
st.caption("서울시 공공데이터를 활용한 문화공간 분포 및 문화 접근성 분석")

BASE_DIR = Path(__file__).parent


# =========================================================
# 한글 파일명/컬럼명 정규화 함수
# =========================================================
def normalize_text(text):
    """
    한글 파일명/컬럼명 인식 오류를 줄이기 위한 정규화 함수
    - 맥북/깃허브/Streamlit Cloud에서 한글 조합 방식이 달라지는 문제 방지
    - 공백, 언더바, 하이픈 제거
    """
    text = str(text)
    text = unicodedata.normalize("NFC", text)
    text = unicodedata.normalize("NFKC", text)
    text = text.replace(" ", "")
    text = text.replace("_", "")
    text = text.replace("-", "")
    text = text.lower()
    return text


# =========================================================
# CSV 안전하게 읽기
# =========================================================
def read_csv_safely(file_path):
    """
    CSV 인코딩 문제를 피하기 위해 여러 인코딩으로 읽기 시도
    """
    encodings = ["utf-8-sig", "utf-8", "cp949", "euc-kr"]

    last_error = None

    for enc in encodings:
        try:
            return pd.read_csv(file_path, encoding=enc)
        except UnicodeDecodeError as e:
            last_error = e
            continue
        except Exception as e:
            last_error = e
            continue

    st.error(f"❌ CSV 파일을 읽을 수 없습니다: {file_path.name}")
    st.write("마지막 오류:", last_error)
    st.stop()


# =========================================================
# 현재 폴더의 CSV 파일 모두 찾기
# =========================================================
def get_csv_files():
    """
    app.py가 있는 폴더와 하위 폴더에서 CSV 파일 탐색
    단, .git 폴더는 제외
    """
    csv_files = []

    for p in BASE_DIR.rglob("*.csv"):
        if ".git" in p.parts:
            continue
        csv_files.append(p)

    return sorted(csv_files)


# =========================================================
# 파일 판별 점수 계산
# =========================================================
def get_column_names(df):
    return [normalize_text(c) for c in df.columns]


def score_culture_file(file_path, df):
    """
    문화공간 파일인지 판별하는 점수
    파일명뿐 아니라 컬럼명까지 같이 봄
    """
    name = normalize_text(file_path.name)
    cols = get_column_names(df)

    score = 0

    # 파일명 기준
    if "문화공간" in name:
        score += 100
    if "문화" in name and "공간" in name:
        score += 80

    # 컬럼명 기준
    if "문화시설명" in cols or "facname" in cols:
        score += 120
    if "주제분류" in cols or "subjcode" in cols:
        score += 40
    if "자치구" in cols or "gngu" in cols:
        score += 40
    if "무료구분" in cols or "entrfree" in cols:
        score += 40
    if "위도" in cols or "xcoord" in cols:
        score += 20
    if "경도" in cols or "ycoord" in cols:
        score += 20

    return score


def score_tour_file(file_path, df):
    """
    관광명소 파일인지 판별하는 점수
    """
    name = normalize_text(file_path.name)
    cols = get_column_names(df)

    score = 0

    if "관광명소" in name:
        score += 100
    elif "관광" in name:
        score += 80

    if "상호명" in cols:
        score += 50
    if "신주소" in cols:
        score += 40
    if "태그" in cols:
        score += 30
    if "관광지명" in cols:
        score += 50

    return score


def score_event_file(file_path, df):
    """
    문화행사 파일인지 판별하는 점수
    """
    name = normalize_text(file_path.name)
    cols = get_column_names(df)

    score = 0

    if "문화행사" in name:
        score += 120
    elif "행사" in name:
        score += 80

    if "공연/행사명" in [str(c).strip() for c in df.columns]:
        score += 80
    if "공연행사명" in cols:
        score += 80
    if "행사명" in cols:
        score += 50
    if "장소" in cols:
        score += 30
    if "분류" in cols:
        score += 20

    return score


# =========================================================
# CSV 파일 자동 분류
# =========================================================
def load_and_classify_csv_files():
    """
    폴더 안 CSV 파일을 모두 읽고,
    문화공간 / 관광명소 / 문화행사 파일을 자동 판별
    """
    csv_files = get_csv_files()

    if not csv_files:
        st.error("❌ CSV 파일을 찾을 수 없습니다.")
        st.write("현재 폴더 파일 목록:")
        st.write([p.name for p in BASE_DIR.iterdir()])
        st.stop()

    loaded = []

    for file in csv_files:
        df_temp = read_csv_safely(file)
        loaded.append({
            "path": file,
            "df": df_temp,
            "culture_score": score_culture_file(file, df_temp),
            "tour_score": score_tour_file(file, df_temp),
            "event_score": score_event_file(file, df_temp),
        })

    # 점수 높은 파일 선택
    culture_item = max(loaded, key=lambda x: x["culture_score"])
    tour_item = max(loaded, key=lambda x: x["tour_score"])
    event_item = max(loaded, key=lambda x: x["event_score"])

    # 문화공간 파일은 필수
    if culture_item["culture_score"] <= 0:
        st.error("❌ 문화공간 CSV 파일을 판별하지 못했습니다.")
        st.write("현재 발견된 CSV 파일 목록:")
        st.write([item["path"].name for item in loaded])

        st.write("파일별 판별 점수:")
        score_table = pd.DataFrame([
            {
                "파일명": item["path"].name,
                "문화공간점수": item["culture_score"],
                "관광명소점수": item["tour_score"],
                "문화행사점수": item["event_score"],
                "컬럼": list(item["df"].columns)
            }
            for item in loaded
        ])
        st.dataframe(score_table, use_container_width=True)
        st.stop()

    culture_path = culture_item["path"]
    culture_df = culture_item["df"]

    # 관광/행사는 선택 데이터
    if tour_item["tour_score"] > 0 and tour_item["path"] != culture_path:
        tour_path = tour_item["path"]
        tour_df = tour_item["df"]
    else:
        tour_path = None
        tour_df = pd.DataFrame()

    if event_item["event_score"] > 0 and event_item["path"] != culture_path:
        event_path = event_item["path"]
        event_df = event_item["df"]
    else:
        event_path = None
        event_df = pd.DataFrame()

    return culture_df, tour_df, event_df, culture_path, tour_path, event_path, loaded


# =========================================================
# 컬럼명 정리
# =========================================================
def clean_column_names(df):
    """
    컬럼명 앞뒤 공백 제거 + 한글 정규화
    """
    df = df.copy()
    df.columns = [
        unicodedata.normalize("NFC", str(col)).strip()
        for col in df.columns
    ]
    return df


# =========================================================
# 문화공간 데이터 정리
# =========================================================
def normalize_culture_columns(df):
    """
    문화공간 데이터 컬럼명을 대시보드용으로 통일
    """
    df = clean_column_names(df)

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

    required_cols = [
        "시설명", "자치구", "유형", "주소",
        "위도", "경도", "무료구분",
        "관람료", "관람시간", "휴관일",
        "홈페이지", "전화번호"
    ]

    for col in required_cols:
        if col not in df.columns:
            df[col] = "정보없음"

    # 위도, 경도 숫자 변환
    df["위도"] = pd.to_numeric(df["위도"], errors="coerce")
    df["경도"] = pd.to_numeric(df["경도"], errors="coerce")

    # 텍스트 컬럼 결측 처리
    text_cols = [
        "시설명", "자치구", "유형", "주소",
        "무료구분", "관람료", "관람시간",
        "휴관일", "홈페이지", "전화번호"
    ]

    for col in text_cols:
        df[col] = df[col].fillna("정보없음")
        df[col] = df[col].astype(str)
        df[col] = df[col].replace("nan", "정보없음")
        df[col] = df[col].replace("", "정보없음")

    return df[required_cols]


# =========================================================
# 관광명소 데이터 정리
# =========================================================
def normalize_tour_columns(tour):
    if tour.empty:
        return pd.DataFrame(columns=["시설명", "주소", "유형"])

    tour = clean_column_names(tour)

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

        tour[col] = tour[col].fillna("정보없음")
        tour[col] = tour[col].astype(str)
        tour[col] = tour[col].replace("nan", "정보없음")
        tour[col] = tour[col].replace("", "정보없음")

    return tour[["시설명", "주소", "유형"]]


# =========================================================
# 문화행사 데이터 정리
# =========================================================
def normalize_event_columns(event):
    if event.empty:
        return pd.DataFrame(columns=["시설명", "주소", "유형"])

    event = clean_column_names(event)

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

        event[col] = event[col].fillna("정보없음")
        event[col] = event[col].astype(str)
        event[col] = event[col].replace("nan", "정보없음")
        event[col] = event[col].replace("", "정보없음")

    return event[["시설명", "주소", "유형"]]


# =========================================================
# 데이터 로드
# =========================================================
raw_culture, raw_tour, raw_event, culture_path, tour_path, event_path, loaded_files = load_and_classify_csv_files()

df = normalize_culture_columns(raw_culture)
tour = normalize_tour_columns(raw_tour)
event = normalize_event_columns(raw_event)


# =========================================================
# 불러온 파일 확인
# =========================================================
with st.expander("📁 불러온 파일 확인 / 디버깅"):
    st.write("문화공간 파일:", culture_path.name if culture_path else "없음")
    st.write("관광명소 파일:", tour_path.name if tour_path else "없음")
    st.write("문화행사 파일:", event_path.name if event_path else "없음")

    debug_df = pd.DataFrame([
        {
            "파일명": item["path"].name,
            "문화공간점수": item["culture_score"],
            "관광명소점수": item["tour_score"],
            "문화행사점수": item["event_score"],
            "컬럼수": len(item["df"].columns)
        }
        for item in loaded_files
    ])
    st.dataframe(debug_df, use_container_width=True)


# =========================================================
# SQLite DB 생성
# =========================================================
conn = sqlite3.connect(":memory:")

df.to_sql("culture_space", conn, index=False, if_exists="replace")
tour.to_sql("tour_place", conn, index=False, if_exists="replace")
event.to_sql("culture_event", conn, index=False, if_exists="replace")


# =========================================================
# 사이드바 필터
# =========================================================
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


# =========================================================
# KPI 영역
# =========================================================
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


# =========================================================
# 차트 1: 자치구별 문화시설 수
# =========================================================
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


# =========================================================
# 차트 2: 문화공간 유형 분포
# =========================================================
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


# =========================================================
# 차트 3: 무료 vs 유료 문화시설
# =========================================================
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


# =========================================================
# 지도 시각화
# =========================================================
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


# =========================================================
# 시설 목록 테이블
# =========================================================
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


# =========================================================
# 하단 안내
# =========================================================
st.divider()
st.caption("※ CSV 파일은 app.py와 같은 폴더 또는 하위 폴더에 있으면 자동으로 탐색됩니다.")

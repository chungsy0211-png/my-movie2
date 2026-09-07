import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


# --------------------------------------------------
# 1. 기본 설정
# --------------------------------------------------

st.set_page_config(
    page_title="어제의 박스오피스",
    page_icon="🎬",
    layout="wide"
)

st.title("🎬 어제의 박스오피스")
st.write("KOBIS 영화관입장권통합전산망의 일일 박스오피스 정보를 보여줍니다.")


# --------------------------------------------------
# 2. 한국 시간 기준으로 '어제' 날짜 계산
# --------------------------------------------------

# 배포 서버의 시간이 한국 시간이 아닐 수 있으므로
# 반드시 Asia/Seoul 시간대를 사용합니다.
korea_now = datetime.now(ZoneInfo("Asia/Seoul"))

# 오늘에서 하루를 빼서 어제 날짜를 구합니다.
yesterday = korea_now - timedelta(days=1)

# KOBIS API가 요구하는 YYYYMMDD 형식으로 변환합니다.
target_date = yesterday.strftime("%Y%m%d")

# 화면에는 보기 편한 날짜 형식으로 표시합니다.
display_date = yesterday.strftime("%Y년 %m월 %d일")

st.info(f"📅 조회 날짜: {display_date} (한국 시간 기준)")


# --------------------------------------------------
# 3. KOBIS API 호출 함수
# --------------------------------------------------

# 같은 날짜의 데이터를 1시간 동안 캐시합니다.
# 따라서 새로고침을 해도 1시간 이내에는 API를 다시 호출하지 않습니다.
@st.cache_data(ttl=3600)
def get_boxoffice(target_dt):
    # Streamlit Secrets에서 인증키를 가져옵니다.
    # 실제 인증키는 코드에 작성하지 않습니다.
    api_key = st.secrets["KOBIS_KEY"]

    # KOBIS 일일 박스오피스 API 주소
    url = (
        "https://www.kobis.or.kr/kobisopenapi/webservice/rest/"
        "boxoffice/searchDailyBoxOfficeList.json"
    )

    # API에 보낼 요청 데이터
    params = {
        "key": api_key,
        "targetDt": target_dt
    }

    try:
        # KOBIS API에 요청을 보냅니다.
        response = requests.get(
            url,
            params=params,
            timeout=10
        )

        # HTTP 오류가 발생하면 예외를 발생시킵니다.
        response.raise_for_status()

        # JSON 형태의 응답을 가져옵니다.
        data = response.json()

        return data, None

    except requests.exceptions.RequestException as e:
        # 인터넷 연결이나 API 요청에 문제가 있는 경우
        return None, f"API 요청에 실패했습니다: {e}"

    except ValueError:
        # JSON으로 변환할 수 없는 응답이 온 경우
        return None, "API 응답을 JSON 데이터로 읽을 수 없습니다."

    except Exception as e:
        # 그 밖의 예상하지 못한 오류
        return None, f"예상하지 못한 오류가 발생했습니다: {e}"


# --------------------------------------------------
# 4. API 호출
# --------------------------------------------------

data, error_message = get_boxoffice(target_date)


# --------------------------------------------------
# 5. 요청 자체가 실패한 경우
# --------------------------------------------------

if error_message:
    st.error("❌ 데이터를 가져오지 못했습니다.")

    st.warning(
        """
        다음 내용을 확인해 주세요.

        - 인터넷 연결이 정상인지 확인하세요.
        - KOBIS API 주소가 정상인지 확인하세요.
        - Streamlit Cloud의 Secrets에 `KOBIS_KEY`가 등록되어 있는지 확인하세요.
        - API 인증키가 정확한지 확인하세요.
        - KOBIS API 서버가 정상적으로 작동하는지 확인하세요.
        """
    )

    st.caption(f"오류 내용: {error_message}")

    st.stop()


# --------------------------------------------------
# 6. KOBIS의 faultInfo 오류 확인
# --------------------------------------------------

# KOBIS는 인증키가 잘못되어도 HTTP 상태코드가 200으로 올 수 있습니다.
# 따라서 faultInfo가 있는지 별도로 확인해야 합니다.
if "faultInfo" in data:
    fault_info = data["faultInfo"]

    st.error("❌ KOBIS API에서 오류를 반환했습니다.")

    st.warning(
        """
        인증키 또는 API 설정을 확인해 주세요.

        - Streamlit Cloud의 Secrets에 `KOBIS_KEY`가 있는지 확인하세요.
        - 인증키를 복사할 때 앞뒤에 불필요한 공백이 없는지 확인하세요.
        - KOBIS에서 발급받은 인증키가 현재 사용할 수 있는 키인지 확인하세요.
        """
    )

    # KOBIS가 보내준 오류 내용을 보여줍니다.
    if isinstance(fault_info, dict):
        for key, value in fault_info.items():
            st.write(f"**{key}**: {value}")
    else:
        st.write(fault_info)

    st.stop()


# --------------------------------------------------
# 7. 박스오피스 결과 확인
# --------------------------------------------------

boxoffice_result = data.get("boxOfficeResult")

if not boxoffice_result:
    st.error("❌ 박스오피스 결과가 없습니다.")

    st.warning(
        """
        KOBIS API의 응답에 `boxOfficeResult`가 있는지 확인할 수 없습니다.

        잠시 후 다시 시도하거나 KOBIS API 서버 상태를 확인해 주세요.
        """
    )

    st.stop()


# 영화 목록 가져오기
movie_list = boxoffice_result.get("dailyBoxOfficeList", [])


# 영화 목록이 비어 있는 경우
if not movie_list:
    st.error("❌ 조회된 영화 목록이 없습니다.")

    st.warning(
        f"""
        {display_date}의 박스오피스 데이터가 비어 있습니다.

        다음 내용을 확인해 주세요.

        - 조회 날짜가 올바른지 확인하세요.
        - KOBIS에서 해당 날짜의 박스오피스 자료가 제공되는지 확인하세요.
        - API 인증키가 정상인지 확인하세요.
        - 잠시 후 다시 실행해 보세요.
        """
    )

    st.stop()


# --------------------------------------------------
# 8. 데이터를 표로 만들기
# --------------------------------------------------

# API에서 받은 영화 데이터를 DataFrame으로 변환합니다.
df = pd.DataFrame(movie_list)


# --------------------------------------------------
# 9. 숫자로 변환
# --------------------------------------------------

# KOBIS API에서는 숫자도 문자열로 전달되므로
# 정렬과 그래프를 위해 숫자형으로 변환합니다.

numeric_columns = [
    "rank",
    "audiCnt",
    "audiAcc",
    "scrnCnt"
]

for column in numeric_columns:
    df[column] = pd.to_numeric(
        df[column],
        errors="coerce"
    ).fillna(0).astype(int)


# --------------------------------------------------
# 10. 순위 기준으로 정렬
# --------------------------------------------------

df = df.sort_values("rank")


# --------------------------------------------------
# 11. 1위 영화 정보
# --------------------------------------------------

first_movie = df.iloc[0]

movie_name = first_movie["movieNm"]
today_audience = first_movie["audiCnt"]
total_audience = first_movie["audiAcc"]
screen_count = first_movie["scrnCnt"]


# --------------------------------------------------
# 12. 1위 영화 지표 카드
# --------------------------------------------------

st.subheader(f"🥇 1위: {movie_name}")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "어제 관객수",
        f"{today_audience:,}명"
    )

with col2:
    st.metric(
        "누적 관객수",
        f"{total_audience:,}명"
    )

with col3:
    st.metric(
        "스크린 수",
        f"{screen_count:,}개"
    )


# --------------------------------------------------
# 13. 전체 박스오피스 표
# --------------------------------------------------

st.subheader("📊 어제의 박스오피스")

# 화면에 보여줄 열만 선택합니다.
display_df = df[
    [
        "rank",
        "movieNm",
        "openDt",
        "audiCnt",
        "audiAcc",
        "scrnCnt"
    ]
].copy()

# 표에 표시할 한국어 이름으로 변경합니다.
display_df.columns = [
    "순위",
    "영화명",
    "개봉일",
    "관객수",
    "누적관객",
    "스크린수"
]

# 숫자를 천 단위 쉼표가 들어간 문자열로 표시합니다.
# 내부 DataFrame에서는 숫자형으로 유지했기 때문에
# 정렬과 그래프에는 숫자 데이터가 사용됩니다.
display_df["관객수"] = display_df["관객수"].map(
    lambda x: f"{x:,}"
)

display_df["누적관객"] = display_df["누적관객"].map(
    lambda x: f"{x:,}"
)

display_df["스크린수"] = display_df["스크린수"].map(
    lambda x: f"{x:,}"
)

# 전체 표를 보여줍니다.
st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True
)


# --------------------------------------------------
# 14. 관객수 상위 5편 막대그래프
# --------------------------------------------------

st.subheader("📈 관객수 상위 5편")

# 관객수가 많은 순서로 정렬합니다.
top5 = df.sort_values(
    "audiCnt",
    ascending=False
).head(5).copy()

# 그래프에 사용할 데이터만 선택합니다.
chart_df = top5[
    ["movieNm", "audiCnt"]
].set_index("movieNm")

# Streamlit의 막대그래프를 사용합니다.
st.bar_chart(
    chart_df,
    y="audiCnt",
    use_container_width=True
)

st.caption(
    "※ 관객수는 해당 날짜의 일일 관객수이며, "
    "KOBIS API에서 제공한 데이터를 사용합니다."
)

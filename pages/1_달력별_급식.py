import datetime
import re

import requests
import streamlit as st


MEAL_URL = (
    "https://open.neis.go.kr/"
    "hub/mealServiceDietInfo"
)

OFFICE_CODE = "J10"
SCHOOL_CODE = "7530480"
SCHOOL_NAME = "송탄고등학교"


st.set_page_config(
    page_title="달력별 급식",
    page_icon="📅",
    layout="wide",
)


st.title(
    "📅 송탄고등학교 달력별 급식"
)

st.caption(
    "날짜를 선택하면 해당 날짜의 중식 메뉴를 확인합니다."
)


# 한국 시간 기준 오늘
today_kst = (
    datetime.datetime.utcnow()
    + datetime.timedelta(hours=9)
).date()


c1, c2 = st.columns([1, 1])


with c1:

    picked = st.date_input(
        "날짜",
        value=today_kst,
    )


with c2:

    show_allergen = st.toggle(
        "알레르기 정보 보기",
        value=True,
    )


ymd = picked.strftime("%Y%m%d")


@st.cache_data(ttl=300)
def get_meal(ymd):

    response = requests.get(
        MEAL_URL,
        params={
            "Type": "json",
            "ATPT_OFCDC_SC_CODE": OFFICE_CODE,
            "SD_SCHUL_CODE": SCHOOL_CODE,
            "MMEAL_SC_CODE": "2",
            "MLSV_FROM_YMD": ymd,
            "MLSV_TO_YMD": ymd,
        },
        timeout=15,
    )

    response.raise_for_status()

    data = response.json()


    if "mealServiceDietInfo" not in data:

        result = data.get(
            "RESULT",
            {},
        )

        if result.get("CODE") == "INFO-200":

            return None

        raise ValueError(
            result.get(
                "MESSAGE",
                "급식 조회에 실패했습니다.",
            )
        )


    rows = data[
        "mealServiceDietInfo"
    ][1].get(
        "row",
        [],
    )


    if not rows:
        return None


    return rows[0]


try:

    meal = get_meal(ymd)

except (
    requests.RequestException,
    ValueError,
) as error:

    st.error(
        f"급식 조회에 실패했습니다: {error}"
    )

    st.stop()


if meal is None:

    st.info(
        "급식이 없는 날입니다."
    )

    st.stop()


raw_dishes = [
    d.strip()
    for d in meal.get(
        "DDISH_NM",
        "",
    ).split("<br/>")
    if d.strip()
]


def format_dish(dish):

    if show_allergen:

        return dish

    return re.sub(
        r"\s*\([0-9.]+\)",
        "",
        dish,
    ).strip()


dishes = [
    format_dish(d)
    for d in raw_dishes
]


st.subheader(
    f"{SCHOOL_NAME} · "
    f"{picked.strftime('%Y년 %m월 %d일')} 중식"
)


m1, m2 = st.columns(2)


m1.metric(
    "메뉴 가짓수",
    f"{len(dishes)}개",
)


m2.metric(
    "칼로리",
    meal.get(
        "CAL_INFO",
        "-",
    ),
)


st.markdown(
    "### 🍽️ 메뉴"
)


cols = st.columns(3)


for i, dish in enumerate(dishes):

    with cols[i % 3]:

        st.container(
            border=True
        ).write(
            f"**{i + 1}. {dish}**"
        )


with st.expander(
    "원본 메뉴 데이터"
):

    st.code(
        meal.get(
            "DDISH_NM",
            "",
        ),
        language="text",
    )


with st.expander(
    "원산지 정보"
):

    st.write(
        meal.get(
            "ORPLC_INFO",
            "제공된 원산지 정보가 없습니다.",
        )
    )


st.caption(
    "괄호 속 숫자는 나이스 API의 "
    "알레르기 유발 식품 번호입니다."
)

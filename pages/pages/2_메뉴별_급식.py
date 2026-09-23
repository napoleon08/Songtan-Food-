import re

import pandas as pd
import plotly.express as px
import requests
import streamlit as st


MEAL_URL = (
    "https://open.neis.go.kr/"
    "hub/mealServiceDietInfo"
)

OFFICE_CODE = "J10"
SCHOOL_CODE = "7530480"


st.set_page_config(
    page_title="메뉴별 급식",
    page_icon="🥇",
    layout="wide",
)


st.title(
    "🥇 조회 기간의 최다 등장 메뉴"
)

st.caption(
    "인증키를 사용해 조회 기간 전체의 중식을 "
    "모아 메뉴 등장 빈도를 계산합니다."
)


# --------------------------------
# API KEY
# --------------------------------

try:

    api_key = st.secrets[
        "NEIS_API_KEY"
    ]

except Exception:

    st.error(
        "Secrets에 NEIS_API_KEY가 없습니다."
    )

    st.info(
        'Streamlit 앱의 Settings → Secrets에 '
        '다음 한 줄을 넣으세요:\n\n'
        'NEIS_API_KEY = "발급받은_인증키"'
    )

    st.stop()


# --------------------------------
# 전체 급식 데이터 가져오기
# --------------------------------

@st.cache_data(ttl=1800)
def load_lunch(
    frm,
    to,
    api_key,
):

    days = {}

    page = 1

    received = 0


    while True:

        response = requests.get(
            MEAL_URL,
            params={
                "Type": "json",

                "KEY": api_key,

                "pSize": 1000,

                "pIndex": page,

                "ATPT_OFCDC_SC_CODE":
                    OFFICE_CODE,

                "SD_SCHUL_CODE":
                    SCHOOL_CODE,

                "MMEAL_SC_CODE":
                    "2",

                "MLSV_FROM_YMD":
                    frm,

                "MLSV_TO_YMD":
                    to,
            },

            timeout=30,
        )


        response.raise_for_status()


        data = response.json()


        if (
            "mealServiceDietInfo"
            not in data
        ):

            result = data.get(
                "RESULT",
                {},
            )


            if (
                result.get("CODE")
                == "INFO-200"
                and page == 1
            ):

                return {}


            raise ValueError(
                result.get(
                    "MESSAGE",
                    "급식 데이터를 "
                    "가져오지 못했습니다.",
                )
            )


        head = data[
            "mealServiceDietInfo"
        ][0].get(
            "head",
            [],
        )


        total = next(
            (
                item[
                    "list_total_count"
                ]

                for item in head

                if "list_total_count"
                in item
            ),

            0,
        )


        rows = data[
            "mealServiceDietInfo"
        ][1].get(
            "row",
            [],
        )


        if not rows:

            raise ValueError(
                f"전체 {total}건인데 "
                "받은 데이터가 없습니다. "
                "인증키를 확인하세요."
            )


        # --------------------------------
        # 메뉴 정리
        # --------------------------------

        for row in rows:

            dishes = []


            for dish in row.get(
                "DDISH_NM",
                "",
            ).split("<br/>"):

                clean = re.sub(
                    r"\s*\([0-9.]+\)",
                    "",
                    dish,
                ).strip()


                clean = re.sub(
                    r"\s+",
                    " ",
                    clean,
                )


                if clean:

                    dishes.append(
                        clean
                    )


            # 같은 날짜의 같은 메뉴가
            # 두 번 나와도 하루로 계산

            days.setdefault(
                row["MLSV_YMD"],
                set(),
            ).update(dishes)


        received += len(rows)


        # 전체 데이터 수를 받았으면 종료

        if received >= total:

            return days


        # 1000개보다 적게 왔는데
        # 전체 수보다 적으면 문제

        if len(rows) < 1000:

            raise ValueError(
                f"전체 {total}건 중 "
                f"{received}건만 받았습니다. "
                "인증키 또는 페이지 요청을 확인하세요."
            )


        page += 1


# --------------------------------
# 데이터 가져오기
# --------------------------------

try:

    meals = load_lunch(
        "20250901",
        "20260930",
        api_key,
    )

except (
    requests.RequestException,
    ValueError,
) as error:

    st.error(
        str(error)
    )

    st.stop()


if not meals:

    st.info(
        "조회 기간의 급식 정보가 없습니다."
    )

    st.stop()


days = len(meals)


# --------------------------------
# 메뉴별 등장 횟수 계산
# --------------------------------

counts = (
    pd.Series(
        [
            dish

            for dishes
            in meals.values()

            for dish
            in dishes
        ]
    )

    .value_counts()

    .rename_axis("메뉴")

    .reset_index(
        name="일수"
    )
)


counts["비율(%)"] = (
    counts["일수"]
    / days
    * 100
).round(1)


# --------------------------------
# TOP N 선택
# --------------------------------

top_n = st.slider(
    "몇 위까지 볼까요?",
    min_value=5,
    max_value=min(
        20,
        len(counts),
    ),
    value=min(
        10,
        len(counts),
    ),
)


top = counts.head(
    top_n
).copy()


top.insert(
    0,
    "순위",
    range(
        1,
        len(top) + 1,
    ),
)


# --------------------------------
# 큰 숫자 카드
# --------------------------------

first = top.iloc[0]


c1, c2, c3 = st.columns(3)


c1.metric(
    "집계한 급식일",
    f"{days}일",
)


c2.metric(
    "1위 메뉴",
    first["메뉴"],
)


c3.metric(
    "1위 등장 비율",
    f"{first['비율(%)']}%",
)


# --------------------------------
# 그래프용 텍스트
# --------------------------------

top["표시"] = (
    top["일수"].astype(str)
    + "일 ("
    + top["비율(%)"].astype(str)
    + "%)"
)


# --------------------------------
# Plotly 그래프
# --------------------------------

fig = px.bar(
    top.sort_values(
        "일수"
    ),

    x="일수",

    y="메뉴",

    orientation="h",

    text="표시",

    color="일수",

    color_continuous_scale="Oranges",

    title=(
        f"중식 {days}일 중 "
        f"가장 자주 나온 메뉴 "
        f"TOP {top_n}"
    ),
)


fig.update_layout(
    coloraxis_showscale=False,

    xaxis_title="등장 일수",

    yaxis_title="",
)


st.plotly_chart(
    fig,
    width="stretch",
)


# --------------------------------
# 표
# --------------------------------

st.dataframe(
    top[
        [
            "순위",
            "메뉴",
            "일수",
            "비율(%)",
        ]
    ],

    hide_index=True,

    width="stretch",
)


st.caption(
    "이 그래프로 알 수 있는 것: "
    "조회 기간 동안 어떤 메뉴가 "
    "반복적으로 등장했는지 비교할 수 있습니다."
)

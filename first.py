# app.py
import io
import datetime as dt
import requests
import pandas as pd
import streamlit as st

API_TOKEN = "68fa2f405fccb1.86547776d0fd5ab136d4a7ab48903d2c9c8558ef"  # hardcoded as requested

st.set_page_config(page_title="Отчёт по категории", layout="wide")
st.title("Отчёт по категории")

# --- Inputs ---
col1, col2, col3 = st.columns([1,1,2])
with col1:
    category = st.selectbox("Категория", ["Сапоги", "Туфли"])
with col2:
    end_default = dt.date.today()
    start_default = end_default - dt.timedelta(days=14)
    d1, d2 = st.date_input("Период (d1 → d2)", value=(start_default, end_default), format="DD.MM.YYYY")
with col3:
    st.markdown("**Поля отчёта (на данном этапе):**")
    fields_list = [
        "name", "id", "thumb", "url", "balance",
        "lost_profit (или loss_profit)", "stocks_graph",
        "sales", "revenue", "start_price", "basic_sale"
    ]
    st.markdown("- " + "\n- ".join(fields_list))

# Map UI category to MPStats path (same path logic as your working code)
PATHS = {
    "Туфли": "Женщинам/Свадьба/Обувь для невесты/Туфли",
    "Сапоги": "Женщинам/Свадьба/Обувь для невесты/Сапоги",
}
path = PATHS[category]

def to_https(u):
    return ("https:" + u) if isinstance(u, str) and isinstance(u, str) and u.startswith("//") else u

def fetch_rows(token: str, d1_str: str, d2_str: str, path: str, page_size: int = 200) -> list[dict]:
    URL = "https://mpstats.io/api/wb/get/category"
    HEADERS = {"X-Mpstats-TOKEN": token, "Content-Type": "application/json"}
    page = 0
    all_rows: list[dict] = []
    while True:
        params = {"d1": d1_str, "d2": d2_str, "path": path}
        payload = {
            "startRow": page * page_size,
            "endRow": (page + 1) * page_size,
            "filterModel": {},
            "sortModel": [{"colId": "revenue", "sort": "desc"}],
        }
        r = requests.post(URL, headers=HEADERS, params=params, json=payload, timeout=60)
        r.raise_for_status()
        data = r.json().get("data", [])
        if not data:
            break
        all_rows.extend(data)
        if len(data) < page_size:
            break
        page += 1
    return all_rows

def rows_to_df(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame([{
        "name": it.get("name"),
        "id": it.get("id"),
        "thumb": to_https(it.get("thumb")),
        "url": it.get("url"),
        "balance": it.get("balance"),
        "loss_profit": it.get("lost_profit") if it.get("lost_profit") is not None else it.get("loss_profit"),
        "stocks_graph": it.get("stocks_graph"),
        "sales": it.get("sales"),
        "revenue": it.get("revenue"),
        "start_price": it.get("start_price"),
        "basic_sale": it.get("basic_sale"),
    } for it in rows])

st.divider()
if st.button("Сформировать отчёт и скачать CSV", type="primary"):
    if d1 > d2:
        st.error("Дата начала (d1) не может быть позже даты окончания (d2).")
    else:
        d1_str, d2_str = d1.strftime("%Y-%m-%d"), d2.strftime("%Y-%m-%d")
        with st.spinner(f"Загружаем: {path} ({d1_str} → {d2_str})…"):
            try:
                rows = fetch_rows(API_TOKEN, d1_str, d2_str, path)
                df = rows_to_df(rows)
            except requests.HTTPError as e:
                st.error(f"HTTP ошибка: {e.response.status_code} — {e.response.text}")
                st.stop()
            except Exception as e:
                st.error(f"Ошибка: {e}")
                st.stop()

        st.success(f"Найдено записей: {len(df)}")
        if len(df):
            st.dataframe(df.head(20), use_container_width=True)
            buf = io.StringIO()
            df.to_csv(buf, index=False)
            st.download_button(
                label="⬇️ Скачать CSV",
                data=buf.getvalue().encode("utf-8-sig"),
                file_name=f"mpstats_{category}_{d1_str}_to_{d2_str}.csv",
                mime="text/csv"
            )
        else:
            st.info("По выбранным фильтрам данных не найдено.")

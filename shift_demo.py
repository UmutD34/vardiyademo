import json
import os
from datetime import datetime

import pandas as pd
import streamlit as st

# ────────────────────────────────────────────────────────────────────────────────
# CONFIG & PAGE SETUP
# ────────────────────────────────────────────────────────────────────────────────
PAGE_TITLE = "Şişecam Paşabahçe Otomatik Vardiya Sistemi"
st.set_page_config(page_title=PAGE_TITLE, page_icon="📆", layout="wide")
PRIMARY = "#0D4C92"  # kurumsal mavi
st.markdown(
    f"""
    <style>
      div.block-container {{padding-top:1rem}}
      .st-emotion-cache-fblp2m {{color:{PRIMARY}!important}}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title(PAGE_TITLE)

DATA_FILE = "data.json"  # basit kalıcılık

# ────────────────────────────────────────────────────────────────────────────────
# HELPER – LOAD / SAVE
# ────────────────────────────────────────────────────────────────────────────────

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    # varsayılan yapı
    return {
        "users": {
            "admin": "1234",
            "fatihdemir": "123456",
            "ademkeles": "123456",
        },
        "employees": [],
        "scenario": {"ht_rule": True, "max_work_days": 6},
        "history": [],
    }


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# state
if "db" not in st.session_state:
    st.session_state["db"] = load_data()
DB = st.session_state["db"]

# ────────────────────────────────────────────────────────────────────────────────
# AUTH
# ────────────────────────────────────────────────────────────────────────────────
if "user" not in st.session_state:
    st.header("🔐 Yönetici Girişi")
    col1, col2 = st.columns(2)
    u = col1.text_input("Kullanıcı Adı")
    p = col2.text_input("Şifre", type="password")
    if st.button("Giriş"):
        if u in DB["users"] and DB["users"][u] == p:
            st.session_state["user"] = u
            save_data(DB)  # güvenli tarafta
            st.rerun()
        else:
            st.error("Hatalı kullanıcı veya şifre")
    st.stop()

# ────────────────────────────────────────────────────────────────────────────────
# SABİT TABLOLAR / KISALTMA
# ────────────────────────────────────────────────────────────────────────────────
MENU = st.sidebar.radio("Menü", ["Vardiya Oluştur", "Ayarlar", "Geçmiş"], index=0)
SHIFT_MAP = {
    "Sabah": "09:30‑18:00",
    "Ara": "11:30‑20:00",
    "Akşam": "13:30‑22:00",
    "H.T": "Haftalık Tatil",
    "PT": "Part‑time İzin",
}
DAYS = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]

# ────────────────────────────────────────────────────────────────────────────────
# AYARLAR
# ────────────────────────────────────────────────────────────────────────────────
if MENU == "Ayarlar":
    st.header("⚙️  Ayarlar")

    st.subheader("Çalışan Listesi")
    with st.expander("Yeni Çalışan Ekle"):
        c1, c2 = st.columns(2)
        name = c1.text_input("İsim")
        sicil = c2.text_input("Sicil No")
        is_pt = st.checkbox("Part‑time mi?")
        ht_day = st.selectbox("Haftalık Tatil Günü", DAYS, index=6)
        pt_days = st.multiselect("PT İzin Günleri (PT ise)", DAYS)
        if st.button("Ekle") and name and sicil:
            DB["employees"].append({
                "name": name,
                "sicil": sicil,
                "pt": is_pt,
                "pt_days": pt_days,
                "ht_day": ht_day,
            })
            save_data(DB)
            st.success(f"{name} eklendi ✔️")

    if DB["employees"]:
        st.dataframe(pd.DataFrame(DB["employees"]), use_container_width=True)

    st.divider()
    st.subheader("Kullanıcı Yönetimi")
    nu = st.text_input("Yeni kullanıcı")
    npass = st.text_input("Şifre", type="password")
    if st.button("Kullanıcı Ekle") and nu and npass:
        DB["users"][nu] = npass
        save_data(DB)
        st.success("Kullanıcı eklendi")

# ────────────────────────────────────────────────────────────────────────────────
# VARDİYA OLUŞTUR
# ────────────────────────────────────────────────────────────────────────────────
if MENU == "Vardiya Oluştur":
    st.header("🗓️  Yeni Vardiya Oluştur")
    if not DB["employees"]:
        st.warning("Önce Ayarlar sayfasından çalışan ekleyin.")
        st.stop()

    week_start = st.date_input("Haftanın Pazartesi tarihi", datetime.today())
    if st.button("Vardiyayı Oluştur 🛠️"):
        def prev(emp_name):
            if not DB["history"]:
                return None
            for r in DB["history"][-1]["schedule"]:
                if r["Çalışan"] == emp_name:
                    return r
            return None

        rows = []
        for emp in DB["employees"]:
            row = {"Çalışan": emp["name"], "Sicil": emp["sicil"]}
            last = prev(emp["name"])
            for idx, day in enumerate(DAYS):
                if emp["pt"] and day in emp["pt_days"]:
                    row[day] = "PT"; continue
                if day == emp["ht_day"]:
                    row[day] = "H.T"; continue
                if DAYS[(idx + 1) % 7] == emp["ht_day"]:
                    row[day] = "Sabah"; continue
                if DAYS[(idx - 1) % 7] == emp["ht_day"]:
                    row[day] = "Ara"; continue
                prop = "Sabah" if (idx + len(emp["name"])) % 2 == 0 else "Akşam"
                if last and last.get(day) == prop:
                    prop = "Akşam" if prop == "Sabah" else "Sabah"
                if idx > 0 and row[DAYS[idx - 1]] == prop:
                    prop = "Akşam" if prop == "Sabah" else "Sabah"
                row[day] = prop
            rows.append(row)

        df = pd.DataFrame(rows)
        pretty = df.copy()
        for d in DAYS:
            pretty[d] = pretty[d].map(lambda x: SHIFT_MAP.get(x, x))

        st.subheader("🔍 Oluşturulan Vardiya")
        st.dataframe(pretty, use_container_width=True)

        DB["history"].append({"week_start": str(week_start), "schedule": df.to_dict("records")})
        save_data(DB)

        st.download_button("Excel'e Aktar (CSV)", pretty.to_csv(index=False).encode("utf-8-sig"), file_name="vardiya.csv")

# ────────────────────────────────────────────────────────────────────────────────
# GEÇMİŞ
# ────────────────────────────────────────────────────────────────────────────────
if MENU == "Geçmiş":
    st.header("📑 Geçmiş Vardiyalar")
    if not DB["history"]:
        st.info("Henüz kayıt yok.")
    else:
        opts = [f"Hafta: {rec['week_start']}" for rec in DB["history"][::-1]]
        choose = st.selectbox("Hafta seç", opts)
        rec = DB["history"][::-1][opts.index(choose)]
        hd = pd.DataFrame(rec["schedule"])
        for d in DAYS:
            hd[d] = hd[d].map(lambda x: SHIFT_MAP.get(x, x))
        st.dataframe(hd, use_container_width=True)

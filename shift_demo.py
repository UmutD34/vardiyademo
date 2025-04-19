import json
import os
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

# ────────────────────────────────────────────────────────────────────────────────
# CONFIG & PAGE SETUP
# ────────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Palladium Vardiya", page_icon="📆", layout="wide"
)

PRIMARY = "#0D4C92"  # kurumsal mavi (Paşabahçe‑Şişecam tonunda)

st.markdown(
    f"<style>div.block-container{{padding-top:1rem}} .st-emotion-cache-fblp2m{{color:{PRIMARY}!important}}</style>",
    unsafe_allow_html=True,
)

DATA_FILE = "data.json"  # basit yerel kalıcılık (Spaces/Railway diskinde de çalışır)

# ────────────────────────────────────────────────────────────────────────────────
# HELPER FNS – PERSISTENCE
# ────────────────────────────────────────────────────────────────────────────────

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    # default structure
    return {
        "users": {"admin": "1234"},  # username:password (demo)
        "employees": [],  # {name, sicil, pt, pt_days[], ht_day}
        "scenario": {
            "ht_rule": True,
            "max_work_days": 6,
        },
        "history": [],  # list of {week_start, schedule(df.to_dict())}
    }


def save_data(d):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)


if "db" not in st.session_state:
    st.session_state["db"] = load_data()

DB = st.session_state["db"]

# ────────────────────────────────────────────────────────────────────────────────
# AUTHENTICATION (VERY BASIC DEMO)
# ────────────────────────────────────────────────────────────────────────────────
if "user" not in st.session_state:
    st.subheader("🔐 Yönetici Giriş")
    u = st.text_input("Kullanıcı Adı")
    p = st.text_input("Şifre", type="password")
    if st.button("Giriş"):
        if u in DB["users"] and DB["users"][u] == p:
            st.session_state["user"] = u
            st.experimental_rerun()
        else:
            st.error("Hatalı kullanıcı veya şifre")
    st.stop()

# ────────────────────────────────────────────────────────────────────────────────
# NAVIGATION
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
# AYARLAR SAYFASI
# ────────────────────────────────────────────────────────────────────────────────
if MENU == "Ayarlar":
    st.header("⚙️  Ayarlar")

    st.subheader("Çalışan Listesi")
    with st.expander("Yeni Çalışan Ekle"):
        col1, col2 = st.columns(2)
        name = col1.text_input("İsim")
        sicil = col2.text_input("Sicil No")
        is_pt = st.checkbox("Part‑time mi?")
        ht = st.selectbox("Haftalık Tatil Günü", DAYS, index=6)
        pt_days = st.multiselect("PT İzin Günleri (sadece PT ise)", DAYS)
        if st.button("Ekle") and name and sicil:
            DB["employees"].append(
                {
                    "name": name,
                    "sicil": sicil,
                    "pt": is_pt,
                    "pt_days": pt_days,
                    "ht_day": ht,
                }
            )
            save_data(DB)
            st.success(f"{name} eklendi")

    # mevcut tablo
    if DB["employees"]:
        df_emp = pd.DataFrame(DB["employees"])
        st.dataframe(df_emp, use_container_width=True)

    st.divider()
    st.subheader("Giriş Bilgileri")
    new_user = st.text_input("Yeni kullanıcı adı")
    new_pass = st.text_input("Şifre", type="password")
    if st.button("Kullanıcı Ekle") and new_user and new_pass:
        DB["users"][new_user] = new_pass
        save_data(DB)
        st.success("Kullanıcı eklendi")

# ────────────────────────────────────────────────────────────────────────────────
# VARDİYA OLUŞTUR SAYFASI
# ────────────────────────────────────────────────────────────────────────────────
if MENU == "Vardiya Oluştur":
    st.header("🗓️  Yeni Vardiya Oluştur")
    if not DB["employees"]:
        st.warning("Önce Ayarlar menüsünden çalışan ekleyin.")
        st.stop()

    week_start = st.date_input("Haftanın Pazartesi tarihi", datetime.today())
    generate = st.button("Vardiyayı Oluştur 🛠️")

    def last_schedule(emp_name):
        """Return last week's row dict for emp_name if exists"""
        if not DB["history"]:
            return None
        last = DB["history"][-1]["schedule"]
        for r in last:
            if r["Çalışan"] == emp_name:
                return r
        return None

    def build_schedule():
        rows = []
        for emp in DB["employees"]:
            row = {"Çalışan": emp["name"], "Sicil": emp["sicil"]}
            last = last_schedule(emp["name"])
            for d_idx, day in enumerate(DAYS):
                # PT izin günleri
                if emp["pt"] and day in emp["pt_days"]:
                    row[day] = "PT"
                    continue
                # HT bireysel
                if day == emp["ht_day"]:
                    row[day] = "H.T"
                    continue
                # HT kuralı: önceki gün Sabah, ertesi gün Ara
                if DAYS[(d_idx + 1) % 7] == emp["ht_day"]:
                    row[day] = "Sabah"
                    continue
                if DAYS[(d_idx - 1) % 7] == emp["ht_day"]:
                    row[day] = "Ara"
                    continue
                # Adalet: bir önceki haftada aynı vardiya geldiyse değiştir
                proposed = "Sabah" if (d_idx + len(emp["name"])) % 2 == 0 else "Akşam"
                if last and last.get(day) == proposed:
                    proposed = "Akşam" if proposed == "Sabah" else "Sabah"
                # Üst üste kontrol (demo: sadece önceki gün)
                if d_idx > 0 and row[DAYS[d_idx - 1]] == proposed:
                    proposed = "Akşam" if proposed == "Sabah" else "Sabah"
                row[day] = proposed
            rows.append(row)
        return pd.DataFrame(rows)

    if generate:
        sched_df = build_schedule()
        st.subheader("🔍 Oluşturulan Vardiya")
        # saatlere dönüştürülmüş görünüm
        pretty = sched_df.copy()
        for d in DAYS:
            pretty[d] = pretty[d].map(lambda x: SHIFT_MAP.get(x, x))
        st.dataframe(pretty, use_container_width=True)

        # kaydet
        DB["history"].append(
            {
                "week_start": str(week_start),
                "schedule": sched_df.to_dict(orient="records"),
            }
        )
        save_data(DB)

        # excel export
        csv = pretty.to_csv(index=False).encode("utf-8-sig")
        st.download_button("Excel'e Aktar (CSV)", csv, file_name="vardiya.csv")

# ────────────────────────────────────────────────────────────────────────────────
# GEÇMİŞ PROGRAMLAR
# ────────────────────────────────────────────────────────────────────────────────
if MENU == "Geçmiş":
    st.header("📑 Geçmiş Vardiyalar")
    if not DB["history"]:
        st.info("Henüz kayıt yok.")
    else:
        options = [f"Hafta başlangıç: {rec['week_start']}" for rec in DB["history"][::-1]]
        choice = st.selectbox("Görüntülenecek hafta", options)
        rec = DB["history"][::-1][options.index(choice)]
        hist_df = pd.DataFrame(rec["schedule"])
        for d in DAYS:
            hist_df[d] = hist_df[d].map(lambda x: SHIFT_MAP.get(x, x))
        st.dataframe(hist_df, use_container_width=True)

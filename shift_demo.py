import json
import os
from datetime import datetime

import pandas as pd
import streamlit as st

# ────────────────────────────────────────────────────────────────────────────────
# KURUMSAL SABİTLER
# ────────────────────────────────────────────────────────────────────────────────
PAGE_TITLE = "Şişecam Paşabahçe | Otomatik Vardiya Sistemi"
PRIMARY = "#0D4C92"
DATA_FILE = "data.json"  # basit JSON kalıcılığı (kullanıcı bazlı)
DAYS = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
SHIFT_MAP = {
    "Sabah": "09:30‑18:00",
    "Ara": "11:30‑20:00",
    "Akşam": "13:30‑22:00",
    "H.T": "Haftalık Tatil",
    "PT": "Part‑time İzin",
}

st.set_page_config(page_title=PAGE_TITLE, page_icon="📆", layout="wide")
st.markdown(
    f"<style>div.block-container{{padding-top:1rem}}.st-emotion-cache-fblp2m{{color:{PRIMARY}!important}}</style>",
    unsafe_allow_html=True,
)
st.title(PAGE_TITLE)

# ────────────────────────────────────────────────────────────────────────────────
# VERİ TABANI – YÖNETİCİ BAZLI
# ────────────────────────────────────────────────────────────────────────────────

def load_db():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "users": {
            "admin": "1234",
            "fatihdemir": "123456",
            "ademkeles": "123456",
        },
        "managers": {},  # username→{employees, scenario, history}
    }


def save_db(db):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)


if "db" not in st.session_state:
    st.session_state["db"] = load_db()
DB = st.session_state["db"]

# ────────────────────────────────────────────────────────────────────────────────
# GİRİŞ EKRANI
# ────────────────────────────────────────────────────────────────────────────────
if "user" not in st.session_state:
    st.subheader("🔐 Yönetici Girişi")
    c1, c2 = st.columns(2)
    uname = c1.text_input("Kullanıcı Adı")
    upass = c2.text_input("Şifre", type="password")
    if st.button("Giriş"):
        if DB["users"].get(uname) == upass:
            if uname not in DB["managers"]:
                DB["managers"][uname] = {
                    "employees": [],
                    "scenario": {
                        "type": "balance",  # balance | split
                        "ask_ara": False,
                    },
                    "history": [],
                }
                save_db(DB)
            st.session_state["user"] = uname
            st.rerun()
        else:
            st.error("Hatalı giriş")
    st.stop()

USER = st.session_state["user"]
MGR = DB["managers"][USER]

# ────────────────────────────────────────────────────────────────────────────────
# YAN MENÜ (kurumsal)
# ────────────────────────────────────────────────────────────────────────────────
st.sidebar.title("🚀 Menü")
MENU = st.sidebar.radio("İşlem Seç", ["Vardiya Oluştur", "Veriler", "Geçmiş"], index=0)

# ────────────────────────────────────────────────────────────────────────────────
# VERİLER (ÇALIŞAN + SENARYO)
# ────────────────────────────────────────────────────────────────────────────────
if MENU == "Veriler":
    st.header("📂 Veriler")

    # Senaryo Ayarı
    st.subheader("Senaryo Ayarları")
    scen = st.radio(
        "Haftalık Dağıtım Senaryosu",
        {
            "balance": "Adalet: herkes 3 Sabah + 3 Akşam",
            "split": "Karma: çalışanların yarısı sürekli Sabah, yarısı Akşam",
        },
        index=0 if MGR["scenario"]["type"] == "balance" else 1,
        key="scenario_type",
    )
    ask_ara = st.checkbox("Ara vardiyalarını her hafta manuel seçmek istiyorum", value=MGR["scenario"].get("ask_ara", False))
    if st.button("Kaydet Senaryo"):
        MGR["scenario"].update({"type": scen, "ask_ara": ask_ara})
        save_db(DB)
        st.success("Senaryo kaydedildi")

    st.divider()
    # Çalışan Tablosu
    st.subheader("Çalışan Listesi")
    with st.expander("Yeni Çalışan Ekle"):
        nc1, nc2 = st.columns(2)
        n_name = nc1.text_input("İsim", key="n_name")
        n_sicil = nc2.text_input("Sicil", key="n_sicil")
        n_pt = st.checkbox("Part‑time", key="n_pt")
        n_ht = st.selectbox("Haftalık Tatil", DAYS, index=6, key="n_ht")
        n_pt_days = st.multiselect("PT İzin Günleri", DAYS, key="n_pt_days")
        if st.button("Ekle", key="add_emp") and n_name and n_sicil:
            MGR["employees"].append({
                "name": n_name,
                "sicil": n_sicil,
                "pt": n_pt,
                "pt_days": n_pt_days,
                "ht_day": n_ht,
            })
            save_db(DB)
            st.success("Çalışan eklendi")

    # Düzenle / Sil
    if MGR["employees"]:
        edf = pd.DataFrame(MGR["employees"])
        st.dataframe(edf, use_container_width=True)
        del_idx = st.number_input("Silinecek satır no (0‑...)", min_value=0, max_value=len(edf)-1, step=1)
        if st.button("Sil"):
            MGR["employees"].pop(int(del_idx))
            save_db(DB)
            st.experimental_rerun()
    else:
        st.info("Henüz çalışan tanımlanmadı.")

# ────────────────────────────────────────────────────────────────────────────────
# VARDİYA OLUŞTUR
# ────────────────────────────────────────────────────────────────────────────────
if MENU == "Vardiya Oluştur":
    st.header("🗓️ Yeni Vardiya Oluştur")
    if not MGR["employees"]:
        st.warning("Önce Veriler menüsünde en az bir çalışan ekleyin.")
        st.stop()

    week_start = st.date_input("Haftanın Pazartesi tarihi", datetime.today())

    # Ara vardiya seçimi (isteğe bağlı)
    ara_list = []
    if MGR["scenario"].get("ask_ara"):
        ara_list = st.multiselect("Bu hafta Ara vardiya atanacak çalışanlar", [e["name"] for e in MGR["employees"]])

    if st.button("Vardiya Oluştur 🛠️"):
        last_hist = MGR["history"][-1]["schedule"] if MGR["history"] else None

        def last_row(emp_name):
            if not last_hist:
                return None
            for r in last_hist:
                if r["Çalışan"] == emp_name:
                    return r
            return None

        rows = []
        for idx_emp, emp in enumerate(MGR["employees"]):
            row = {"Çalışan": emp["name"], "Sicil": emp["sicil"]}
            prev = last_row(emp["name"])
            for d_idx, day in enumerate(DAYS):
                # PT günleri
                if emp["pt"] and day in emp["pt_days"]:
                    row[day] = "PT"; continue
                # Haftalık tatil
                if day == emp["ht_day"]:
                    row[day] = "H.T"; continue
                # Tatil komşuları
                if DAYS[(d_idx + 1) % 7] == emp["ht_day"]:
                    row[day] = "Sabah"; continue
                if DAYS[(d_idx - 1) % 7] == emp["ht_day"]:
                    row[day] = "Ara" if emp["name"] in ara_list else "Akşam"; continue

                scen_type = MGR["scenario"]["type"]
                if scen_type == "split":
                    prop = "Sabah" if idx_emp < len(MGR["employees"]) / 2 else "Akşam"
                else:  # balance
                    prop = "Sabah" if (d_idx + idx_emp) % 2 == 0 else "Akşam"

                # Ara önceliği
                if emp["name"] in ara_list and prop == "Sabah":
                    prop = "Ara"

                # Önceki haftayla denge
                if prev and prev.get(day) == prop:
                    prop = "Akşam" if prop == "Sabah" else "Sabah"
                # Aynı haftada üst üste engel
                if d_idx > 0 and row[DAYS[d_idx - 1]] == prop:
                    prop = "Akşam" if prop == "Sabah" else "Sabah"

                row[day] = prop
            rows.append(row)

        raw_df = pd.DataFrame(rows)
        pretty = raw_df.copy()
        for d in DAYS:
            pretty[d] = pretty[d].map(lambda x: SHIFT_MAP.get(x, x))

        st.subheader("🔍 Oluşturulan Vardiya")
        st.dataframe(pretty, use_container_width=True)

        # Kaydet
        MGR["history"].append({"week_start": str(week_start), "schedule": raw_df.to_dict("records")})
        save_db(DB)

        st.download_button("Excel'e Aktar (CSV)", pretty.to_csv(index=False).encode("utf-8-sig"), file_name="vardiya.csv")

# ────────────────────────────────────────────────────────────────────────────────
# GEÇMİŞ
# ────────────────────────────────────────────────────────────────────────────────
if MENU == "Geçmiş":
    st.header("📑 Geçmiş Vardiyalar")
    if not MGR["history"]:
        st.info("Henüz kayıt yok.")
    else:
        options = [f"Hafta: {rec['week_start']}" for rec in MGR["history"][::-1]]
        choice = st.selectbox("Hafta seç", options)
        rec = MGR["history"][::-1][options.index(choice)]
        df_hist = pd.DataFrame(rec["schedule"])
        for d in DAYS:
            df_hist[d] = df_hist[d].map(lambda x: SHIFT_MAP.get(x, x))
        st.dataframe(df_hist, use_container_width=True)

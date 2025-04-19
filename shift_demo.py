import json
import os
from datetime import datetime

import pandas as pd
import streamlit as st

# ────────────────────────────────────────────────────────────────────────────────
# SABİTLER
# ────────────────────────────────────────────────────────────────────────────────
PAGE_TITLE = "Şişecam Paşabahçe | Otomatik Vardiya Sistemi"
PRIMARY = "#0D4C92"
DATA_FILE = "data.json"
DAYS = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
SHIFT_MAP = {
    "Sabah": "09:30‑18:00",
    "Ara": "11:30‑20:00",
    "Akşam": "13:30‑22:00",
    "H.T": "Haftalık Tatil",
    "PT": "Part‑time İzin",
    "IZ": "İzin/Rapor",
}
SCENS = {
    "denge": "Denge (her çalışan 3 Sabah + 3 Akşam)",
    "ayrik": "Ayrık (ekibin yarısı daima Sabah, yarısı Akşam)",
}

st.set_page_config(page_title=PAGE_TITLE, page_icon="📆", layout="wide")
st.markdown(
    f"<style>div.block-container{{padding-top:1rem}} .st-emotion-cache-fblp2m{{color:{PRIMARY}!important}}</style>",
    unsafe_allow_html=True,
)
st.title(PAGE_TITLE)

# ────────────────────────────────────────────────────────────────────────────────
# VERİ TUTAR
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
        "managers": {},  # username▶dict
    }


def save_db(db):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)


if "db" not in st.session_state:
    st.session_state["db"] = load_db()
DB = st.session_state["db"]
DB.setdefault("users", {})
DB.setdefault("managers", {})
save_db(DB)

# ────────────────────────────────────────────────────────────────────────────────
# GİRİŞ
# ────────────────────────────────────────────────────────────────────────────────
if "user" not in st.session_state:
    st.subheader("🔐 Yönetici Girişi")
    ucol, pcol = st.columns(2)
    uname = ucol.text_input("Kullanıcı Adı")
    upass = pcol.text_input("Şifre", type="password")
    if st.button("Giriş"):
        if DB["users"].get(uname) == upass:
            if uname not in DB["managers"]:
                DB["managers"][uname] = {
                    "employees": [],
                    "scenario": {"type": "denge", "ask_ara": False},
                    "history": [],
                }
                save_db(DB)
            st.session_state["user"] = uname
            st.rerun()
        else:
            st.error("Hatalı giriş")
    st.stop()

USER = st.session_state["user"]
MGR = DB["managers"][USER]

# ────────────────────────────────────────────────────────────────────────────────
# SIDEBAR MENU
# ────────────────────────────────────────────────────────────────────────────────
MENU = st.sidebar.radio("🚀 Menü", ["Vardiya Oluştur", "Veriler", "Geçmiş"], index=0)

# ────────────────────────────────────────────────────────────────────────────────
# VERİLER
# ────────────────────────────────────────────────────────────────────────────────
if MENU == "Veriler":
    st.header("📂 Veriler")

    # SENEARYO ------------------------------------------------
    st.subheader("Senaryo Ayarları")
    scen_sel = st.radio(
        "Haftalık Dağıtım Senaryosu",
        SCENS,
        index=list(SCENS.keys()).index(MGR["scenario"]["type"]),
    )
    ask_ara = st.checkbox(
        "Ara vardiyaları her hafta manuel seçeceğim", value=MGR["scenario"].get("ask_ara", False)
    )
    if st.button("Kaydet Senaryo"):
        MGR["scenario"].update({"type": scen_sel, "ask_ara": ask_ara})
        save_db(DB)
        st.success("Senaryo kaydedildi")

    st.divider()
    st.subheader("Çalışanlar")

    with st.expander("Yeni Çalışan Ekle"):
        c1, c2 = st.columns(2)
        nm = c1.text_input("İsim")
        sc = c2.text_input("Sicil")
        is_pt = st.checkbox("Part‑time")
        ht_day = st.selectbox("Haftalık Tatil", DAYS, index=6)
        if is_pt:
            pt_days = st.multiselect("PT İzin Günleri", DAYS)
        else:
            pt_days = []
        if st.button("Ekle") and nm and sc:
            MGR["employees"].append({
                "name": nm,
                "sicil": sc,
                "pt": is_pt,
                "pt_days": pt_days,
                "ht_day": ht_day,
            })
            save_db(DB)
            st.success("Çalışan eklendi")

    # Tablo & satır‑sil butonu
    if MGR["employees"]:
        for idx, emp in enumerate(MGR["employees"]):
            cols = st.columns([3,2,1])
            cols[0].markdown(f"**{emp['name']}** — {emp['sicil']}")
            cols[1].markdown("PT" if emp["pt"] else "FT")
            if cols[2].button("Sil", key=f"del_{idx}"):
                MGR["employees"].pop(idx)
                save_db(DB)
                st.experimental_rerun()
    else:
        st.info("Henüz çalışan yok.")

# ────────────────────────────────────────────────────────────────────────────────
# VARDIYA OLUŞTUR
# ────────────────────────────────────────────────────────────────────────────────
if MENU == "Vardiya Oluştur":
    st.header("🗓️ Yeni Vardiya Oluştur")
    if not MGR["employees"]:
        st.warning("Önce Veriler bölümünde çalışan ekleyin.")
        st.stop()

    week_start = st.date_input("Haftanın Pazartesi tarihi", datetime.today())

    ara_list = []
    if MGR["scenario"].get("ask_ara"):
        ara_list = st.multiselect("Bu hafta Ara vardiya atanacak çalışanlar", [e["name"] for e in MGR["employees"]])

    # Haftalık İzin/Rapor butonu
    with st.expander("Bu hafta izin/rapor girişi"):
        iz_emp = st.selectbox("Çalışan seç", [e["name"] for e in MGR["employees"]] + ["—"])
        iz_day = st.selectbox("Gün seç", DAYS)
        iz_entries = {}
        if st.button("Ekle İzin/Rapor") and iz_emp != "—":
            iz_entries[iz_emp] = iz_day
            st.success(f"{iz_emp} için {iz_day} günü izin/rapor eklendi")

    if st.button("Vardiya Oluştur 🛠️"):
        last_hist = MGR["history"][-1]["schedule"] if MGR["history"] else None

        def last_row(name):
            if not last_hist:
                return None
            for r in last_hist:
                if r["Çalışan"] == name:
                    return r
            return None

        rows = []
        for idx, emp in enumerate(MGR["employees"]):
            row = {"Çalışan": emp["name"], "Sicil": emp["sicil"]}
            prev = last_row(emp["name"])
            for d_idx, day in enumerate(DAYS):
                # Özel izin
                if iz_entries.get(emp["name"]) == day:
                    row[day] = "IZ"; continue
                # PT
                if emp["pt"] and day in emp["pt_days"]:
                    row[day] = "PT"; continue
                # HT
                if day == emp["ht_day"]:
                    row[day] = "H.T"; continue
                # Tatil komşuları
                if DAYS[(d_idx+1)%7] == emp["ht_day"]:
                    row[day] = "Sabah"; continue
                if DAYS[(d_idx-1)%7] == emp["ht_day"]:
                    row[day] = "Ara" if emp["name"] in ara_list else "Akşam"; continue

                scen = MGR["scenario"]["type"]
                if scen == "ayrik":
                    prop = "Sabah" if idx < len(MGR["employees"])/2 else "Akşam"
                else:
                    prop = "Sabah" if (d_idx+idx) %2 ==0 else "Akşam"

                if emp["name"] in ara_list and prop=="Sabah":
                    prop="Ara"
                if prev and prev.get(day)==prop:
                    prop = "Akşam" if prop=="Sabah" else "Sabah"
                if d_idx>0 and row[DAYS[d_idx-1]]==prop:
                    prop = "Akşam" if prop=="Sabah" else "Sabah"
                row[day]=prop
            rows.append(row)

        raw = pd.DataFrame(rows)
        pretty = raw.copy()
        for d in DAYS:
            pretty[d] = pretty[d].map(lambda x: SHIFT_MAP.get(x,x))
        st.subheader("🔍 Oluşturulan Vardiya")
        st.dataframe(pretty, use_container_width=True)

        MGR["history"].append({"week_start": str(week_start), "schedule": raw.to_dict("records")})
        save_db(DB)
        st.download_button("Excel'e Aktar", pretty.to_csv(index=False).encode("utf-8-sig"), file_name="vardiya.csv")

# ────────────────────────────────────────────────────────────────────────────────
# GEÇMIŞ
# ────────────────────────────────────────────────────────────────────────────────
if MENU == "Geçmiş":
    st.header("📑 Geçmiş Vardiyalar")
    if not MGR["history"]:
        st.info("Kayıt bulunamadı")
    else:
        opts = [f"Hafta: {rec['week_start']}" for rec in MGR["history"][::-1]]
        ch = st.selectbox("Hafta seç", opts)
        rec = MGR["history"][::-1][opts.index(ch)]
        dfh = pd.DataFrame(rec["schedule"])
        for d in DAYS:
            dfh[d] = dfh[d].map(lambda x: SHIFT_MAP.get(x,x))
        st.dataframe(dfh, use_container_width=True)

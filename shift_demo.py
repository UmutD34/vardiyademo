import json
import os
from datetime import datetime
import pandas as pd
import streamlit as st

# ──────────────────────────────────────────────────────────────
# SABİTLER
# ──────────────────────────────────────────────────────────────
PAGE_TITLE = "Şişecam Paşabahçe | Otomatik Vardiya Sistemi"
PRIMARY = "#0D4C92"
DATA_FILE = "data.json"
DAYS = ["Pazartesi","Salı","Çarşamba","Perşembe","Cuma","Cumartesi","Pazar"]
SHIFT_MAP = {
    "Sabah": "09:30‑18:00",
    "Ara"  : "11:30‑20:00",
    "Akşam": "13:30‑22:00",
    "H.T" : "Haftalık Tatil",
    "PT"  : "Part‑time İzin",
    "IZ"  : "İzin/Rapor",
}
SCENS = {
    "denge": "Denge (her çalışan 3 Sabah + 3 Akşam)",
    "ayrik": "Ayrık (ekibin yarısı sabit Sabah, yarısı sabit Akşam)",
}
LEGACY_MAP = {"balance": "denge", "split": "ayrik"}
DEFAULT_USERS = {"admin":"1234","fatihdemir":"1234","ademkeles":"1234"}

# ──────────────────────────────────────────────────────────────
# PERSISTENCE
# ──────────────────────────────────────────────────────────────

def load_db():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE,"r",encoding="utf-8") as f:
            return json.load(f)
    return {"users":DEFAULT_USERS.copy(),"managers":{}}

def save_db(db):
    with open(DATA_FILE,"w",encoding="utf-8") as f:
        json.dump(db,f,ensure_ascii=False,indent=2)

# ──────────────────────────────────────────────────────────────
# STATE INIT
# ──────────────────────────────────────────────────────────────
if "db" not in st.session_state:
    st.session_state["db"] = load_db()
DB = st.session_state["db"]
DB.setdefault("users",{}).update({k:v for k,v in DEFAULT_USERS.items() if k not in DB["users"]})
DB.setdefault("managers",{})
save_db(DB)

st.set_page_config(page_title=PAGE_TITLE,page_icon="📆",layout="wide")
st.markdown(f"<style>div.block-container{{padding-top:1rem}} .st-emotion-cache-fblp2m{{color:{PRIMARY}!important}}</style>",unsafe_allow_html=True)
st.title(PAGE_TITLE)

# ──────────────────────────────────────────────────────────────
# AUTH
# ──────────────────────────────────────────────────────────────
if "user" not in st.session_state:
    st.subheader("🔐 Yönetici Girişi")
    c1,c2 = st.columns(2)
    uname = c1.text_input("Kullanıcı Adı")
    upass = c2.text_input("Şifre",type="password")
    if st.button("Giriş"):
        if DB["users"].get(uname)==upass:
            if uname not in DB["managers"]:
                DB["managers"][uname] = {"employees":[],"scenario":{"type":"denge","ask_ara":False},"history":[]}
                save_db(DB)
            st.session_state["user"] = uname
            st.experimental_rerun()
        else:
            st.error("Hatalı kullanıcı / şifre")
    st.stop()

USER = st.session_state["user"]
MGR  = DB["managers"][USER]

# Logout
if st.sidebar.button("🔓 Oturumu Kapat"):
    del st.session_state["user"]
    st.experimental_rerun()

# Senaryo legacy dönüşüm
stype = LEGACY_MAP.get(MGR.get("scenario",{}).get("type","denge"),MGR.get("scenario",{}).get("type","denge"))
if stype not in SCENS: stype="denge"
MGR.setdefault("scenario",{"type":stype,"ask_ara":False})
MGR["scenario"]["type"] = stype
save_db(DB)

# ──────────────────────────────────────────────────────────────
# MENU
# ──────────────────────────────────────────────────────────────
MENU = st.sidebar.radio("🚀 Menü",["Vardiya Oluştur","Veriler","Geçmiş"],index=0)

# ──────────────────────────────────────────────────────────────
# VERİLER
# ──────────────────────────────────────────────────────────────
if MENU=="Veriler":
    st.header("📂 Veriler")
    st.subheader("Senaryo Ayarları")
    scen_sel = st.radio("Haftalık Dağıtım Senaryosu",SCENS,index=list(SCENS.keys()).index(stype))
    ask_ara = st.checkbox("Ara vardiyaları her hafta manuel seçeceğim",value=MGR["scenario"].get("ask_ara",False))
    if st.button("Kaydet Senaryo"):
        MGR["scenario"].update({"type":scen_sel,"ask_ara":ask_ara}); save_db(DB); st.success("Kaydedildi")

    st.divider(); st.subheader("Çalışanlar")
    with st.expander("Yeni Çalışan Ekle"):
        ec1,ec2 = st.columns(2)
        nm = ec1.text_input("İsim")
        sc = ec2.text_input("Sicil")
        is_pt = st.checkbox("Part‑time")
        ht_day = st.selectbox("Haftalık Tatil",DAYS,index=6)
        pt_days = st.multiselect("PT İzin Günleri",DAYS) if is_pt else []
        if st.button("Ekle") and nm and sc:
            MGR["employees"].append({"name":nm,"sicil":sc,"pt":is_pt,"pt_days":pt_days,"ht_day":ht_day}); save_db(DB); st.success("Eklendi")

    if MGR["employees"]:
        for idx,emp in enumerate(MGR["employees"]):
            cols = st.columns([4,1])
            cols[0].markdown(f"**{emp['name']}** — {emp['sicil']} • {emp['ht_day']} • {'PT' if emp['pt'] else 'FT'}")
            if cols[1].button("Sil",key=f"del_{idx}"):
                MGR["employees"].pop(idx); save_db(DB); st.experimental_rerun()
    else:
        st.info("Henüz çalışan yok.")

# ──────────────────────────────────────────────────────────────
# VARDİYA OLUŞTUR
# ──────────────────────────────────────────────────────────────
if MENU=="Vardiya Oluştur":
    st.header("🗓️ Yeni Vardiya Oluştur")
    if not MGR["employees"]:
        st.warning("Önce çalışan ekleyin"); st.stop()

    week_start = st.date_input("Haftanın Pazartesi tarihi",datetime.today())
    ara_list = st.multiselect("Bu hafta Ara vardiya atanacak çalışanlar",[e["name"] for e in MGR["employees"]]) if MGR["scenario"].get("ask_ara") else []

    iz_entries = {}
    with st.expander("Bu hafta İzin / Rapor girişi"):
        iz_emp = st.selectbox("Çalışan seç",["—"]+[e["name"] for e in MGR["employees"]])
        iz_day = st.selectbox("Gün seç",DAYS)
        if st.button("Ekle İzin/Rapor") and iz_emp!="—":
            iz_entries[iz_emp]=iz_day; st.success("Kayıt eklendi")

    if st.button("Vardiya Oluştur 🛠️"):
        last_hist = MGR["history"][-1]["schedule"] if MGR["history"] else None
        def last_row(name):
            return next((r for r in last_hist if r["Çalışan"]==name),None) if last_hist else None

        rows=[]
        for idx,emp in enumerate(MGR["employees"]):
            row={"Çalışan":emp["name"],"Sicil":emp["sicil"]}
            prev=last_row(emp["name"])
            for d_idx,day in enumerate(DAYS):
                if iz_entries.get(emp["name"])==day:
                    row[day]="IZ"; continue
                if emp["pt"] and day in emp["pt_days"]:
                    row[day]="PT"; continue
                if day==emp["ht_day"]:
                    row[day]="H.T"; continue
                if DAYS[(d_idx+1)%7]==emp["ht_day"]:
                    row[day]="Sabah"; continue
                if DAYS[(d_idx-1)%7]==emp[

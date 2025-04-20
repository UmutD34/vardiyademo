# Shift Demo – Stabil base + Erken Vardiya Senaryosu
import json, os, random
from datetime import datetime, timedelta
import pandas as pd
import streamlit as st

PAGE_TITLE = "Şişecam Paşabahçe | Otomatik Vardiya Sistemi"
DATA_FILE = "data.json"
DAYS = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
SHIFT_MAP = {
    "Sabah": "09:30‑18:00",
    "Ara": "11:30‑20:00",
    "Akşam": "13:30‑22:00",
    "H.T": "Haftalık Tatil",
    "PT": "Part‑time İzin",
    "Rapor": "Raporlu",
    "Yİ": "Yıllık İzin",
}
SCENS = {
    "denge": "Haftada herkese 3 gün Sabahçı + 3 gün Akşamcı",
    "ayrik": "Yarısı Sabahçı, yarısı Akşamcı (hafta hafta terslenir)",
    "erken": "Erken Vardiya (sevkiyat saati + rastgele 2 kişi erken gelir)",
}
LEGACY = {"balance": "denge", "split": "ayrik"}
DEFAULT_USERS = {"admin": "1234", "fatihdemir": "1234", "ademkeles": "1234"}

# ───────────── Persistence ─────────────

def load_db():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"users": DEFAULT_USERS.copy(), "managers": {}}


def save_db(db):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

if "db" not in st.session_state:
    st.session_state["db"] = load_db()
DB = st.session_state["db"]
DB.setdefault("users", {}).update({k: v for k, v in DEFAULT_USERS.items() if k not in DB["users"]})
DB.setdefault("managers", {})
save_db(DB)

# ───────────── Page Config & Style ─────────────

st.set_page_config(page_title=PAGE_TITLE, page_icon="📆", layout="wide")
st.markdown(
    """
    <style>
      div.block-container { padding-top: 2rem; }
      .stButton>button { border-radius: 8px; font-weight: 600; }
      [role="grid"] { border: 1px solid #E0E0E0; }
    </style>
    """,
    unsafe_allow_html=True,
)
st.title(PAGE_TITLE)

# ───────────── Authentication ─────────────

if "user" not in st.session_state:
    col1, col2 = st.columns(2)
    uname = col1.text_input("Kullanıcı Adı")
    upass = col2.text_input("Şifre", type="password")
    if st.button("Giriş"):
        if DB["users"].get(uname) == upass:
            if uname not in DB["managers"]:
                DB["managers"][uname] = {"employees": [], "scenario": {"type": "denge", "ask_ara": False}, "history": []}
                save_db(DB)
            st.session_state["user"] = uname
            st.rerun()
        else:
            st.error("Hatalı kullanıcı/şifre")
    st.stop()

USER = st.session_state["user"]
MGR = DB["managers"][USER]
if st.sidebar.button("🔓 Oturumu Kapat"):
    del st.session_state["user"]
    st.rerun()

# ───────────── Scenario Legacy Fix ─────────────

stype = LEGACY.get(MGR.get("scenario", {}).get("type", "denge"), MGR.get("scenario", {}).get("type", "denge"))
if stype not in SCENS:
    stype = "denge"
MGR.setdefault("scenario", {"type": stype, "ask_ara": False, "ship_hour": 8})
MGR["scenario"]["type"] = stype
save_db(DB)

# ───────────── Sidebar Menu ─────────────

menu = st.sidebar.radio("🚀 Menü", ["Vardiya Oluştur", "Veriler", "Geçmiş"], index=0)
st.sidebar.markdown("---")
st.sidebar.markdown("👤 <b>Umut Doğan</b>", unsafe_allow_html=True)

# ───────────── Veriler Page ─────────────

if menu == "Veriler":
    st.header("📂 Veriler")
    st.subheader("Senaryo Ayarları")
    keys = list(SCENS.keys())
    labels = list(SCENS.values())
    idx = keys.index(stype)
    label = st.radio("Haftalık Dağıtım", labels, index=idx)
    sel = keys[labels.index(label)]
    ask = st.checkbox("Ara vardiyaları manuel seçeceğim", value=MGR["scenario"].get("ask_ara", False))
    ship = MGR["scenario"].get("ship_hour", 8)
    if sel == "erken":
        ship = st.number_input("Sevkiyat Saati (0-23)", min_value=0, max_value=23, value=int(ship))
    if st.button("Kaydet Senaryo"):
        MGR["scenario"].update({"type": sel, "ask_ara": ask, "ship_hour": ship})
        save_db(DB)
        st.success("Kaydedildi")
    st.divider()
    st.subheader("Çalışanlar")
    with st.expander("Yeni Çalışan Ekle"):
        e1, e2 = st.columns(2)
        name = e1.text_input("İsim")
        sicil = e2.text_input("Sicil")
        pt = st.checkbox("Part-time")
        ht = st.selectbox("Haftalık Tatil", DAYS)
        pt_days = st.multiselect("PT İzin Günleri", DAYS) if pt else []
        if st.button("Ekle", key="add_emp") and name and sicil:
            MGR["employees"].append({"name": name, "sicil": sicil, "pt": pt, "pt_days": pt_days, "ht_day": ht})
            save_db(DB)
            st.success("Çalışan eklendi")
            st.rerun()
    df = pd.DataFrame(MGR["employees"]) if MGR["employees"] else pd.DataFrame(columns=["name","sicil","pt","pt_days","ht_day"])
    edited = st.data_editor(df, num_rows="dynamic", hide_index=True)
    if st.button("Değişiklikleri Kaydet"):
        tmp = edited.replace({"": None}).dropna(subset=["name","sicil"]).drop_duplicates(subset=["sicil"])
        MGR["employees"] = tmp.to_dict("records")
        save_db(DB)
        st.success("Kaydedildi")
        st.rerun()

# ───────────── Vardiya Oluştur Page ─────────────

if menu == "Vardiya Oluştur":
    st.header("🗓️ Yeni Vardiya")
    if not MGR["employees"]:
        st.warning("Önce çalışan ekleyin")
        st.stop()
    week = st.date_input("Haftanın Pazartesi", datetime.today())
    ara = []
    if MGR["scenario"].get("ask_ara"):
        ara = st.multiselect("Ara vardiya atanacaklar", [e["name"] for e in MGR["employees"]])
    if "iz_entries" not in st.session_state:
        st.session_state["iz_entries"] = {}
    iz = st.session_state["iz_entries"]
    with st.expander("Bu hafta İzin/Rapor"):
        sel_emp = st.selectbox("Çalışan", ["—"] + [e["name"] for e in MGR["employees"]])
        sel_day = st.selectbox("Gün", DAYS)
        sel_type = st.selectbox("İzin Türü", ["Rapor","Yıllık İzin"])
        if st.button("Ekle", key="add_iz") and sel_emp != "—":
            iz[sel_emp] = {"day": sel_day, "type": ("Rapor" if sel_type=="Rapor" else "Yİ")}
            st.success("Eklendi")
    if st.button("Vardiya Oluştur 🛠️"):
        last = MGR["history"][-1]["schedule"] if MGR["history"] else []
        def prev_row(n): return next((r for r in last if r["Çalışan"]==n),None)
        rows=[]
        for idx, emp in enumerate(MGR["employees"]):
            r={"Çalışan":emp["name"],"Sicil":emp["sicil"]}
            prev = prev_row(emp["name"])
            for d_i, day in enumerate(DAYS):
                # İzin/Rapor
                ent = iz.get(emp["name"])
                if ent and ent["day"]==day:
                    r[day]=ent["type"]
                    continue
                # PT
                if emp.get("pt") and day in emp.get("pt_days",[]):
                    r[day]="PT"
                    continue
                # Haftalık Tatil
                if day==emp.get("ht_day"):
                    r[day]="H.T"
                    continue
                # Tatil komşusu kuralları
                if DAYS[(d_i+1)%7]==emp.get("ht_day"):
                    r[day]="Sabah"
                    continue
                if DAYS[(d_i-1)%7]==emp.get("ht_day"):
                    r[day]="Ara" if emp["name"] in ara else "Akşam"
                    continue
                # Senaryo
                scen = MGR["scenario"]["type"]
                if scen=="ayrik":
                    # Haftalık tersleme
                    if prev:
                        sab= sum(1 for d in DAYS if prev.get(d) in ["Sabah","Ara"])
                        akm= sum(1 for d in DAYS if prev.get(d)=="Akşam")
                        prop = "Akşam" if sab>akm else "Sabah"
                    else:
                        prop = "Sabah" if idx<len(MGR["employees"])/2 else "Akşam"
                elif scen=="erken":
                    # Erken vardiya: rastgele 2 kişi sabahcıdan seçilir
                    ship = MGR["scenario"].get("ship_hour",8)
                    if d_i==0: prop = f"{int(ship):02d}:00-{int(ship)+8:02d}:30"
                    elif (d_i==0) and emp["name"] not in random.sample([e["name"] for e in MGR["employees"]],2): prop="Sabah"
                    else: prop = "Akşam"
                else:
                    prop = "Sabah" if (d_i+idx)%2==0 else "Akşam"
                # Ara önceliği
                if emp["name"] in ara and prop=="Sabah": prop="Ara"
                if scen!="erken" and emp["name"] not in ara and prop=="Ara": prop="Sabah"
                # Ardışık kontrol
                if prev and prev.get(day)==prop: prop = "Akşam" if prop=="Sabah" else "Sabah"
                if d_i>0 and r[DAYS[d_i-1]]==prop: prop = "Akşam" if prop=="Sabah" else "Sabah"
                r[day]=prop
            rows.append(r)
        df_raw=pd.DataFrame(rows)
        df_pre = df_raw.applymap(lambda x: SHIFT_MAP.get(x,x))
        st.dataframe(df_pre,use_container_width=True)
        MGR["history"].append({"week_start":str(week),"schedule":df_raw.to_dict("records")})
        save_db(DB)
        st.session_state["iz_entries"] = {}
        st.download_button("Excel'e Aktar", df_pre.to_csv(index=False).encode('utf-8-sig'))

# ───────────── Geçmiş Page ─────────────
if menu=="Geçmiş":
    st.header("📑 Geçmiş Vardiyalar")
    hist = MGR.get("history",[])
    if not hist:
        st.info("Kayıt yok")
    else:
        opts=[f"Hafta: {h['week_start']}" for h in hist[::-1]]
        choice=st.selectbox("Hafta",opts)
        rec=hist[::-1][opts.index(choice)]
        dfh=pd.DataFrame(rec['schedule']).applymap(lambda x:SHIFT_MAP.get(x,x))
        st.dataframe(dfh,use_container_width=True)
        if st.button("Geçmişi Sil 🗑️"):
            MGR['history'].clear(); save_db(DB); st.success("Silindi"); st.rerun()

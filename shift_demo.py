# Shift Demo – with “Erken Vardiya” senaryosu ve iyileştirmeler
import json, os, random
from datetime import datetime, timedelta
import pandas as pd, streamlit as st

PAGE_TITLE = "Şişecam Paşabahçe | Otomatik Vardiya Sistemi"
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
    "denge": "Haftada herkese 3 gün Sabahçı + 3 gün Akşamcı",
    "ayrik": "Yarısı Sabahçı, yarısı Akşamcı (hafta hafta terslenir)",
    "erken": "Erken Vardiya (sevkiyat saati + rastgele 2 kişi erken gelir)",
}
LEGACY = {"balance": "denge", "split": "ayrik"}
DEFAULT_USERS = {"admin": "1234", "fatihdemir": "1234", "ademkeles": "1234"}

# ---------- persistence ----------

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

st.set_page_config(page_title=PAGE_TITLE, page_icon="📆", layout="wide")
st.title(PAGE_TITLE)

# ---------- login ----------
if "user" not in st.session_state:
    u, p = st.columns(2)
    uname = u.text_input("Kullanıcı Adı")
    upass = p.text_input("Şifre", type="password")
    if st.button("Giriş"):
        if DB["users"].get(uname) == upass:
            if uname not in DB["managers"]:
                DB["managers"][uname] = {"employees": [], "scenario": {"type": "denge", "ask_ara": False}, "history": []}
                save_db(DB)
            st.session_state["user"] = uname
            st.rerun()
        else:
            st.error("Hatalı giriş")
    st.stop()

USER = st.session_state["user"]
MGR = DB["managers"][USER]

# ---------- scenario legacy ----------
stype = LEGACY.get(MGR.get("scenario", {}).get("type", "denge"), MGR.get("scenario", {}).get("type", "denge"))
if stype not in SCENS:
    stype = "denge"
MGR.setdefault("scenario", {"type": stype, "ask_ara": False})
MGR["scenario"]["type"] = stype
save_db(DB)

MENU = st.sidebar.radio("🚀 Menü", ["Vardiya Oluştur", "Veriler", "Geçmiş"], index=0)

st.sidebar.markdown("---")
st.sidebar.markdown("Palladium&Hiltown Pasabahce ❤️")

# ---------- Veriler page ----------
if MENU == "Veriler":
    st.header("📂 Veriler")
    st.subheader("Senaryo Ayarları")
    scen_keys = list(SCENS.keys())
    scen_labels = list(SCENS.values())
    sel_label = st.radio("Haftalık Dağıtım", scen_labels, index=scen_keys.index(stype))
    scen_sel = scen_keys[scen_labels.index(sel_label)]

    ask_ara = st.checkbox("Ara vardiyaları manuel seçeceğim", value=MGR["scenario"].get("ask_ara", False))

    ship_hour = MGR["scenario"].get("ship_hour", 8)
    if scen_sel == "erken":
        ship_hour = st.number_input("Sevkiyat saatiniz nedir? (0‑23)", min_value=0, max_value=23, value=int(ship_hour))

    if st.button("Kaydet Senaryo"):
        MGR["scenario"].update({"type": scen_sel, "ask_ara": ask_ara, "ship_hour": ship_hour})
        save_db(DB)
        st.success("Kaydedildi")

    st.divider(); st.subheader("Çalışanlar")
    with st.expander("Yeni Çalışan Ekle"):
        c1, c2 = st.columns(2)
        nm = c1.text_input("İsim")
        sc = c2.text_input("Sicil")
        is_pt = st.checkbox("Part‑time")
        ht = st.selectbox("Haftalık Tatil", DAYS, index=6)
        pt_days = st.multiselect("PT İzin Günleri", DAYS) if is_pt else []
        if st.button("Ekle", key="add_emp") and nm and sc:
            MGR["employees"].append({"name": nm, "sicil": sc, "pt": is_pt, "pt_days": pt_days, "ht_day": ht})
            save_db(DB)
            st.success("Çalışan eklendi")
            st.rerun()

    emp_df = pd.DataFrame(MGR["employees"]) if MGR["employees"] else pd.DataFrame(columns=["name", "sicil", "pt", "pt_days", "ht_day"])
    edited = st.data_editor(emp_df, num_rows="dynamic", hide_index=True)

    if st.button("Değişiklikleri Kaydet"):
        tmp = edited.replace({"": None}).dropna(subset=["name", "sicil"]).drop_duplicates(subset=["sicil"])
        MGR["employees"] = tmp.to_dict("records")
        save_db(DB)
        st.success("Kaydedildi"); st.rerun()

# ---------- Vardiya Oluştur page ----------
if MENU == "Vardiya Oluştur":
    st.header("🗓️ Yeni Vardiya")
    if not MGR["employees"]:
        st.warning("Önce çalışan ekleyin"); st.stop()

    week_start = st.date_input("Haftanın Pazartesi", datetime.today())
    ara_list = st.multiselect("Ara vardiya atanacaklar", [e["name"] for e in MGR["employees"]]) if MGR["scenario"].get("ask_ara") else []

    if "iz_entries" not in st.session_state:
        st.session_state["iz_entries"] = {}
    iz_entries = st.session_state["iz_entries"]

    with st.expander("Bu hafta İzin / Rapor"):
        ie = st.selectbox("Çalışan", ["—"] + [e["name"] for e in MGR["employees"]])
        iday = st.selectbox("Gün", DAYS)
        itype = st.selectbox("İzin Türü", ["Rapor", "Yıllık İzin"])
        if st.button("Ekle", key="add_iz") and ie != "—":
            iz_entries[ie] = {"day": iday, "type": ("Rapor" if itype == "Rapor" else "Yİ")}
            st.success("Eklendi")

    if st.button("Vardiya Oluştur 🛠️"):
        last = MGR["history"][-1]["schedule"] if MGR["history"] else []
        def last_row(n):
            return next((r for r in last if r["Çalışan"] == n), None)

        rows = []
        for idx, e in enumerate(MGR["employees"]):
            r = {"Çalışan": e["name"], "Sicil": e["sicil"]}
            prev = last_row(e["name"])
            for d_idx, day in enumerate(DAYS):
                # izin/rapor
                ent = iz_entries.get(e["name"])
                if ent and ent["day"] == day:
                    r[day] = ent["type"]; continue
                # PT izin günleri
                if e.get("pt") and day in e.get("pt_days", []):
                    r[day] = "PT"; continue
                # Haftalık tatil
                if day == e.get("ht_day"):
                    r[day] = "H.T"; continue
                if DAYS[(d_idx + 1) % 7] == e.get("ht_day"):
                    r[day] = "Sabah"; continue
                if DAYS[(

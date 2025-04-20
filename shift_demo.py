# Shift Demo – cleaned indentation and login card
import json, os, pathlib
from datetime import datetime
import pandas as pd
import streamlit as st

PAGE_TITLE = "Şişecam Paşabahçe | Otomatik Vardiya Sistemi"
PRIMARY = "#0D4C92"
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
    "denge": "Haftada herkese 3 gün Sabahçı 3 gün Akşamcı",
    "ayrik": "Haftada belli kişiler Sabahçı belli kişiler Akşamcı (ertesi hafta tersine döner)",
}
LEGACY = {"balance": "denge", "split": "ayrik"}
DEFAULT_USERS = {"admin": "1234", "fatihdemir": "1234", "ademkeles": "1234"}

# ─────────────────────────────────────────────────────────────
# Yardımcılar
# ─────────────────────────────────────────────────────────────

def load_db():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"users": DEFAULT_USERS.copy(), "managers": {}}


def save_db(db):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

# ─────────────────────────────────────────────────────────────
# Başlat / State
# ─────────────────────────────────────────────────────────────
if "db" not in st.session_state:
    st.session_state["db"] = load_db()
DB = st.session_state["db"]
DB.setdefault("users", {}).update({k: v for k, v in DEFAULT_USERS.items() if k not in DB["users"]})
DB.setdefault("managers", {})
save_db(DB)

st.set_page_config(page_title=PAGE_TITLE, page_icon="📆", layout="wide")
# Basit kurumsal stil
st.markdown(
    """
    <style>
      div.block-container{padding-top:2rem}
      .stButton>button{border-radius:8px;font-weight:600}
      [role="grid"]{border:1px solid #E0E0E0}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title(PAGE_TITLE)

# ─────────────────────────────────────────────────────────────
# Giriş ekranı
# ─────────────────────────────────────────────────────────────
if "user" not in st.session_state:

    st.markdown(
        """
        <style>
            body {background:url('bg.jpg') no-repeat center center fixed; background-size:cover;}
            .login-card{max-width:420px;margin:8% auto;padding:2rem 2.5rem;background:rgba(255,255,255,0.92);border-radius:12px;box-shadow:0 4px 20px rgba(0,0,0,0.15);} 
            .login-card h2{text-align:center;margin-bottom:1.2rem;}
            .stTextInput>div>input{border-radius:6px;}
            .stButton>button{width:100%;border-radius:6px;}
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.container():
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        logo_path = pathlib.Path("logo.png")
        if logo_path.exists():
            st.image(str(logo_path), width=96)
        st.markdown("<h2>Yönetici Girişi</h2>", unsafe_allow_html=True)
        uname = st.text_input("Kullanıcı Adı")
        upass = st.text_input("Şifre", type="password")
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
                st.error("Hatalı kullanıcı / şifre")
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# (devam eden kod—vardiya, veriler, geçmiş)

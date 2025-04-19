import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Otomatik Vardiya Demo", page_icon="⚙️", layout="wide")

# -------------------------------------------------
# OTURUM DURUMU (TEK SEFERLİK YÖNETİCİ TANIMI)
# -------------------------------------------------
if "employees" not in st.session_state:
    st.session_state["employees"] = []  # [{name, sicil}]

# -------------------------------------------------
# BAŞLIK
# -------------------------------------------------
st.title("🗓️  Palladium Otomatik Vardiya Oluşturucu (Demo)")

# -------------------------------------------------
# YAN PANEL: YÖNETİCİ AYARLARI
# -------------------------------------------------
with st.sidebar:
    st.header("Yönetici Ayarları")

    names_input = st.text_area(
        "Çalışan isimlerini SICIL numarasıyla birlikte gir (her satıra: İsim - Sicil)",
        placeholder="Fatih Demir - 128938\nMesut Küçük - 110755",
        height=150,
    )
    if st.button("Kaydet Çalışanlar"):
        employees = []
        for line in names_input.splitlines():
            parts = [p.strip() for p in line.split("-") if p.strip()]
            if not parts:
                continue
            name = parts[0]
            sicil = parts[1] if len(parts) >= 2 else str(100000 + len(employees))
            employees.append({"name": name, "sicil": sicil})
        st.session_state["employees"] = employees
        st.success("Çalışan listesi güncellendi ✔️")

    if st.session_state["employees"]:
        emp_names = [e["name"] for e in st.session_state["employees"]]
        pt_selected = st.multiselect("Part‑time (izinli) çalışanları seç", emp_names, key="pt")
        ara_selected = st.multiselect(
            "Bu haftaya *Ara* vardiya atamak istediğin çalışan(lar)", emp_names, key="ara"
        )
    else:
        pt_selected = []
        ara_selected = []

    ht_day = st.selectbox(
        "Haftalık Tatil (H.T) Günü",
        [
            "Pazartesi",
            "Salı",
            "Çarşamba",
            "Perşembe",
            "Cuma",
            "Cumartesi",
            "Pazar",
        ],
        index=4,
    )
    generate = st.button("VARDİYA YAP 🛠️")

# -------------------------------------------------
# FONKSİYON: PROGRAMI OLUŞTUR
# -------------------------------------------------
DAYS = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
SHIFTS_ORDER = ["Sabah", "Akşam"]  # Demo sıralaması


def build_schedule(employees, ht_day, ara_selected, pt_selected):
    # Basit demo algoritması: kuralları örneklemek için.
    df_rows = []
    for i, emp in enumerate(employees):
        row = {"Çalışan": emp["name"], "Sicil": emp["sicil"]}
        for d_idx, day in enumerate(DAYS):
            if emp["name"] in pt_selected:
                row[day] = "PT"
                continue
            if day == ht_day:
                row[day] = "H.T"
                continue

            # Haftalık tatilin bir önceki ve bir sonraki gün kuralı
            if DAYS[(d_idx + 1) % 7] == ht_day:
                row[day] = "Sabah"
            elif DAYS[(d_idx - 1) % 7] == ht_day:
                row[day] = "Ara" if emp["name"] in ara_selected else "Akşam"
            else:
                # Basit denge: sıra + gün indeksi ile alterne et
                proposed = SHIFTS_ORDER[(i + d_idx) % 2]
                # Üst üste aynı vardiyayı engelle (demo: sadece önceki gün bakarak)
                prev_day = DAYS[d_idx - 1]
                if d_idx > 0 and row.get(prev_day) == proposed:
                    proposed = "Akşam" if proposed == "Sabah" else "Sabah"
                # Ara önceliği
                if proposed == "Sabah" and emp["name"] in ara_selected:
                    proposed = "Ara"
                row[day] = proposed
        df_rows.append(row)
    return pd.DataFrame(df_rows)

# -------------------------------------------------
# ARAYÜZ: ÇIKTI
# -------------------------------------------------
if generate:
    if not st.session_state["employees"]:
        st.warning("Lütfen önce çalışanları gir ⏳")
    else:
        sched = build_schedule(
            st.session_state["employees"], ht_day, ara_selected, pt_selected
        )
        st.subheader("📋 Oluşturulan Vardiya Programı (Demo)")
        st.dataframe(sched, use_container_width=True)

        csv = sched.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Excel'e Aktar (CSV)",
            csv,
            file_name="vardiya_programi.csv",
            mime="text/csv",
        )
else:
    st.info("Çalışanları ekle ve *VARDİYA YAP* düğmesine bas.")

st.caption("⏳ Bu demo temel mantığı göstermek içindir. Tam CP‑SAT algoritması üretim sürümünde entegre edilecek.")

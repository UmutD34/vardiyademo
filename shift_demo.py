# Shift Demo – Güncellenmiş ve Stabil Kod
import json, os, random
from datetime import datetime, timedelta
import pandas as pd
import streamlit as st

# ───────────── Sabitler ─────────────
PAGE_TITLE = "Şişecam Paşabahçe | Otomatik Vardiya Sistemi"
DATA_FILE = "data.json"
DAYS = ["Pazartesi","Salı","Çarşamba","Perşembe","Cuma","Cumartesi","Pazar"]

SHIFT_MAP = {
    "Sabah": "09:30‑18:00",
    "Ara":   "11:30‑20:00",
    "Akşam": "13:30‑22:00",
    "H.T":   "Haftalık Tatil",
    "PT":    "Part‑time İzin",
    "Rapor": "Raporlu",
    "Yİ":    "Yıllık İzin",
}
SCENS = {
    "denge": "3 Sabahçı + 3 Akşamcı",
    "ayrik": "Yarı Sabahçı / Yarı Akşamcı (hafta hafta terslenir)",
    "erken": "Erken Vardiya"
}
DEFAULT_USERS = {"admin":"1234","fatihdemir":"1234","ademkeles":"1234"}

# ───────────── Veri Yükleme / Kaydetme ─────────────

def load_db():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, encoding='utf-8') as f:
            return json.load(f)
    return {"users": DEFAULT_USERS.copy(), "managers": {}}

def save_db(db):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

if 'db' not in st.session_state:
    st.session_state['db'] = load_db()
DB = st.session_state['db']
DB.setdefault('users', {}).update({u: DEFAULT_USERS[u] for u in DEFAULT_USERS if u not in DB['users']})
DB.setdefault('managers', {})
save_db(DB)

# ───────────── Sayfa Konfigürasyonu ─────────────

st.set_page_config(page_title=PAGE_TITLE, page_icon='📆', layout='wide')
st.markdown(
    """
    <style>
      div.block-container { padding-top:2rem; }
      .stButton>button { border-radius:8px; font-weight:600; }
      [role="grid"] { border:1px solid #E0E0E0; }
    </style>
    """, unsafe_allow_html=True
)

st.title(PAGE_TITLE)

# ───────────── Giriş / Kullanıcı Kontrol ─────────────

if 'user' not in st.session_state:
    c1, c2 = st.columns(2)
    uname = c1.text_input('Kullanıcı Adı')
    upass = c2.text_input('Şifre', type='password')
    if st.button('Giriş'):
        if DB['users'].get(uname) == upass:
            DB['managers'].setdefault(uname, {
                'employees': [],
                'scenario': {'type': 'denge', 'ask_ara': False, 'ship_hour': 8.0, 'early_days': []},
                'history': []
            })
            save_db(DB)
            st.session_state['user'] = uname
            st.rerun()
        else:
            st.error('Hatalı kullanıcı / şifre')
    st.stop()

USER = st.session_state['user']
MGR = DB['managers'][USER]
if st.sidebar.button('🔓 Oturumu Kapat'):
    del st.session_state['user']
    st.rerun()

# ───────────── Yan Menü ─────────────

menu = st.sidebar.radio('Menü', ['Vardiya Oluştur','Veriler','Geçmiş'])
st.sidebar.markdown('---')
st.sidebar.write(f'👤 {USER}')

# ───────────── Veriler Sayfası ─────────────

if menu == 'Veriler':
    st.header('Senaryo Ayarları')
    keys = list(SCENS.keys())
    labels = list(SCENS.values())
    idx = keys.index(MGR['scenario']['type'])
    sel_label = st.radio('Senaryo', labels, index=idx)
    scen = keys[labels.index(sel_label)]

    ask_ara = st.checkbox('Ara vardiyaları manuel seçeceğim', value=MGR['scenario']['ask_ara'])
    ship_hour = MGR['scenario']['ship_hour']
    early_days = MGR['scenario']['early_days']
    if scen == 'erken':
        ship_hour = st.number_input('Sevkiyat Saati', min_value=0.0, max_value=23.5, step=0.5, value=float(ship_hour))
        early_days = st.multiselect('Erken Günler', DAYS, default=early_days)

    if st.button('Kaydet'): 
        MGR['scenario'] = {'type':scen, 'ask_ara':ask_ara, 'ship_hour':ship_hour, 'early_days':early_days}
        save_db(DB)
        st.success('Senaryo kaydedildi')

    st.divider()
    st.header('Çalışanlar')
    with st.expander('Yeni Çalışan Ekle'):
        n1, n2 = st.columns(2)
        name = n1.text_input('İsim')
        code = n2.text_input('Sicil')
        is_pt = st.checkbox('Part-time')
        ht_day = st.selectbox('Haftalık Tatil', DAYS)
        pt_days = st.multiselect('PT İzin Günleri', DAYS) if is_pt else []
        if st.button('Ekle', key='add_emp') and name and code:
            MGR['employees'].append({'name':name,'sicil':code,'pt':is_pt,'pt_days':pt_days,'ht_day':ht_day})
            save_db(DB); st.success('Çalışan eklendi'); st.rerun()

    df_emp = pd.DataFrame(MGR['employees']) if MGR['employees'] else pd.DataFrame(columns=['name','sicil','pt','pt_days','ht_day'])
    edited = st.data_editor(df_emp, num_rows='dynamic', hide_index=True)
    if st.button('Çalışanları Kaydet'):
        clean = edited.dropna(subset=['name','sicil']).drop_duplicates(subset=['sicil'])
        MGR['employees'] = clean.to_dict('records')
        save_db(DB); st.success('Kaydedildi'); st.rerun()

# ───────────── Vardiya Oluştur Sayfası ─────────────

if menu == 'Vardiya Oluştur':
    st.header('Yeni Vardiya')
    if not MGR['employees']:
        st.warning('Önce çalışan ekleyin'); st.stop()

    week_start = st.date_input('Haftanın Pazartesi Tarihi', datetime.today())
    manual_ara = MGR['scenario']['ask_ara']
    ara_list = st.multiselect('Ara vardiyaları', [e['name'] for e in MGR['employees']]) if manual_ara else []

    if 'iz_entries' not in st.session_state:
        st.session_state['iz_entries'] = {}
    iz_entries = st.session_state['iz_entries']

    with st.expander('İzin / Rapor Girişi'):
        sel_emp = st.selectbox('Çalışan', ['—'] + [e['name'] for e in MGR['employees']])
        sel_day = st.selectbox('Gün', DAYS)
        sel_type = st.selectbox('İzin Türü', ['Rapor','Yıllık İzin'])
        if st.button('Ekle İzin') and sel_emp != '—':
            iz_entries[sel_emp] = {'day':sel_day,'type':('Rapor' if sel_type=='Rapor' else 'Yİ')}
            st.success('İzin eklendi')

    scen = MGR['scenario']['type']
    early_ass = {}
    if scen == 'erken':
        for d in MGR['scenario']['early_days']:
            pool = [e['name'] for e in MGR['employees']]
            early_ass[d] = random.sample(pool, 2)

    last_schedule = MGR['history'][-1]['schedule'] if MGR['history'] else []

    def get_prev(name, day):
        rec = next((r for r in last_schedule if r['Çalışan']==name), {})
        return rec.get(day)

    rows = []
    for idx, emp in enumerate(MGR['employees']):
        prev = {d:get_prev(emp['name'], d) for d in DAYS}
        for di, day in enumerate(DAYS):
            # İzin/Rapor
            ent = iz_entries.get(emp['name'])
            if ent and ent['day']==day:
                shift = ent['type']
            elif emp['pt'] and day in emp['pt_days']:
                shift = 'PT'
            elif day == emp['ht_day']:
                shift = 'H.T'
            elif day == DAYS[(di+1)%7] and ent is None:
                shift = 'Sabah'
            elif day == DAYS[(di-1)%7] and ent is None:
                shift = 'Ara' if emp['name'] in ara_list else 'Akşam'
            elif scen == 'erken' and day in MGR['scenario']['early_days'] and emp['name'] in early_ass.get(day, []):
                sh = MGR['scenario']['ship_hour']
                h1, m1 = int(sh), int((sh-int(sh))*60)
                h2, m2 = int(sh+8), int(((sh+8)-int(sh+8))*60)
                shift = f"{h1:02d}:{m1:02d}-{h2:02d}:{m2:02d}"
            else:
                # Denge veya ayrık
                if scen == 'ayrik':
                    total_sab = sum(1 for d in DAYS if prev[d] in ['Sabah','Ara'])
                    total_akm = sum(1 for d in DAYS if prev[d]=='Akşam')
                    prop = 'Akşam' if total_sab>total_akm else 'Sabah'
                else:
                    prop = 'Sabah' if (di+idx)%2==0 else 'Akşam'
                # Ara önceliği
                if emp['name'] in ara_list and prop=='Sabah': prop='Ara'
                shift = prop
            rows.append({'Çalışan':emp['name'], 'Gün':day, 'Vardiya':shift})

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True)

    # Kaydet
    MGR['history'].append({'week_start':str(week_start), 'schedule':rows})
    save_db(DB)
    st.session_state['iz_entries'] = {}
    st.download_button('Excel’e Aktar', df.to_csv(index=False).encode('utf-8-sig'))

# ───────────── Geçmiş Sayfası ─────────────

if menu == 'Geçmiş':
    st.header('Geçmiş Vardiya Kayıtları')
    hist = MGR.get('history', [])
    if not hist:
        st.info('Kayıt bulunamadı')
    else:
        opts = [f"{r['week_start']}" for r in hist]
        sel = st.selectbox('Hafta seç', opts)
        rec = hist[opts.index(sel)]
        dfh = pd.DataFrame(rec['schedule'])
        st.dataframe(dfh, use_container_width=True)
